"""Escalation engine: given the echoed tutoring state, this turn's classification label and
any detected strategy request, decide what the tutor does next. Pure logic: no FastAPI, no
I/O, no logging of student text, no randomness (the new episode id comes from an injected
callable). Text generation, route wiring and the episode log are later stages.

The label comes from the prototype hybrid classifier (a proxy trained on synthetic
answers); the engine only consumes it.

Tiers: 1 default order theory -> example -> simplified -> analogy; 2 an explicit student
request overrides the default immediately; 3 personalised order is a SEAM ONLY (raises).

Research-critical rules (each has dedicated tests):
 1. A requested delivery is appended to `strategies_used` with trigger "request" but never
    consumes an escalation slot (claim C6): a request expresses a preference, not a weakness.
 2. `offer_new_cycle` sets awaiting_cycle_confirmation = True (the frontend shows Yes/No
    from this flag, not from `action`).
 3. `unclear` cycle intent returns `clarify` and keeps the flag True.
 4. Resolution needs at least one prior delivery.
 5. trigger is "default" only for the episode's very first delivery, else "confusion"
    (including the first delivery of cycle 2).
 6. No non-request strategy repeats within a cycle; a requested one may.

`strategies_used` is cumulative for the whole episode and never cleared. The current cycle
is DERIVED by counting, anchored on `state.cycle`: the current cycle's consumed slots are
`non_request[4 * (state.cycle - 1):]`. (Counting to "the last multiple of four" instead
would see the boundary as already passed when cycle 1 has just used its fourth strategy,
and the offer would never happen.)

`prior_explanations` is never touched here; a later stage appends generated text.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, get_args
from uuid import uuid4

from app.escalation.request_detector import detect_cycle_intent
from app.schemas import Strategy, StrategyUse, Trigger, TutorState

Action = Literal["explain", "resolved", "offer_new_cycle", "end_unresolved", "clarify"]
Outcome = Literal["resolved", "end_unresolved"]
Label = Literal["confused", "understood"]

DEFAULT_ORDER: tuple[Strategy, ...] = ("theory", "example", "simplified", "analogy")
CYCLE_SIZE = len(DEFAULT_ORDER)  # every completed cycle holds exactly 4 non-request deliveries
_STRATEGIES = frozenset(get_args(Strategy))
_TRIGGERS = frozenset(get_args(Trigger))


class InvalidStateError(ValueError):
    """The echoed state is one the engine could never have produced (a later stage maps it to 422)."""


@dataclass(frozen=True)
class EngineConfig:
    max_cycles: int = 2
    personalise: bool = False  # Tier 3 seam; personalised_order raises while it is unbuilt

    @classmethod
    def from_settings(cls, settings) -> "EngineConfig":
        return cls(max_cycles=settings.MAX_CYCLES, personalise=settings.PERSONALISE)


@dataclass(frozen=True)
class Decision:
    action: Action
    strategy: Strategy | None  # non-null only for explain
    trigger: Trigger | None  # non-null only for explain
    updated_state: TutorState  # always a NEW object, never the input
    outcome: Outcome | None = None  # terminal actions only
    winning_strategy: Strategy | None = None  # last delivered strategy, on resolved only


def default_episode_id() -> str:
    return f"ep_{uuid4().hex[:8]}"


def personalised_order(state: TutorState, cfg: EngineConfig) -> tuple[Strategy, ...]:
    """Tier 3 seam. Deliberately unbuilt: a seam that pretends to work is worse than one that says it doesn't."""
    raise NotImplementedError("personalised ordering is PP2")


# --- derived cycle structure ----------------------------------------------------------


def _non_request(uses: list[StrategyUse]) -> list[StrategyUse]:
    return [u for u in uses if u.trigger != "request"]


def current_cycle_slots(state: TutorState) -> list[StrategyUse]:
    """Non-request deliveries consumed in the CURRENT cycle, anchored on state.cycle."""
    return _non_request(state.strategies_used)[CYCLE_SIZE * (state.cycle - 1):]


def delivery_cycles(strategies_used: list[StrategyUse]) -> list[int]:
    """Cycle number of each entry, in order.

    A non-request entry at position i among the non-request entries is in cycle i // 4 + 1.
    A request entry belongs to the cycle of the most recent non-request entry before it
    (cycle 1 if there is none). The episode log reuses this.
    """
    cycles: list[int] = []
    non_request_seen = 0
    last_cycle = 1
    for use in strategies_used:
        if use.trigger == "request":
            cycles.append(last_cycle)
        else:
            last_cycle = non_request_seen // CYCLE_SIZE + 1
            cycles.append(last_cycle)
            non_request_seen += 1
    return cycles


# --- validation of the echoed (untrusted) state ----------------------------------------


def validate_state(state: TutorState, cfg: EngineConfig) -> None:
    for use in state.strategies_used:
        if use.strategy not in _STRATEGIES:
            raise InvalidStateError(f"unknown strategy in state: {use.strategy!r}")
        if use.trigger not in _TRIGGERS:
            raise InvalidStateError(f"unknown trigger in state: {use.trigger!r}")
    if isinstance(state.cycle, bool) or not 1 <= state.cycle <= cfg.max_cycles:
        raise InvalidStateError(f"cycle {state.cycle!r} outside 1..{cfg.max_cycles}")
    non_request = _non_request(state.strategies_used)
    n = len(non_request)
    if n > CYCLE_SIZE * state.cycle or n < CYCLE_SIZE * (state.cycle - 1):
        raise InvalidStateError(
            f"{n} non-request deliveries impossible in cycle {state.cycle} "
            f"(expected {CYCLE_SIZE * (state.cycle - 1)}..{CYCLE_SIZE * state.cycle})"
        )
    if state.awaiting_cycle_confirmation:
        if len(current_cycle_slots(state)) != CYCLE_SIZE:
            raise InvalidStateError("awaiting cycle confirmation before all four strategies were used")
        if state.cycle >= cfg.max_cycles:
            # Extra invariant, reported to the lead: an offer is only made when cycle < max_cycles.
            raise InvalidStateError("awaiting cycle confirmation in the final cycle")
    for start in range(0, n, CYCLE_SIZE):
        chunk = [u.strategy for u in non_request[start:start + CYCLE_SIZE]]
        if len(set(chunk)) != len(chunk):
            raise InvalidStateError(f"non-request strategy repeated within cycle {start // CYCLE_SIZE + 1}")


# --- decisions -----------------------------------------------------------------------------


def _fresh_state(new_episode_id: Callable[[], str]) -> TutorState:
    return TutorState(
        episode_id=new_episode_id(),
        cycle=1,
        strategies_used=[],
        awaiting_cycle_confirmation=False,
        prior_explanations=[],
    )


def _with(state: TutorState, **changes) -> TutorState:
    """A NEW state (deep copy of the input with changes applied); the input is never mutated."""
    return state.model_copy(deep=True, update=changes)


def _explain(state: TutorState, strategy: Strategy, trigger: Trigger) -> Decision:
    uses = [u.model_copy() for u in state.strategies_used]
    uses.append(StrategyUse(strategy=strategy, trigger=trigger))
    new_state = _with(state, strategies_used=uses, awaiting_cycle_confirmation=False)
    return Decision("explain", strategy, trigger, new_state)


def _trigger_for(state: TutorState) -> Trigger:
    return "default" if not state.strategies_used else "confusion"


def _order(state: TutorState, cfg: EngineConfig) -> tuple[Strategy, ...]:
    return personalised_order(state, cfg) if cfg.personalise else DEFAULT_ORDER


def _deliver_next(state: TutorState, cfg: EngineConfig) -> Decision:
    """Next unused strategy of the current cycle, else offer a new cycle / end."""
    used = {u.strategy for u in current_cycle_slots(state)}
    nxt = next((s for s in _order(state, cfg) if s not in used), None)
    if nxt is not None:
        return _explain(state, nxt, _trigger_for(state))
    if state.cycle < cfg.max_cycles:
        return Decision("offer_new_cycle", None, None, _with(state, awaiting_cycle_confirmation=True))
    return _end_unresolved(state)


def _end_unresolved(state: TutorState) -> Decision:
    return Decision(
        "end_unresolved", None, None, _with(state, awaiting_cycle_confirmation=False),
        outcome="end_unresolved",
    )


def next_action(
    state: TutorState | None,
    label: Label,
    request: Strategy | None,
    message: str,
    cfg: EngineConfig = EngineConfig(),
    new_episode_id: Callable[[], str] = default_episode_id,
    request_is_confusion: bool = False,
) -> Decision:
    """Decide what the tutor does next. `state` is None on the first message of a topic.

    request_is_confusion: the caller says the RULE layer judged this message confused. See the
    comment at the Tier 2 branch."""
    if label not in ("confused", "understood"):
        raise ValueError(f"unknown label: {label!r}")
    if request is not None and request not in _STRATEGIES:
        raise ValueError(f"unknown requested strategy: {request!r}")

    if state is None:
        state = _fresh_state(new_episode_id)
    else:
        validate_state(state, cfg)

    if state.awaiting_cycle_confirmation:
        intent = detect_cycle_intent(message)
        if intent == "accept":
            # New cycle: cycle + 1, availability is derived from the new cycle (so it is
            # reset), history is kept, and the first strategy is delivered this turn.
            return _deliver_next(_with(state, cycle=state.cycle + 1, awaiting_cycle_confirmation=False), cfg)
        if intent == "decline":
            return _end_unresolved(state)
        return Decision("clarify", None, None, _with(state))  # flag stays True

    if request is not None:  # Tier 2
        # `trigger` answers WHY a delivery happened; the strategy records WHICH was chosen.
        # "I don't understand, explain the theory again" happened because of confusion, and
        # `counted_strategies` / `is_weak` measure difficulty, so it must count. Rule-layer
        # confusion only, never the model's: the model scores "that makes sense" at 0.99
        # confused, so letting model-confusion override a request would turn nearly every request
        # into confusion and inflate `is_weak`. Rules are the high-precision signal; only they
        # earn this override. Do not "improve" this by including the model (the caller passes
        # request_is_confusion=True only for rule-sourced confusion).
        # The repeat case: a strategy already delivered as a COUNTED delivery in this cycle stays
        # "request", or counting it again would repeat a strategy within the cycle and break the
        # four-per-cycle arithmetic the cycle derivation depends on.
        trigger: Trigger = "request"
        if request_is_confusion and request not in {u.strategy for u in current_cycle_slots(state)}:
            trigger = "confusion"
        return _explain(state, request, trigger)

    if label == "understood" and state.strategies_used:
        return Decision(
            "resolved", None, None, _with(state),
            outcome="resolved", winning_strategy=state.strategies_used[-1].strategy,
        )

    return _deliver_next(state, cfg)

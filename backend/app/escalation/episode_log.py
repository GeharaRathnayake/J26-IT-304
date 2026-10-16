"""Episode log builder: the research artifact (weakness record, evidence for claim C6).

Pure function: no FastAPI, no I/O, no logging of student text. The log is returned only on the
two terminal actions (resolved, end_unresolved); the service stores nothing. Route wiring is a
later stage. The classifier behind the labels is a prototype proxy trained on synthetic
answers, so these labels are a proxy signal, not a measurement of confusion.

Counting: `counted_strategies` excludes only trigger "request" (claim C6); "default" COUNTS, so
the opening explanation is one of the three that make an episode weak. This matches the
proposal's "three or more strategies to grasp a concept". `default` is NOT guaranteed to be
present in an episode: one that opens with a request has no `default` delivery, so log
analysis must not assume one.

`started_at` is the `ts` of the first `history` turn and is CLIENT-REPORTED.

THE REACTION. Each delivery's student_label / probability / source record how the student
reacted to THAT delivery: the classification of the student message the service acted on next.
The service is stateless and TutorState does not carry these, so they are recomputed by
classifying the reaction message again. Never copy the current turn's classification onto every
delivery (the prototype mockTransport.ts does, which fabricates the research log).

Which message is the reaction: the LAST student turn before the next tutor turn of any kind.
If no tutor turn follows (the final delivery), it is the CURRENT message, whose classification
the caller already has. "The first student reply" would be wrong: a failed send leaves the
student's message in `history` with no tutor reply, so two student turns can be adjacent and the
first was never processed by the service.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from app.escalation.engine import Decision, delivery_cycles
from app.escalation.question_guard import r6_applies
from app.escalation.request_detector import detect_request
from app.escalation.resolution_guard import r7_applies
from app.schemas import Delivery, EpisodeLog, HistoryTurn, TutorState

_TERMINAL = ("resolved", "end_unresolved")


class EpisodeLogError(ValueError):
    """The echoed history and state contradict each other (or the decision is not terminal);
    an honest log cannot be built. Never guess, pad or fill in."""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_z(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def weak_rule_text(threshold: int) -> str:
    return f"counted_strategies >= {threshold} OR outcome == end_unresolved"


def _check_consistency(history: list[HistoryTurn], state: TutorState) -> list[int]:
    """Indices of the tutor turns that delivered a strategy, which must match
    state.strategies_used one for one, in count and in order."""
    delivery_idx = [i for i, t in enumerate(history) if t.role == "tutor" and t.strategy is not None]
    in_history = [history[i].strategy for i in delivery_idx]
    in_state = [u.strategy for u in state.strategies_used]
    if in_history != in_state:
        raise EpisodeLogError(
            f"history and state disagree: history has tutor deliveries {in_history}, "
            f"state.strategies_used has {in_state}"
        )
    return delivery_idx


def _reaction_turn_indices(history: list[HistoryTurn], delivery_idx: list[int]) -> list[int | None]:
    """For each delivery, the index of its reaction turn in `history`, or None for a delivery
    with no tutor turn after it (the reaction is then the current message)."""
    tutor_idx = [i for i, t in enumerate(history) if t.role == "tutor"]
    reactions: list[int | None] = []
    for i in delivery_idx:
        next_tutor = next((j for j in tutor_idx if j > i), None)
        if next_tutor is None:
            reactions.append(None)
            continue
        students = [k for k in range(i + 1, next_tutor) if history[k].role == "student"]
        if not students:
            raise EpisodeLogError(f"no student reaction between tutor turns {i} and {next_tutor}")
        reactions.append(students[-1])
    return reactions


def build_episode_log(
    *,
    decision: Decision,
    state: TutorState,
    history: list[HistoryTurn],
    current_reaction: Any,
    classify_fn: Callable[[str], Any],
    student_id: str,
    topic: str,
    model_version: str,
    weak_threshold: int,
    now: Callable[[], datetime] = utc_now,
) -> EpisodeLog:
    """Build the log for a terminal turn.

    decision: the engine's terminal Decision. state: the echoed (validated) state, whose
    strategies_used are the deliveries. history: as the client sent it (excludes the current
    message). current_reaction: the classification of the CURRENT message (label, probability,
    source), already computed by the caller. classify_fn(text) -> same shape, injected.
    """
    if decision.action not in _TERMINAL:
        raise EpisodeLogError(f"an episode log is only built on a terminal action, got {decision.action!r}")
    if decision.updated_state.strategies_used != state.strategies_used:
        raise EpisodeLogError("decision and state disagree about the deliveries")
    if not history:
        raise EpisodeLogError("history is empty: cannot determine when the episode started")

    delivery_idx = _check_consistency(history, state)
    reaction_idx = _reaction_turn_indices(history, delivery_idx)
    cycles = delivery_cycles(state.strategies_used)

    deliveries: list[Delivery] = []
    for n, (use, cycle, ridx) in enumerate(zip(state.strategies_used, cycles, reaction_idx), start=1):
        # Exact only because the classifier sees the current message alone (correction C2): it
        # is a pure function of one message, so classifying the reaction again returns exactly
        # what was computed live, bit for bit. A context-aware classifier (PP2, Experiment 2)
        # would need the same context rebuilt to re-derive the same result, and this shortcut
        # would stop being exact. Revisit this before changing the classifier's input.
        reaction = current_reaction if ridx is None else classify_fn(history[ridx].text)
        # R6 audit: the classifier's label is kept as it was; only a HISTORICAL reaction can carry the
        # flag. The current message never does: a resolving message was not a question, and an
        # end_unresolved one answered a cycle offer, where R6 does not apply.
        override = None
        if ridx is not None:
            text = history[ridx].text
            request = detect_request(text)
            if r6_applies(reaction.label, text, request):  # R6 first, then R7 (same precedence as the engine)
                override = "question_guard"
            elif r7_applies(reaction.label, reaction.source, text, request):
                override = "model_understood_not_trusted"
        deliveries.append(
            Delivery(
                seq=n,
                strategy=use.strategy,
                trigger=use.trigger,
                cycle=cycle,
                student_label=reaction.label,
                probability=reaction.probability,
                source=reaction.source,
                reaction_override=override,
            )
        )

    counted = sum(1 for u in state.strategies_used if u.trigger != "request")
    requested = sum(1 for u in state.strategies_used if u.trigger == "request")
    return EpisodeLog(
        schema_version="1.0",
        episode_id=state.episode_id,
        student_id=student_id,
        topic=topic,
        started_at=history[0].ts,
        ended_at=_iso_z(now()),
        outcome=decision.outcome,
        cycles=state.cycle,
        deliveries=deliveries,
        counted_strategies=counted,
        requested_strategies=requested,
        winning_strategy=decision.winning_strategy,
        winning_combination=[u.strategy for u in state.strategies_used],
        is_weak=counted >= weak_threshold or decision.outcome == "end_unresolved",
        weak_rule=weak_rule_text(weak_threshold),
        model_version=model_version,
    )

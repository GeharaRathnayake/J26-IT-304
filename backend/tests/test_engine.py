"""Escalation engine tests: one per transition, named for the behaviour.

The label fed to the engine comes from the prototype hybrid classifier (a proxy trained on
synthetic answers); here it is supplied directly. All strings are hand-written.
"""

import copy

import pytest

from app.config import Settings
from app.escalation.engine import (
    DEFAULT_ORDER,
    Decision,
    EngineConfig,
    InvalidStateError,
    current_cycle_slots,
    delivery_cycles,
    next_action,
    personalised_order,
)
from app.escalation.request_detector import detect_request
from app.schemas import StrategyUse, TutorState

CFG = EngineConfig()


def eid():
    return "ep_test"


def uses(*pairs):
    return [StrategyUse(strategy=s, trigger=t) for s, t in pairs]


def state(cycle=1, used=(), awaiting=False, prior=()):
    return TutorState(
        episode_id="ep_1", cycle=cycle, strategies_used=uses(*used),
        awaiting_cycle_confirmation=awaiting, prior_explanations=list(prior),
    )


CYCLE1 = [("theory", "default"), ("example", "confusion"), ("simplified", "confusion"), ("analogy", "confusion")]


def step(st, label="confused", message="hmm", cfg=CFG):
    """One turn as the pipeline will run it: detect the request, then ask the engine."""
    return next_action(st, label, detect_request(message), message, cfg, new_episode_id=eid)


def pairs(st):
    return [(u.strategy, u.trigger) for u in st.strategies_used]


# --- single transitions -----------------------------------------------------------------------


def test_first_message_explains_theory_with_default_trigger():
    d = step(None)
    assert (d.action, d.strategy, d.trigger) == ("explain", "theory", "default")
    s = d.updated_state
    assert (s.episode_id, s.cycle, s.awaiting_cycle_confirmation) == ("ep_test", 1, False)
    assert pairs(s) == [("theory", "default")]
    assert s.prior_explanations == []


def test_confused_delivers_next_unused_strategy_with_confusion_trigger():
    d = step(state(used=[("theory", "default")]))
    assert (d.action, d.strategy, d.trigger) == ("explain", "example", "confusion")


def test_requested_strategy_has_request_trigger_and_does_not_consume_a_slot():
    st = state(used=[("theory", "default")])
    d = step(st, message="can i see an analogy")  # 'analogy' pattern
    assert (d.action, d.strategy, d.trigger) == ("explain", "analogy", "request")
    assert pairs(d.updated_state) == [("theory", "default"), ("analogy", "request")]
    non_request = lambda s: [u for u in s.strategies_used if u.trigger != "request"]
    assert len(non_request(d.updated_state)) == len(non_request(st)) == 1


def test_c6_default_order_continues_where_it_was_after_a_request():
    st = step(None).updated_state  # theory
    st = step(st, "confused", "hmm").updated_state  # example
    st = step(st, "confused", "give me an analogy").updated_state  # request analogy
    d = step(st, "confused", "still lost")
    assert (d.strategy, d.trigger) == ("simplified", "confusion")  # as if no request happened
    d2 = step(d.updated_state, "confused", "still lost")
    assert (d2.strategy, d2.trigger) == ("analogy", "confusion")  # analogy slot was never consumed
    assert d2.updated_state.strategies_used[-1].trigger == "confusion"


def test_understood_after_a_delivery_resolves_with_the_last_delivered_winner():
    st = state(used=[("theory", "default"), ("example", "confusion")])
    d = step(st, "understood", "ok")
    assert (d.action, d.outcome, d.winning_strategy) == ("resolved", "resolved", "example")
    assert d.strategy is None and d.trigger is None
    assert d.updated_state == st


def test_understood_with_zero_deliveries_does_not_resolve():
    d = step(None, "understood", "ok")
    assert (d.action, d.strategy, d.trigger) == ("explain", "theory", "default")
    assert d.outcome is None and d.winning_strategy is None


def test_request_overrides_an_understood_label():
    d = step(state(used=[("theory", "default")]), "understood", "show me")
    assert (d.action, d.strategy, d.trigger) == ("explain", "example", "request")


def test_four_used_in_cycle_one_then_confused_offers_new_cycle_with_flag_true():
    d = step(state(used=CYCLE1))
    assert d.action == "offer_new_cycle"
    assert d.updated_state.awaiting_cycle_confirmation is True
    assert d.strategy is None and d.trigger is None
    assert pairs(d.updated_state) == CYCLE1 and d.updated_state.cycle == 1


def test_pending_offer_yes_starts_cycle_two_and_delivers_theory_in_the_same_turn():
    st = state(used=CYCLE1, awaiting=True)
    d = step(st, "understood", "yes")  # even a classifier 'understood' on 'yes' must not resolve
    assert (d.action, d.strategy, d.trigger) == ("explain", "theory", "confusion")
    s = d.updated_state
    assert (s.cycle, s.awaiting_cycle_confirmation) == (2, False)
    assert pairs(s) == CYCLE1 + [("theory", "confusion")]  # cycle 1 is still all there


def test_pending_offer_no_ends_unresolved_and_clears_the_flag():
    d = step(state(used=CYCLE1, awaiting=True), message="no")
    assert (d.action, d.outcome, d.winning_strategy) == ("end_unresolved", "end_unresolved", None)
    assert d.updated_state.awaiting_cycle_confirmation is False
    assert pairs(d.updated_state) == CYCLE1


def test_pending_offer_unclear_clarifies_and_keeps_the_flag_true():
    st = state(used=CYCLE1, awaiting=True, prior=["x"])
    d = step(st, message="wait, what do you mean?")
    assert d.action == "clarify"
    assert d.updated_state.awaiting_cycle_confirmation is True
    assert d.updated_state == st and d.updated_state is not st


def test_pending_offer_request_does_not_bypass_the_offer():
    d = step(state(used=CYCLE1, awaiting=True), message="show me an example")
    assert d.action == "clarify"
    assert d.updated_state.awaiting_cycle_confirmation is True


def test_cycle_two_exhausted_ends_unresolved():
    full = CYCLE1 + [("theory", "confusion"), ("example", "confusion"), ("simplified", "confusion"), ("analogy", "confusion")]
    d = step(state(cycle=2, used=full))
    assert (d.action, d.outcome) == ("end_unresolved", "end_unresolved")
    assert d.updated_state.awaiting_cycle_confirmation is False


def test_request_as_the_very_first_message_then_confused_gets_theory_with_confusion_trigger():
    d = step(None, "confused", "show me")
    assert (d.action, d.strategy, d.trigger) == ("explain", "example", "request")
    d2 = step(d.updated_state, "confused", "hmm")
    assert (d2.strategy, d2.trigger) == ("theory", "confusion")  # the rule as written, pinned


def test_requested_strategy_may_repeat_within_a_cycle():
    st = state(used=[("example", "confusion")])
    d = step(st, message="show me")
    assert (d.strategy, d.trigger) == ("example", "request")


def test_resolution_winner_can_be_a_requested_strategy():
    st = state(used=[("theory", "default"), ("analogy", "request")])
    assert step(st, "understood", "ok").winning_strategy == "analogy"


# --- cycle derivation, anchored on state.cycle ---------------------------------------------------


def test_cycle_one_with_four_used_has_all_four_consumed_so_the_offer_happens():
    consumed = current_cycle_slots(state(used=CYCLE1))
    assert len(consumed) == 4  # all four consumed: NOT "boundary passed, four available again"
    d = step(state(used=CYCLE1))
    assert d.action == "offer_new_cycle"  # and in particular not an explain of theory again


def test_cycle_one_four_plus_two_requests_then_two_in_cycle_two_leaves_exactly_two_available():
    eight = (
        CYCLE1
        + [("example", "request"), ("analogy", "request")]
        + [("theory", "confusion"), ("example", "confusion")]
    )
    st = state(cycle=2, used=eight)
    assert len(st.strategies_used) == 8
    d1 = step(st)
    assert (d1.action, d1.strategy) == ("explain", "simplified")
    d2 = step(d1.updated_state)
    assert (d2.action, d2.strategy) == ("explain", "analogy")
    d3 = step(d2.updated_state)
    assert d3.action == "end_unresolved"  # cycle 2 is the last cycle
    assert pairs(d2.updated_state)[:8] == eight  # nothing was cleared or reordered
    assert len(d2.updated_state.strategies_used) == 10


def test_current_cycle_slots_in_cycle_two():
    st = state(cycle=2, used=CYCLE1 + [("theory", "confusion")])
    assert [u.strategy for u in current_cycle_slots(st)] == ["theory"]


# --- delivery_cycles ---------------------------------------------------------------------------


def test_delivery_cycles_basic_two_cycles():
    all8 = CYCLE1 + [("theory", "confusion"), ("example", "confusion"), ("simplified", "confusion"), ("analogy", "confusion")]
    assert delivery_cycles(uses(*all8)) == [1, 1, 1, 1, 2, 2, 2, 2]


def test_delivery_cycles_request_after_fourth_non_request_belongs_to_cycle_one():
    assert delivery_cycles(uses(*CYCLE1, ("example", "request"))) == [1, 1, 1, 1, 1]


def test_delivery_cycles_request_before_any_non_request_is_cycle_one():
    assert delivery_cycles(uses(("example", "request"), ("theory", "default"))) == [1, 1]


def test_delivery_cycles_request_inside_cycle_two_follows_the_latest_non_request():
    seq = uses(*CYCLE1, ("theory", "confusion"), ("analogy", "request"), ("example", "confusion"))
    assert delivery_cycles(seq) == [1, 1, 1, 1, 2, 2, 2]


def test_delivery_cycles_four_plus_two_requests_plus_two():
    seq = uses(*CYCLE1, ("example", "request"), ("analogy", "request"), ("theory", "confusion"), ("example", "confusion"))
    assert delivery_cycles(seq) == [1, 1, 1, 1, 1, 1, 2, 2]


def test_delivery_cycles_empty():
    assert delivery_cycles([]) == []


# --- full episodes ---------------------------------------------------------------------------------


def test_no_non_request_strategy_repeats_within_a_cycle_over_a_full_two_cycle_episode():
    st = None
    delivered = []
    messages = ["hmm"] * 4 + ["yes"] + ["hmm"] * 4
    for message in messages[:4]:
        d = step(st, "confused", message)
        st = d.updated_state
    d = step(st, "confused", "hmm")  # fifth confused turn -> offer
    assert d.action == "offer_new_cycle"
    st = d.updated_state
    d = step(st, "confused", "yes")
    st = d.updated_state
    for _ in range(3):
        d = step(st, "confused", "hmm")
        st = d.updated_state
    non_request = [u.strategy for u in st.strategies_used if u.trigger != "request"]
    assert non_request[:4] == list(DEFAULT_ORDER) and non_request[4:] == list(DEFAULT_ORDER)
    assert len(set(non_request[:4])) == 4 and len(set(non_request[4:])) == 4


def test_full_episode_end_to_end_cycle_one_through_cycle_two():
    turns = [
        ("confused", "hmm"),
        ("confused", "hmm"),
        ("confused", "hmm"),
        ("confused", "hmm"),
        ("confused", "hmm"),  # offer
        ("confused", "yes"),  # accept -> theory in cycle 2
        ("confused", "hmm"),
        ("confused", "hmm"),
        ("confused", "hmm"),
        ("confused", "hmm"),  # exhausted
    ]
    st, seq = None, []
    for label, message in turns:
        d = step(st, label, message)
        st = d.updated_state
        seq.append((d.action, d.strategy, d.trigger))
    assert seq == [
        ("explain", "theory", "default"),
        ("explain", "example", "confusion"),
        ("explain", "simplified", "confusion"),
        ("explain", "analogy", "confusion"),
        ("offer_new_cycle", None, None),
        ("explain", "theory", "confusion"),
        ("explain", "example", "confusion"),
        ("explain", "simplified", "confusion"),
        ("explain", "analogy", "confusion"),
        ("end_unresolved", None, None),
    ]
    assert st.cycle == 2 and len(st.strategies_used) == 8
    assert st.awaiting_cycle_confirmation is False


def test_full_episode_resolving_in_cycle_two():
    st = state(cycle=2, used=CYCLE1 + [("theory", "confusion")])
    d = step(st, "understood", "ok")
    assert (d.action, d.winning_strategy) == ("resolved", "theory")


# --- purity: nothing is mutated, prior_explanations passes through -----------------------------


@pytest.mark.parametrize(
    "st, label, message",
    [
        (None, "confused", "hmm"),
        (state(used=[("theory", "default")], prior=["a"]), "confused", "hmm"),
        (state(used=[("theory", "default")], prior=["a"]), "confused", "show me"),
        (state(used=[("theory", "default")], prior=["a"]), "understood", "ok"),
        (state(used=CYCLE1, prior=["a", "b", "c", "d"]), "confused", "hmm"),
        (state(used=CYCLE1, awaiting=True, prior=["a"]), "confused", "yes"),
        (state(used=CYCLE1, awaiting=True, prior=["a"]), "confused", "no"),
        (state(used=CYCLE1, awaiting=True, prior=["a"]), "confused", "hmm"),
    ],
    ids=["first", "confused", "request", "resolve", "offer", "accept", "decline", "clarify"],
)
def test_input_state_is_never_mutated_and_prior_explanations_pass_through(st, label, message):
    before = copy.deepcopy(st)
    d = step(st, label, message)
    assert st == before
    assert isinstance(d, Decision)
    if st is not None:
        assert d.updated_state is not st
        assert d.updated_state.prior_explanations == st.prior_explanations
        assert d.updated_state.strategies_used is not st.strategies_used
        # editing the output must not reach the input either
        d.updated_state.strategies_used.append(StrategyUse(strategy="theory", trigger="request"))
        d.updated_state.prior_explanations.append("changed")
        assert st == before


def test_decision_is_immutable():
    d = step(None)
    with pytest.raises(Exception):
        d.action = "resolved"


def test_strategy_and_trigger_are_set_only_for_explain():
    for st, label, message in [
        (state(used=CYCLE1), "confused", "hmm"),
        (state(used=[("theory", "default")]), "understood", "ok"),
        (state(used=CYCLE1, awaiting=True), "confused", "hmm"),
        (state(used=CYCLE1, awaiting=True), "confused", "no"),
    ]:
        d = step(st, label, message)
        assert d.action != "explain" and d.strategy is None and d.trigger is None


# --- InvalidStateError ------------------------------------------------------------------------------


def bad_state(**fields):
    base = dict(episode_id="e", cycle=1, strategies_used=[], awaiting_cycle_confirmation=False, prior_explanations=[])
    base.update(fields)
    return TutorState.model_construct(**base)  # bypasses request validation, like a hostile caller


def raw_uses(*pairs):
    return [StrategyUse.model_construct(strategy=s, trigger=t) for s, t in pairs]


INVALID = {
    "cycle-zero": bad_state(cycle=0),
    "cycle-above-max": bad_state(cycle=3),
    "cycle-negative": bad_state(cycle=-1),
    "cycle-bool": bad_state(cycle=True),
    "non-request-above-4-times-cycle": bad_state(strategies_used=raw_uses(*CYCLE1, ("theory", "confusion"))),
    "non-request-below-lower-bound": bad_state(cycle=2, strategies_used=raw_uses(("theory", "default"))),
    "awaiting-with-too-few": bad_state(awaiting_cycle_confirmation=True, strategies_used=raw_uses(("theory", "default"))),
    "awaiting-in-final-cycle": bad_state(cycle=2, awaiting_cycle_confirmation=True, strategies_used=raw_uses(*CYCLE1, *[(s, "confusion") for s in DEFAULT_ORDER])),
    "repeat-within-cycle": bad_state(strategies_used=raw_uses(("theory", "default"), ("theory", "confusion"))),
    "repeat-within-cycle-two": bad_state(
        cycle=2,
        strategies_used=raw_uses(*CYCLE1, ("theory", "confusion"), ("theory", "confusion")),
    ),
    "unknown-strategy": bad_state(strategies_used=raw_uses(("lecture", "default"))),
    "unknown-trigger": bad_state(strategies_used=raw_uses(("theory", "whenever"))),
}


@pytest.mark.parametrize("name", list(INVALID))
def test_invalid_state_is_rejected(name):
    with pytest.raises(InvalidStateError):
        step(INVALID[name])


def test_requests_do_not_count_toward_the_state_bounds():
    ok = state(used=[("theory", "default")] + [("example", "request")] * 6)
    assert step(ok).action == "explain"  # six requests, one real slot: valid


def test_valid_boundary_states_are_accepted():
    for st in (
        state(used=CYCLE1),  # cycle 1 full, offer not yet made
        state(used=CYCLE1, awaiting=True),
        state(cycle=2, used=CYCLE1),  # just accepted
        state(cycle=2, used=CYCLE1 + [(s, "confusion") for s in DEFAULT_ORDER]),
    ):
        step(st)


def test_unknown_label_or_request_is_a_programming_error():
    with pytest.raises(ValueError):
        next_action(None, "maybe", None, "x")
    with pytest.raises(ValueError):
        next_action(None, "confused", "lecture", "x")


# --- Tier 3 seam and config -----------------------------------------------------------------------------


def test_personalise_off_uses_the_default_order():
    d = step(state(used=[("theory", "default")]), cfg=EngineConfig(personalise=False))
    assert d.strategy == "example"


def test_personalise_on_raises_not_implemented():
    with pytest.raises(NotImplementedError, match="personalised ordering is PP2"):
        step(state(used=[("theory", "default")]), cfg=EngineConfig(personalise=True))
    with pytest.raises(NotImplementedError, match="PP2"):
        personalised_order(state(), CFG)


def test_settings_defaults_feed_the_engine_config(monkeypatch):
    for var in ("MAX_CYCLES", "PERSONALISE"):
        monkeypatch.delenv(var, raising=False)
    settings = Settings(_env_file=None)
    assert (settings.MAX_CYCLES, settings.PERSONALISE) == (2, False)
    cfg = EngineConfig.from_settings(settings)
    assert (cfg.max_cycles, cfg.personalise) == (2, False)


def test_max_cycles_is_configurable():
    one = EngineConfig(max_cycles=1)
    assert step(state(used=CYCLE1), cfg=one).action == "end_unresolved"  # no second cycle to offer
    three = EngineConfig(max_cycles=3)
    d = step(state(cycle=2, used=CYCLE1 + [(s, "confusion") for s in DEFAULT_ORDER]), cfg=three)
    assert d.action == "offer_new_cycle"


def test_default_episode_id_shape():
    from app.escalation.engine import default_episode_id

    a, b = default_episode_id(), default_episode_id()
    assert a.startswith("ep_") and len(a) == 11 and a != b

# --- the confusion override (lead ruling, S6b): request_is_confusion ----------------------------------


def override(st, request, message="hmm", label="confused"):
    return next_action(st, label, request, message, CFG, new_episode_id=eid, request_is_confusion=True)


def test_override_first_message_request_becomes_a_counted_confusion_delivery():
    d = override(None, "theory")
    assert (d.action, d.strategy, d.trigger) == ("explain", "theory", "confusion")
    assert pairs(d.updated_state) == [("theory", "confusion")]


def test_override_is_off_by_default_so_a_plain_request_stays_a_request():
    d = next_action(None, "confused", "theory", "hmm", CFG, new_episode_id=eid)
    assert d.trigger == "request"


def test_override_applies_when_the_strategy_is_unused_in_the_current_cycle():
    st = state(used=[("theory", "default")])
    d = override(st, "analogy")
    assert (d.strategy, d.trigger) == ("analogy", "confusion")
    # and it is a real slot now: the default order skips it
    d2 = next_action(d.updated_state, "confused", None, "hmm", CFG)
    assert (d2.strategy, d2.trigger) == ("example", "confusion")


def test_documented_limitation_repeat_of_a_counted_strategy_stays_request():
    # Counting it again would repeat a strategy within the cycle and break the four-per-cycle
    # arithmetic the cycle derivation depends on, so the override does not apply.
    st = state(used=[("theory", "default")])
    d = override(st, "theory")
    assert (d.strategy, d.trigger) == ("theory", "request")
    assert len([u for u in d.updated_state.strategies_used if u.trigger != "request"]) == 1


def test_override_does_not_break_the_four_per_cycle_arithmetic():
    st = state(used=CYCLE1)  # every strategy already counted in cycle 1
    for request in DEFAULT_ORDER:
        d = override(st, request)
        assert d.trigger == "request"
    # the next confused turn still offers the new cycle
    assert step(override(st, "example").updated_state).action == "offer_new_cycle"


def test_override_looks_at_the_current_cycle_only():
    st = state(cycle=2, used=CYCLE1 + [("example", "confusion")])
    assert override(st, "theory").trigger == "confusion"  # theory was used in cycle 1, not cycle 2
    assert override(st, "example").trigger == "request"  # example is used in cycle 2


def test_override_never_bypasses_a_pending_offer():
    d = override(state(used=CYCLE1, awaiting=True), "example", message="show me")
    assert d.action == "clarify" and d.updated_state.awaiting_cycle_confirmation is True

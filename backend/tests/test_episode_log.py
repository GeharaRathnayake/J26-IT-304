"""Episode log builder tests.

The labels come from the prototype hybrid classifier (a proxy trained on synthetic answers);
the log records how students reacted to each delivery according to that proxy. All strings
are hand-written.
"""

import copy
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.classifier.hybrid import classify
from app.classifier.model import load_model
from app.config import DEFAULT_MODELS_DIR, Settings
from app.escalation.engine import EngineConfig, next_action
from app.escalation.episode_log import (
    EpisodeLogError,
    build_episode_log,
    utc_now,
    weak_rule_text,
)
from app.escalation.request_detector import detect_request
from app.schemas import EpisodeLog, HistoryTurn, StrategyUse, TutorState

TESTS_DIR = Path(__file__).resolve().parent
FIXTURE = TESTS_DIR / "contract_fixtures" / "episode-log.json"
FRONTEND_SOURCE = (
    TESTS_DIR.parents[1] / "frontend" / "src" / "features" / "tutor" / "api" / "fixtures" / "episode-log.json"
)
NOW = lambda: datetime(2026, 10, 8, 10, 6, 40, tzinfo=timezone.utc)  # noqa: E731
TS = "2026-10-08T10:01:00Z"


@dataclass
class R:
    label: str
    probability: float
    source: str


def st_turn(text):
    return HistoryTurn(role="student", text=text, ts=TS)


def tu_turn(strategy=None):
    return HistoryTurn(role="tutor", text="t", strategy=strategy, ts=TS)


def history(*spec):
    """'S:text' = student turn, 'T:theory' = tutor delivery, 'T:-' = tutor turn with no strategy."""
    out = []
    for item in spec:
        kind, value = item.split(":", 1)
        out.append(st_turn(value) if kind == "S" else tu_turn(None if value == "-" else value))
    return out


def state(used, cycle=1, awaiting=False):
    return TutorState(
        episode_id="ep_77d1", cycle=cycle,
        strategies_used=[StrategyUse(strategy=s, trigger=t) for s, t in used],
        awaiting_cycle_confirmation=awaiting, prior_explanations=[],
    )


class Recorder:
    """Stub classify_fn: records inputs, returns a distinct result per text."""

    def __init__(self, table=None):
        self.calls = []
        self.table = table or {}

    def __call__(self, text):
        self.calls.append(text)
        return self.table.get(text, R("confused", 0.5, "model"))


def build(decision, st, hist, current, fn, weak_threshold=3):
    return build_episode_log(
        decision=decision, state=st, history=hist, current_reaction=current, classify_fn=fn,
        student_id="stu_8f3a", topic="inheritance", model_version="clf-v1.0.0",
        weak_threshold=weak_threshold, now=NOW,
    )


FIXTURE_USED = [("theory", "default"), ("example", "confusion"), ("analogy", "request")]
FIXTURE_HISTORY = history("S:first question", "T:theory", "S:r1", "T:example", "S:r2", "T:analogy")
FIXTURE_TABLE = {"r1": R("confused", 0.74, "model"), "r2": R("confused", 0.81, "rule")}
FIXTURE_CURRENT = R("understood", 0.22, "model")


def resolved_decision(st, message="thanks"):
    return next_action(st, "understood", None, message, label_source="rule")


# --- shape: reproduce the fixture exactly ----------------------------------------------------


def test_built_log_equals_the_contract_fixture_exactly():
    st = state(FIXTURE_USED)
    log = build(resolved_decision(st), st, FIXTURE_HISTORY, FIXTURE_CURRENT, Recorder(FIXTURE_TABLE))
    expected = json.loads(FIXTURE.read_bytes())
    dumped = log.model_dump()
    # R6 added ONE additive field per delivery (null here); the contract's own keys are all present, in order.
    for built in dumped["deliveries"]:
        assert built.pop("reaction_override") is None
    assert dumped == expected
    assert list(dumped) == list(expected)  # same keys, same order
    for built, want in zip(dumped["deliveries"], expected["deliveries"]):
        assert list(built) == list(want)
        assert {k: type(v) for k, v in built.items()} == {k: type(v) for k, v in want.items()}
    EpisodeLog.model_validate(expected)  # the model accepts the contract's own instance


def test_scenario_counts_and_winner():
    st = state(FIXTURE_USED)
    log = build(resolved_decision(st), st, FIXTURE_HISTORY, FIXTURE_CURRENT, Recorder(FIXTURE_TABLE))
    assert (log.counted_strategies, log.requested_strategies) == (2, 1)
    assert log.winning_strategy == "analogy"
    assert log.winning_combination == ["theory", "example", "analogy"]
    assert log.is_weak is False and log.outcome == "resolved" and log.cycles == 1
    assert log.started_at == TS and log.ended_at == "2026-10-08T10:06:40Z"


def test_model_forbids_extra_fields():
    expected = json.loads(FIXTURE.read_bytes())
    with pytest.raises(Exception):
        EpisodeLog.model_validate({**expected, "surprise": 1})
    with pytest.raises(Exception):
        EpisodeLog.model_validate({**expected, "deliveries": [{**expected["deliveries"][0], "extra": 1}]})


@pytest.mark.parametrize("field, value", [("probability", 1.5), ("probability", -0.1), ("seq", 0), ("cycle", 0)])
def test_delivery_constraints_match_the_frontend_schema(field, value):
    expected = json.loads(FIXTURE.read_bytes())
    expected["deliveries"][0][field] = value
    with pytest.raises(Exception):
        EpisodeLog.model_validate(expected)


def test_empty_ids_are_rejected_like_the_frontend_schema():
    expected = json.loads(FIXTURE.read_bytes())
    for key in ("episode_id", "student_id", "topic"):
        with pytest.raises(Exception):
            EpisodeLog.model_validate({**expected, key: ""})


# --- counting and is_weak ------------------------------------------------------------------------


def make_log(used, outcome_decision="resolved", cycle=1, threshold=3):
    st = state(used, cycle=cycle)
    spec = ["S:q"]
    for i, (strategy, _) in enumerate(used):
        spec += [f"T:{strategy}"] + ([f"S:r{i}"] if i < len(used) - 1 else [])
    hist = history(*spec)
    if outcome_decision == "resolved":
        decision = next_action(st, "understood", None, "ok", label_source="rule")
    else:  # exhausted final cycle or similar: build an end_unresolved decision directly
        decision = next_action(st, "confused", None, "hmm", EngineConfig(max_cycles=cycle), label_source="rule")
    return build(decision, st, hist, R("understood", 0.2, "model"), Recorder(), threshold)


def test_three_counted_default_confusion_confusion_is_weak():
    log = make_log([("theory", "default"), ("example", "confusion"), ("simplified", "confusion")])
    assert (log.counted_strategies, log.requested_strategies, log.is_weak) == (3, 0, True)


def test_default_counts_toward_counted_strategies():
    log = make_log([("theory", "default"), ("example", "confusion")])
    assert log.counted_strategies == 2  # 'default' is not excluded


def test_default_request_confusion_is_two_counted_one_requested_and_not_weak():
    log = make_log([("theory", "default"), ("analogy", "request"), ("example", "confusion")])
    assert (log.counted_strategies, log.requested_strategies, log.is_weak) == (2, 1, False)


def test_requests_never_make_an_episode_weak():
    log = make_log([("theory", "default")] + [("example", "request")] * 5)
    assert (log.counted_strategies, log.requested_strategies, log.is_weak) == (1, 5, False)


def test_episode_opening_with_a_request_has_no_default_delivery():
    log = make_log([("example", "request"), ("theory", "confusion")])
    assert [d.trigger for d in log.deliveries] == ["request", "confusion"]


def test_any_end_unresolved_is_weak():
    full = [(s, "default" if i == 0 else "confusion") for i, s in enumerate(["theory", "example", "simplified", "analogy"])]
    log = make_log(full, outcome_decision="end_unresolved", cycle=1, threshold=99)
    assert log.outcome == "end_unresolved" and log.is_weak is True
    assert log.winning_strategy is None


def test_weak_rule_equals_the_fixture_string_at_the_default_threshold():
    fixture = json.loads(FIXTURE.read_bytes())
    assert weak_rule_text(Settings(_env_file=None).WEAK_THRESHOLD) == fixture["weak_rule"]
    log = make_log([("theory", "default")])
    assert log.weak_rule == fixture["weak_rule"]


def test_weak_rule_and_is_weak_follow_the_configured_threshold():
    used = [("theory", "default"), ("example", "confusion")]
    log = make_log(used, threshold=2)
    assert log.weak_rule == "counted_strategies >= 2 OR outcome == end_unresolved"
    assert log.is_weak is True
    assert make_log(used, threshold=3).is_weak is False


def test_weak_threshold_default_setting(monkeypatch):
    monkeypatch.delenv("WEAK_THRESHOLD", raising=False)
    assert Settings(_env_file=None).WEAK_THRESHOLD == 3


# --- cycles --------------------------------------------------------------------------------------------


def test_two_cycle_episode_with_requests_in_both_cycles_gets_the_right_cycle_numbers():
    used = [
        ("theory", "default"), ("example", "request"), ("example", "confusion"),
        ("simplified", "confusion"), ("analogy", "confusion"),
        ("theory", "confusion"), ("analogy", "request"), ("example", "confusion"),
    ]
    st = state(used, cycle=2)
    spec = ["S:q", "T:theory", "S:a", "T:example", "S:b", "T:example", "S:c", "T:simplified", "S:d", "T:analogy",
            "S:e", "T:-", "S:yes", "T:theory", "S:f", "T:analogy", "S:g", "T:example"]
    decision = next_action(st, "understood", None, "ok", label_source="rule")
    log = build(decision, st, history(*spec), R("understood", 0.1, "model"), Recorder())
    assert [d.cycle for d in log.deliveries] == [1, 1, 1, 1, 1, 2, 2, 2]
    assert [d.seq for d in log.deliveries] == list(range(1, 9))
    assert log.cycles == 2
    assert len(log.winning_combination) == 8


# --- the reaction rule -----------------------------------------------------------------------------------


def test_classify_fn_is_called_once_per_delivery_except_the_last_which_uses_current_reaction():
    st = state(FIXTURE_USED)
    rec = Recorder(FIXTURE_TABLE)
    log = build(resolved_decision(st), st, FIXTURE_HISTORY, FIXTURE_CURRENT, rec)
    assert rec.calls == ["r1", "r2"]
    assert (log.deliveries[-1].student_label, log.deliveries[-1].probability) == ("understood", 0.22)


def test_failed_send_reaction_is_the_last_student_turn_not_the_first():
    st = state([("theory", "default"), ("example", "confusion")])
    hist = history("S:a", "T:theory", "S:b", "S:c", "T:example")  # b failed: no tutor reply after it
    rec = Recorder({"b": R("confused", 0.11, "model"), "c": R("confused", 0.99, "rule")})
    log = build(resolved_decision(st), st, hist, R("understood", 0.3, "model"), rec)
    assert rec.calls == ["c"]
    assert (log.deliveries[0].probability, log.deliveries[0].source) == (0.99, "rule")


def test_trailing_failed_send_after_the_last_delivery_still_uses_current_reaction():
    st = state([("theory", "default")])
    hist = history("S:a", "T:theory", "S:failed attempt")
    rec = Recorder()
    log = build(resolved_decision(st), st, hist, R("understood", 0.42, "model"), rec)
    assert rec.calls == []
    assert log.deliveries[0].probability == 0.42


def test_offer_and_clarify_turns_between_deliveries_are_handled():
    four = [("theory", "default"), ("example", "confusion"), ("simplified", "confusion"), ("analogy", "confusion")]
    st = state(four, awaiting=True)
    hist = history(
        "S:q", "T:theory", "S:r1", "T:example", "S:r2", "T:simplified", "S:r3", "T:analogy",
        "S:r4", "T:-", "S:what do you mean", "T:-",
    )
    decision = next_action(st, "confused", None, "no", label_source="rule")  # decline the offer
    assert decision.action == "end_unresolved"
    rec = Recorder({"r4": R("confused", 0.9, "model")})
    log = build(decision, st, hist, R("confused", 0.5, "model"), rec)
    # the last delivery's reaction is r4 (before the offer turn), NOT 'what do you mean' or the current 'no'
    assert rec.calls == ["r1", "r2", "r3", "r4"]
    assert log.deliveries[-1].probability == 0.9


def test_accepting_a_new_cycle_does_not_make_yes_the_reaction_to_the_last_cycle_one_delivery():
    used = [("theory", "default"), ("example", "confusion"), ("simplified", "confusion"), ("analogy", "confusion"),
            ("theory", "confusion")]
    st = state(used, cycle=2)
    hist = history("S:q", "T:theory", "S:r1", "T:example", "S:r2", "T:simplified", "S:r3", "T:analogy",
                   "S:r4", "T:-", "S:yes", "T:theory")
    decision = next_action(st, "understood", None, "ok", label_source="rule")
    rec = Recorder()
    build(decision, st, hist, R("understood", 0.2, "model"), rec)
    # r4 (before the offer turn) reacts to the cycle-1 analogy; 'yes' is an answer to the offer, not a
    # reaction to any delivery; the cycle-2 theory is the last delivery, so the current message is its reaction.
    assert rec.calls == ["r1", "r2", "r3", "r4"]
    assert "yes" not in rec.calls


# --- the exactness test: live turn by turn with the real classifier and engine ------------------------


@pytest.fixture(scope="module")
def model():
    return load_model(DEFAULT_MODELS_DIR / "clf-v1.0.0")


class FrontendSim:
    """Builds `history` and `state` the way reducer.ts / episodeRules.ts do:
    history EXCLUDES the current message; a failed send leaves the student turn in history
    with no tutor reply; a tutor turn carries `strategy` only when it delivered one."""

    def __init__(self, model):
        self.model = model
        self.history, self.state = [], None
        self.live = {}  # delivery seq -> live classification of its reaction
        self.last_delivery_seq = None
        self.n_deliveries = 0
        self.log = None

    def fail(self, message):
        self.history.append(st_turn(message))  # SEND_STARTED, then SEND_FAILED: nothing else changes

    def send(self, message):
        sent_history = copy.deepcopy(self.history)
        sent_state = copy.deepcopy(self.state)
        self.history.append(st_turn(message))  # SEND_STARTED (after the request body was captured)
        result = classify(self.model, message)
        decision = next_action(sent_state, result.label, detect_request(message), message, EngineConfig(), label_source=result.source)
        if self.last_delivery_seq is not None:
            self.live[self.last_delivery_seq] = result  # this message reacts to the previous turn's delivery
        if decision.action == "explain":
            self.n_deliveries += 1
            self.last_delivery_seq = self.n_deliveries
        else:
            self.last_delivery_seq = None
        if decision.action in ("resolved", "end_unresolved"):
            self.log = build_episode_log(
                decision=decision, state=sent_state,
                history=sent_history, current_reaction=result,
                classify_fn=lambda text: classify(self.model, text),
                student_id="stu_test", topic="loops", model_version=self.model.version,
                weak_threshold=3, now=NOW,
            )
        self.history.append(
            HistoryTurn(role="tutor", text="reply", strategy=decision.strategy, ts=TS)
        )  # SEND_SUCCEEDED
        self.state = decision.updated_state
        return decision, result


def test_log_reactions_equal_the_live_classifications_exactly(model):
    sim = FrontendSim(model)
    sim.send("what is a loop")  # delivery 1: theory (default)
    sim.fail("this message failed to send")  # a failed send between turns
    sim.send("I am so lost with this")  # reacts to 1; delivery 2: example
    sim.send("give me an analogy")  # reacts to 2; delivery 3: analogy (request)
    sim.send("i dont get it at all")  # reacts to 3; delivery 4: simplified
    sim.send("no idea what a for loop does")  # reacts to 4; delivery 5: analogy (non-request)
    decision, final = sim.send("that makes sense now")  # reacts to 5; understood -> resolved
    assert decision.action == "resolved"
    log = sim.log
    assert log is not None and len(log.deliveries) == 5
    assert [(d.strategy, d.trigger) for d in log.deliveries] == [
        ("theory", "default"), ("example", "confusion"), ("analogy", "request"),
        ("simplified", "confusion"), ("analogy", "confusion"),
    ]
    live = dict(sim.live)
    live[5] = final  # the last delivery's reaction is the terminal message
    for delivery in log.deliveries:
        want = live[delivery.seq]
        assert delivery.student_label == want.label
        assert delivery.probability == want.probability  # exact, not approximate
        assert delivery.source == want.source
    # and the reactions are NOT all the same: nothing was copied across deliveries
    assert len({(d.student_label, d.probability, d.source) for d in log.deliveries}) > 1
    assert log.deliveries[-1].student_label == "understood" and log.deliveries[-1].source == "rule"


def test_no_fabrication_one_label_is_not_copied_onto_all_deliveries():
    st = state(FIXTURE_USED)
    log = build(resolved_decision(st), st, FIXTURE_HISTORY, FIXTURE_CURRENT, Recorder(FIXTURE_TABLE))
    assert {d.student_label for d in log.deliveries} == {"confused", "understood"}
    assert len({d.probability for d in log.deliveries}) == 3


# --- consistency of the echoed history and state --------------------------------------------------------


def test_missing_tutor_strategy_turn_raises():
    st = state(FIXTURE_USED)
    hist = history("S:q", "T:theory", "S:r1", "T:-", "S:r2", "T:analogy")  # example delivery missing
    with pytest.raises(EpisodeLogError, match="disagree"):
        build(resolved_decision(st), st, hist, FIXTURE_CURRENT, Recorder())


def test_extra_tutor_strategy_turn_raises():
    st = state(FIXTURE_USED)
    hist = history("S:q", "T:theory", "S:r1", "T:example", "S:r2", "T:analogy", "S:r3", "T:simplified")
    with pytest.raises(EpisodeLogError, match="disagree"):
        build(resolved_decision(st), st, hist, FIXTURE_CURRENT, Recorder())


def test_strategies_in_a_different_order_raise():
    st = state(FIXTURE_USED)
    hist = history("S:q", "T:example", "S:r1", "T:theory", "S:r2", "T:analogy")
    with pytest.raises(EpisodeLogError, match="disagree"):
        build(resolved_decision(st), st, hist, FIXTURE_CURRENT, Recorder())


def test_tutor_turns_back_to_back_with_no_student_between_raise():
    st = state(FIXTURE_USED)
    hist = history("S:q", "T:theory", "T:example", "S:r2", "T:analogy")
    with pytest.raises(EpisodeLogError, match="no student reaction"):
        build(resolved_decision(st), st, hist, FIXTURE_CURRENT, Recorder())


def test_empty_history_raises():
    st = state(FIXTURE_USED)
    with pytest.raises(EpisodeLogError, match="empty"):
        build(resolved_decision(st), st, [], FIXTURE_CURRENT, Recorder())


def test_non_terminal_decision_raises():
    st = state(FIXTURE_USED)
    explain = next_action(st, "confused", None, "hmm", label_source="rule")
    assert explain.action == "explain"
    with pytest.raises(EpisodeLogError, match="terminal"):
        build(explain, st, FIXTURE_HISTORY, FIXTURE_CURRENT, Recorder())


def test_decision_and_state_disagreeing_raises():
    st = state(FIXTURE_USED)
    other = state(FIXTURE_USED[:2])
    with pytest.raises(EpisodeLogError, match="disagree"):
        build(resolved_decision(other), st, FIXTURE_HISTORY, FIXTURE_CURRENT, Recorder())


# --- purity ----------------------------------------------------------------------------------------------------


def test_inputs_are_never_mutated():
    st = state(FIXTURE_USED)
    decision = resolved_decision(st)
    hist = FIXTURE_HISTORY
    before = (copy.deepcopy(st), copy.deepcopy(hist), copy.deepcopy(decision))
    build(decision, st, hist, FIXTURE_CURRENT, Recorder(FIXTURE_TABLE))
    assert (st, hist, decision) == before


def test_utc_now_is_timezone_aware():
    assert utc_now().tzinfo is not None


def test_ended_at_comes_from_the_injected_clock_with_z_suffix():
    st = state(FIXTURE_USED)
    local = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    log = build_episode_log(
        decision=resolved_decision(st), state=st, history=FIXTURE_HISTORY, current_reaction=FIXTURE_CURRENT,
        classify_fn=Recorder(), student_id="s", topic="t", model_version="v", weak_threshold=3, now=lambda: local,
    )
    assert log.ended_at == "2026-01-02T03:04:05Z"


# --- fixture drift guard ----------------------------------------------------------------------------------------


def test_episode_log_fixture_copy_matches_frontend_source():
    if not FRONTEND_SOURCE.exists():
        pytest.skip(f"frontend fixture not present in this environment: {FRONTEND_SOURCE}")
    assert FIXTURE.read_bytes() == FRONTEND_SOURCE.read_bytes()

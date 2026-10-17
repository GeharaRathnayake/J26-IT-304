"""R7: only a RULE-matched `understood` resolves an episode (backendPlan/04 section 3.6).

Messages are hand-written. The classifier behind the labels is a prototype proxy trained on synthetic
answers, not a validated confusion detector: the model half hands out `understood` inconsistently
("quiz me on inheritance" 0.305, "test me" 0.609 confused), which is exactly why R7 does not trust it.
"""

import json
import logging

import pytest
from fastapi.testclient import TestClient

import app.escalation.engine as engine_mod
import app.escalation.episode_log as episode_log_mod
import app.escalation.question_guard as qg
import app.escalation.resolution_guard as rg
from app.escalation.engine import next_action
from frontend_sim import Episode, contract_violations
from test_episode_log import FIXTURE_CURRENT, FIXTURE_HISTORY, FIXTURE_TABLE, FIXTURE_USED, Recorder, build, resolved_decision, state
from test_tutor_message import CONFUSED, TO_OFFER, make_app

ASK = "ask me questions related to the topic"  # understood, model, p(confused)=0.051
QUIZ = "quiz me on inheritance"  # understood, model, 0.305
RULE_QUESTION = "that makes sense, but why does it work?"  # understood, RULE
ACTUAL = "where does the actual value come from?"  # understood, model, a question: R6 first
MODEL_UNDERSTOOD_REQUEST = "show me an example related to the topic"  # understood, model, request `example`
STILL_LOST = "I still don't get it"  # confused, rule
R7 = "model_understood_not_trusted"


@pytest.fixture(scope="module")
def client():
    with TestClient(make_app()) as c:
        yield c


def _check_contract(res):
    for i, r in enumerate(res, start=1):
        assert contract_violations(r, f"req-{i}") == [], (i, r["action"])


# --- the predicate and its single definition --------------------------------------------------------------------


@pytest.mark.parametrize("label, source, message, req, expected", [
    ("understood", "model", "quiz me on inheritance", None, True),
    ("understood", "rule", "got it", None, False),  # rule-sourced: allowed to resolve
    ("confused", "model", "quiz me on inheritance", None, False),
    ("understood", "model", "quiz me on inheritance", "example", False),  # a request follows the request branch
    ("understood", "model", "where does the actual value come from?", None, False),  # a question: R6 first
])
def test_r7_applies_table(label, source, message, req, expected):
    assert rg.r7_applies(label, source, message, req) is expected


def test_one_definition_the_engine_and_the_log_builder_import_the_same_function():
    assert engine_mod.r7_applies is rg.r7_applies
    assert episode_log_mod.r7_applies is rg.r7_applies
    assert rg.r6_applies is qg.r6_applies  # imported, never copied


def test_the_precedence_is_part_of_the_predicate_so_a_model_understood_question_is_never_r7():
    """r7_applies excludes R6 cases itself, so even if a caller checked R7 first the answer would be R6's."""
    assert qg.r6_applies("understood", "where does the actual value come from?", None)
    assert not rg.r7_applies("understood", "model", "where does the actual value come from?", None)


def test_label_source_is_required_with_no_default():
    with pytest.raises(TypeError, match="label_source"):
        next_action(None, "confused", None, "hmm")  # type: ignore[call-arg]


# --- the engine, over HTTP ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("message", [ASK, QUIZ])
def test_a_model_sourced_understood_escalates_instead_of_resolving_and_is_reported_unchanged(client, message):
    res = Episode(client).play(CONFUSED, message)
    r = res[1]
    assert (r["confusion"]["label"], r["confusion"]["source"]) == ("understood", "model")  # classifier output unchanged
    assert (r["action"], r["strategy"], r["trigger"]) == ("explain", "example", "confusion")
    assert r["meta"]["resolution_declined"] == R7
    assert r["episode_log"] is None
    _check_contract(res)


@pytest.mark.parametrize("message", ["got it", "that makes sense"])
def test_a_rule_matched_understanding_phrase_still_resolves(client, message):
    res = Episode(client).play(CONFUSED, message)
    r = res[1]
    assert (r["confusion"]["label"], r["confusion"]["source"]) == ("understood", "rule")
    assert r["action"] == "resolved" and r["meta"]["resolution_declined"] is None
    _check_contract(res)


def test_a_rule_matched_question_is_declined_by_r6_unchanged(client):
    res = Episode(client).play(CONFUSED, RULE_QUESTION)
    assert res[1]["meta"]["resolution_declined"] == "question_guard"


def test_precedence_a_model_understood_question_is_recorded_as_r6_not_r7(client):
    res = Episode(client).play(CONFUSED, ACTUAL)
    r = res[1]
    assert (r["confusion"]["label"], r["confusion"]["source"]) == ("understood", "model")
    assert r["meta"]["resolution_declined"] == "question_guard"


def test_a_model_understood_message_with_a_request_follows_the_request_branch_no_guard_fires(client):
    res = Episode(client).play(CONFUSED, MODEL_UNDERSTOOD_REQUEST, "got it")
    r = res[1]
    assert (r["confusion"]["label"], r["confusion"]["source"]) == ("understood", "model")
    assert r["detected_request"] == "example"
    assert (r["action"], r["strategy"], r["trigger"]) == ("explain", "example", "request")
    assert r["meta"]["resolution_declined"] is None
    assert res[2]["action"] == "resolved"
    assert [d["reaction_override"] for d in res[2]["episode_log"]["deliveries"]] == [None, None]
    _check_contract(res)


def test_at_the_fourth_delivery_of_a_cycle_escalation_becomes_offer_new_cycle(client):
    res = Episode(client).play(*[CONFUSED] * 4, QUIZ)
    r = res[4]
    assert r["action"] == "offer_new_cycle" and r["updated_state"]["awaiting_cycle_confirmation"] is True
    assert r["meta"]["resolution_declined"] == R7
    _check_contract(res)


def test_the_reply_to_a_cycle_offer_is_handled_by_cycle_intent_never_by_r7(client):
    """"yes, why not?" is `understood` from the MODEL (p=0.42), but the engine is awaiting a cycle decision."""
    res = Episode(client).play(*TO_OFFER, "yes, why not?")
    r = res[5]
    assert (r["confusion"]["label"], r["confusion"]["source"]) == ("understood", "model")
    assert (r["action"], r["strategy"]) == ("explain", "theory") and r["updated_state"]["cycle"] == 2
    assert r["meta"]["resolution_declined"] is None


# --- the audit ----------------------------------------------------------------------------------------------------


def test_the_log_flags_and_the_engines_decisions_agree_across_an_episode_with_both_guards(client):
    res = Episode(client).play(CONFUSED, QUIZ, ACTUAL, STILL_LOST, "got it")
    assert res[-1]["action"] == "resolved"
    declined = {i: r["meta"]["resolution_declined"] for i, r in enumerate(res) if r["meta"]["resolution_declined"]}
    assert declined == {1: R7, 2: "question_guard"}
    deliveries = res[-1]["episode_log"]["deliveries"]
    flagged = {i + 1: d["reaction_override"] for i, d in enumerate(deliveries) if d["reaction_override"]}
    assert flagged == declined  # delivery i's reaction is turn i + 1
    first = deliveries[0]  # reacted to "quiz me": the classifier's real output is kept
    assert (first["student_label"], first["source"]) == ("understood", "model")


def test_the_current_message_never_carries_the_flag(client):
    res = Episode(client).play(*[CONFUSED] * 4, QUIZ, "no")
    assert res[-1]["action"] == "end_unresolved"
    assert [d["reaction_override"] for d in res[-1]["episode_log"]["deliveries"]] == [None, None, None, R7]


def test_info_line_has_no_student_text_and_the_turn_log_separates_the_two_guards(tmp_path, caplog):
    app_logger = logging.getLogger("app")
    app_logger.addHandler(caplog.handler)
    caplog.set_level(logging.INFO, logger="app")
    path = tmp_path / "turns.jsonl"
    try:
        with TestClient(make_app(TURN_LOG_PATH=path)) as c:
            res = Episode(c).play(CONFUSED, QUIZ, ACTUAL, "got it")
    finally:
        app_logger.removeHandler(caplog.handler)
    episode_id = res[1]["updated_state"]["episode_id"]
    r7_lines = [r.getMessage() for r in caplog.records if r.getMessage().startswith("R7:")]
    assert r7_lines == [f"R7: model-only understood not trusted, resolution declined (episode {episode_id})"]
    assert "quiz" not in r7_lines[0].lower() and "inheritance" not in r7_lines[0].lower()
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    # an R7 decline logs question_guard FALSE (the trap: `is not None` would have said true)
    assert [(r["question_guard"], r["model_understood_guard"]) for r in rows] == [
        (False, False), (False, True), (True, False), (False, False),
    ]

def test_the_log_builder_never_flags_the_current_message_even_when_it_is_a_model_understood():
    """The contract fixture's current message is `understood` from the model (the shape R7 distrusts). It
    is the CURRENT reaction, which never carries a flag (only historical reactions do)."""
    st = state(FIXTURE_USED)
    log = build(resolved_decision(st), st, FIXTURE_HISTORY, FIXTURE_CURRENT, Recorder(FIXTURE_TABLE))
    assert (log.deliveries[-1].student_label, log.deliveries[-1].source) == ("understood", "model")
    assert [d.reaction_override for d in log.deliveries] == [None, None, None]

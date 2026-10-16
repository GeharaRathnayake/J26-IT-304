"""R6, the question guard: a question never resolves an episode (backendPlan/04 section 3.5).

Messages are hand-written. The classifier behind the labels is a prototype proxy trained on synthetic
answers, not a validated confusion detector; several phrases below are labelled `understood` by it
precisely when they should not resolve anything.
"""

import json
import logging

import pytest
from fastapi.testclient import TestClient

import app.escalation.engine as engine_mod
import app.escalation.episode_log as episode_log_mod
import app.escalation.question_guard as qg
from frontend_sim import Episode, contract_violations
from test_tutor_message import CONFUSED, TO_OFFER, make_app

MODEL_QUESTION = "where does the actual value come from?"  # understood, source model, p(confused)=0.115
RULE_QUESTION = "that makes sense, but why does it work?"  # understood, source rule (phrase "that makes sense")
STILL_LOST = "I still don't get it"  # confused, source rule
GOT_IT = "got it"  # understood, source rule, not a question


@pytest.fixture(scope="module")
def client():
    with TestClient(make_app()) as c:
        yield c


def _check_contract(res):
    for i, r in enumerate(res, start=1):
        assert contract_violations(r, f"req-{i}") == [], (i, r["action"])


# --- the predicate ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("message", [
    "why does it work?", "why does it work?!", "why does it work? ", 'is it "Buddy"?', "(why?)", "what?...",
    "why?”", "really?)", "what？", "ok?\n", "why?’ ",
])
def test_is_question_true(message):
    assert qg.is_question(message)


@pytest.mark.parametrize("message", ["got it!", "I wonder why", "", "   ", "that makes sense", "why. I see", "? ok", "what is it. Fine!"])
def test_is_question_false(message):
    assert not qg.is_question(message)


def test_r6_applies_needs_understood_no_request_and_a_question():
    assert qg.r6_applies("understood", "why?", None)
    assert not qg.r6_applies("confused", "why?", None)
    assert not qg.r6_applies("understood", "why?", "example")
    assert not qg.r6_applies("understood", "got it", None)


def test_one_definition_the_engine_and_the_log_builder_import_the_same_function():
    assert engine_mod.r6_applies is qg.r6_applies
    assert episode_log_mod.r6_applies is qg.r6_applies
    assert qg.r6_applies.__globals__["is_question"] is qg.is_question


# --- the engine, over HTTP -------------------------------------------------------------------------------------


def test_model_path_a_question_labelled_understood_escalates_instead_of_resolving(client):
    res = Episode(client).play(CONFUSED, MODEL_QUESTION)
    r = res[1]
    assert (r["confusion"]["label"], r["confusion"]["source"]) == ("understood", "model")
    assert (r["action"], r["strategy"], r["trigger"]) == ("explain", "example", "confusion")
    assert r["meta"]["resolution_declined"] == "question_guard"
    assert r["episode_log"] is None
    _check_contract(res)


def test_rule_path_a_question_with_a_rule_listed_understanding_phrase_escalates(client):
    res = Episode(client).play(CONFUSED, RULE_QUESTION)
    r = res[1]
    assert (r["confusion"]["label"], r["confusion"]["source"]) == ("understood", "rule")
    assert (r["action"], r["strategy"], r["trigger"]) == ("explain", "example", "confusion")
    assert r["meta"]["resolution_declined"] == "question_guard"
    _check_contract(res)


def test_the_same_phrase_without_a_question_mark_still_resolves(client):
    res = Episode(client).play(CONFUSED, "that makes sense")
    r = res[1]
    assert r["action"] == "resolved" and r["meta"]["resolution_declined"] is None
    assert r["episode_log"]["outcome"] == "resolved"
    _check_contract(res)


def test_can_we_move_on_question_mark_escalates_documented_side_effect_of_the_accepted_error_direction(client):
    """Someone who meant to stop ("can we move on?", labelled understood by the model, p(confused)=0.208)
    gets one more explanation. Accepted: a false confused costs one explanation, a false understood
    abandons a lost student (rules.py NOTE 1), and since SF1 the conversation is never blocked."""
    res = Episode(client).play(CONFUSED, "can we move on?")
    assert res[1]["confusion"]["label"] == "understood"
    assert res[1]["action"] == "explain" and res[1]["meta"]["resolution_declined"] == "question_guard"


def test_a_question_that_carries_a_request_follows_the_request_branch_and_the_guard_stays_quiet(client):
    """"got it, can you show me an example?" is `understood` by the RULE layer (p=0.903) AND detects the
    request `example`. The request branch returns first; R6 neither fires nor flags the delivery."""
    res = Episode(client).play(CONFUSED, "got it, can you show me an example?", GOT_IT)
    r = res[1]
    assert (r["confusion"]["label"], r["confusion"]["source"]) == ("understood", "rule")
    assert r["detected_request"] == "example"
    assert (r["action"], r["strategy"], r["trigger"]) == ("explain", "example", "request")
    assert r["meta"]["resolution_declined"] is None
    log = res[2]["episode_log"]
    assert res[2]["action"] == "resolved"
    assert [d["reaction_override"] for d in log["deliveries"]] == [None, None]
    _check_contract(res)


def test_a_question_as_the_reply_to_a_cycle_offer_is_handled_by_cycle_intent_never_by_r6(client):
    """"yes, why not?" is a question the model labels `understood` (p=0.42), but the engine is awaiting a
    cycle decision: the reply is read by detect_cycle_intent (accept), and R6 is never consulted."""
    res = Episode(client).play(*TO_OFFER, "yes, why not?")
    assert res[4]["action"] == "offer_new_cycle"
    r = res[5]
    assert r["confusion"]["label"] == "understood"
    assert (r["action"], r["strategy"], r["trigger"]) == ("explain", "theory", "confusion")
    assert r["updated_state"]["cycle"] == 2
    assert r["meta"]["resolution_declined"] is None
    _check_contract(res)


def test_at_the_fourth_delivery_of_a_cycle_escalation_becomes_offer_new_cycle(client):
    res = Episode(client).play(*[CONFUSED] * 4, MODEL_QUESTION)
    assert res[3]["strategy"] == "analogy"
    r = res[4]
    assert r["action"] == "offer_new_cycle" and r["updated_state"]["awaiting_cycle_confirmation"] is True
    assert r["meta"]["resolution_declined"] == "question_guard"
    _check_contract(res)


# --- the audit: the episode log and the turn log ---------------------------------------------------------------


def test_the_log_flag_lands_on_exactly_the_delivery_whose_reaction_was_declined_with_the_real_label_kept(client):
    res = Episode(client).play(CONFUSED, MODEL_QUESTION, STILL_LOST, GOT_IT)
    assert [r["action"] for r in res] == ["explain", "explain", "explain", "resolved"]
    deliveries = res[-1]["episode_log"]["deliveries"]
    assert [d["reaction_override"] for d in deliveries] == ["question_guard", None, None]
    first = deliveries[0]  # its reaction was the question: the classifier's real answer is kept
    assert (first["student_label"], first["source"]) == ("understood", "model")
    assert first["probability"] == res[1]["confusion"]["probability"]
    assert deliveries[1]["student_label"] == "confused"


def test_the_engines_decision_and_the_logs_rederived_flag_agree_across_a_full_episode(client):
    res = Episode(client).play(CONFUSED, MODEL_QUESTION, RULE_QUESTION, STILL_LOST, GOT_IT)
    declined_turns = {i for i, r in enumerate(res) if r["meta"]["resolution_declined"] == "question_guard"}
    deliveries = res[-1]["episode_log"]["deliveries"]
    flagged_reaction_turns = {i + 1 for i, d in enumerate(deliveries) if d["reaction_override"] == "question_guard"}
    assert declined_turns == {1, 2}
    assert flagged_reaction_turns == declined_turns  # delivery i's reaction is turn i + 1


def test_the_current_message_never_carries_the_flag(client):
    """A resolving message was by definition not a question; an end_unresolved one answered an offer."""
    res = Episode(client).play(*TO_OFFER[:4], MODEL_QUESTION, "no")
    assert res[-1]["action"] == "end_unresolved"
    assert res[4]["meta"]["resolution_declined"] == "question_guard"
    deliveries = res[-1]["episode_log"]["deliveries"]
    assert [d["reaction_override"] for d in deliveries] == [None, None, None, "question_guard"]


def test_meta_resolution_declined_is_null_on_every_turn_that_did_not_decline(client):
    res = Episode(client).play(*TO_OFFER, "wait, what do you mean?", "yes", GOT_IT)
    assert all("resolution_declined" in r["meta"] and r["meta"]["resolution_declined"] is None for r in res)


def test_info_log_has_no_student_text_and_the_turn_log_records_the_guard(tmp_path, caplog):
    app_logger = logging.getLogger("app")
    app_logger.addHandler(caplog.handler)
    caplog.set_level(logging.INFO, logger="app")
    path = tmp_path / "turns.jsonl"
    try:
        with TestClient(make_app(TURN_LOG_PATH=path)) as c:
            res = Episode(c).play(CONFUSED, MODEL_QUESTION, GOT_IT)
    finally:
        app_logger.removeHandler(caplog.handler)
    lines = [r.getMessage() for r in caplog.records if "R6 question guard" in r.getMessage()]
    episode_id = res[1]["updated_state"]["episode_id"]
    assert lines == [f"R6 question guard: resolution declined (episode {episode_id})"]
    assert "actual" not in lines[0] and "Buddy" not in lines[0]
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [r["question_guard"] for r in rows] == [False, True, False]

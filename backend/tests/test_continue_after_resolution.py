"""SF1: the conversation must be able to continue after an episode resolves (owner requirement).

The frontend now starts a NEW episode on the next message (`state: null`, `history: []`). These tests
pin the backend facts that design rests on, so a classifier, engine or contract change shows up here.
The classifier is a prototype proxy trained on synthetic answers, not a validated confusion detector.
"""

import pytest
from fastapi.testclient import TestClient

from app.classifier.hybrid import classify
from app.classifier.model import load_model
from app.config import DEFAULT_MODELS_DIR
from frontend_sim import Episode, contract_violations
from test_tutor_message import make_app

REPORTED = [
    "I don't understand inheritance in Java.",
    "If Dog extends Animal, does Dog automatically get the name 'Buddy'?",
    "I understand that Dog inherits the name field, but where does the actual value 'Buddy' come from?",
]
NEXT_MESSAGE = "I still do not get where Buddy comes from."


@pytest.fixture(scope="module")
def client():
    with TestClient(make_app()) as c:
        yield c


def reported_conversation(client):
    ep = Episode(client, topic="inheritance")
    return ep, ep.play(*REPORTED)


def new_episode_body(ep, message, request_id):
    return {
        "request_id": request_id, "student_id": ep.student_id, "session_id": ep.session_id,
        "topic": ep.topic, "message": message, "history": [], "state": None, "profile": None,
    }


def test_the_reported_conversation_resolves_on_the_third_message(client):
    """CURRENT behaviour, pinned. A tester's conversation resolved on message 3 and the student could
    not reply. Two backend facts cause that: the token "actual" flips the classifier to `understood`
    (p=0.27, source model; see the classifier pin below), and the engine resolves the episode on ONE
    `understood` after a delivery (app/escalation/engine.py:248). Neither is changed by SF1; if a future
    classifier or engine change makes this conversation continue, this test goes red on purpose."""
    _, res = reported_conversation(client)
    assert [(r["action"], r["strategy"]) for r in res] == [
        ("explain", "theory"), ("explain", "example"), ("resolved", None),
    ]
    assert res[2]["confusion"]["label"] == "understood" and res[2]["confusion"]["source"] == "model"
    assert res[2]["episode_log"] is not None and res[2]["episode_log"]["outcome"] == "resolved"
    for i, r in enumerate(res, start=1):
        assert contract_violations(r, f"req-{i}") == []


def test_the_next_message_after_resolution_starts_a_new_episode(client):
    """What the frontend now sends after an episode ends: `state: null` and `history: []`. The service
    answers a normal first turn (explain, trigger default) in a NEW episode."""
    ep, res = reported_conversation(client)
    old_id = res[-1]["updated_state"]["episode_id"]
    r = client.post("/tutor/message", json=new_episode_body(ep, NEXT_MESSAGE, "req-new"))
    assert r.status_code == 200
    body = r.json()
    assert body["action"] == "explain" and body["trigger"] == "default"
    assert body["updated_state"]["episode_id"] != old_id
    assert len(body["updated_state"]["strategies_used"]) == 1
    assert body["episode_log"] is None
    assert contract_violations(body, "req-new") == []


def test_documented_hazard_the_post_resolution_state_reopens_the_same_episode(client):
    """KNOWN LIMITATION, pinned. The contract's `TutorState` has no "ended" flag, so the service cannot
    tell a resolved episode's `updated_state` from a live one: a message sent with it continues the SAME
    `episode_id` and escalates to the next strategy, corrupting the finished episode's record. This is
    why the frontend must send `state: null` (turnInputFor in episodeRules.ts) after resolution."""
    ep, res = reported_conversation(client)
    resolved_state = res[-1]["updated_state"]
    body = new_episode_body(ep, NEXT_MESSAGE, "req-reopen")
    body["history"], body["state"] = ep.history, resolved_state
    r = client.post("/tutor/message", json=body)
    assert r.status_code == 200
    out = r.json()
    assert out["updated_state"]["episode_id"] == resolved_state["episode_id"]  # the SAME episode again
    assert out["action"] == "explain" and out["strategy"] == "simplified"  # it escalated: a third strategy
    assert len(out["updated_state"]["strategies_used"]) == len(resolved_state["strategies_used"]) + 1


def test_classifier_pin_the_token_actual_flips_the_label():
    """The ROOT of the reported conversation, recorded, NOT endorsed. The proxy classifier (trained on
    synthetic answers) gives the token "actual" a logistic-regression weight of about -4.46 (towards
    `understood`): "where does the value come from?" is `confused` (p about 0.80) and adding "actual"
    makes it `understood` (p about 0.12), source `model` in both. A question guard is with the lead."""
    model = load_model(DEFAULT_MODELS_DIR / "clf-v1.0.0")
    with_actual = classify(model, "where does the actual value come from?")
    without = classify(model, "where does the value come from?")
    assert (with_actual.label, with_actual.source) == ("understood", "model")
    assert (without.label, without.source) == ("confused", "model")
    assert with_actual.probability < model.threshold < without.probability
    tfidf, clf = model.pipeline.named_steps["tfidf"], model.pipeline.named_steps["clf"]
    weight = clf.coef_[0][tfidf.vocabulary_["actual"]]
    assert weight == pytest.approx(-4.46, abs=0.02)

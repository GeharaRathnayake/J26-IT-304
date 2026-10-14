"""POST /tutor/message: request validation against the frozen contract.

A valid request gets 501 (pipeline not built yet). 503 means "model not loaded"; 422
means the body is invalid. The classifier is not called in this stage.
"""

import copy
import shutil

import pytest
from fastapi.testclient import TestClient

from app.config import DEFAULT_MODELS_DIR
from app.main import create_app
from app.schemas import TutorRequest


def valid_body(**overrides):
    body = {
        "request_id": "req-1",
        "student_id": "stu-1",
        "session_id": "sess-1",
        "topic": "loops",
        "message": "what is a for loop",
        "history": [
            {"role": "student", "text": "hi", "ts": "2026-10-14T10:00:00Z"},
            {"role": "tutor", "text": "hello", "strategy": "theory", "ts": "2026-10-14T10:00:05Z"},
        ],
        "state": None,
    }
    body.update(overrides)
    return body


MID_EPISODE_STATE = {
    "episode_id": "ep-1",
    "cycle": 1,
    "strategies_used": [{"strategy": "theory", "trigger": "default"}],
    "awaiting_cycle_confirmation": False,
    "prior_explanations": ["A loop repeats code."],
}


@pytest.fixture(scope="module")
def client():
    with TestClient(create_app()) as c:
        yield c


def post(client, body):
    return client.post("/tutor/message", json=body)


# --- accepted (501) -----------------------------------------------------------------


def test_valid_first_message_is_501(client):
    r = post(client, valid_body())
    assert r.status_code == 501
    assert r.json() == {"detail": "tutoring pipeline not implemented yet (stage S6)"}


def test_general_topic_is_accepted(client):
    assert post(client, valid_body(topic="general")).status_code == 501


def test_valid_mid_episode_state_is_501(client):
    assert post(client, valid_body(state=MID_EPISODE_STATE)).status_code == 501


def test_profile_absent_null_and_valid_are_all_501(client):
    absent = valid_body()
    assert "profile" not in absent
    assert post(client, absent).status_code == 501
    assert post(client, valid_body(profile=None)).status_code == 501
    profile = {"strategy_stats": {"theory": {"uses": 2, "wins": 1}}, "weak_topics": ["loops"]}
    assert post(client, valid_body(profile=profile)).status_code == 501
    assert post(client, valid_body(profile={"strategy_stats": {}, "weak_topics": []})).status_code == 501


def test_extra_unknown_fields_are_ignored_not_rejected(client):
    body = valid_body(state=copy.deepcopy(MID_EPISODE_STATE), future_field="x")
    body["state"]["future_state_field"] = {"a": 1}
    assert post(client, body).status_code == 501


# --- rejected (422) -----------------------------------------------------------------


@pytest.mark.parametrize("topic", ["nonsense", "Loops", "file-io", "", "general ", "General"])
def test_bad_topic_is_422(client, topic):
    assert post(client, valid_body(topic=topic)).status_code == 422


def _without(key):
    body = valid_body()
    del body[key]
    return body


@pytest.mark.parametrize(
    "body",
    [
        _without("state"),
        _without("request_id"),
        _without("history"),
        valid_body(state={**MID_EPISODE_STATE, "strategies_used": [{"strategy": "lecture", "trigger": "default"}]}),
        valid_body(state={**MID_EPISODE_STATE, "strategies_used": [{"strategy": "theory", "trigger": "whenever"}]}),
        valid_body(history=[{"role": "teacher", "text": "x", "ts": "t"}]),
        valid_body(history=[{"role": "tutor", "text": "x", "strategy": "lecture", "ts": "t"}]),
        valid_body(message=""),
        valid_body(message="   \t\n "),
        valid_body(state={**MID_EPISODE_STATE, "cycle": "1"}),  # wrongly typed
        valid_body(state={**MID_EPISODE_STATE, "awaiting_cycle_confirmation": "no"}),
        valid_body(state={k: v for k, v in MID_EPISODE_STATE.items() if k != "episode_id"}),
        valid_body(profile={"strategy_stats": {"lecture": {"uses": 1, "wins": 0}}, "weak_topics": []}),
        valid_body(profile={"strategy_stats": {}}),
        valid_body(request_id=7),
    ],
    ids=[
        "missing-state", "missing-request_id", "missing-history", "unknown-strategy",
        "unknown-trigger", "role-teacher", "unknown-history-strategy", "empty-message",
        "whitespace-message", "cycle-as-string", "bool-as-string", "missing-episode_id",
        "unknown-profile-strategy-key", "profile-missing-weak_topics", "request_id-int",
    ],
)
def test_invalid_body_is_422(client, body):
    r = post(client, body)
    assert r.status_code == 422
    assert "detail" in r.json()


# --- the message is never modified ----------------------------------------------------


def test_message_with_surrounding_whitespace_survives_validation_unchanged():
    raw = "  \tWhat IS a For Loop?\n  "
    model = TutorRequest.model_validate(valid_body(message=raw))
    assert model.message == raw


def test_padded_message_is_accepted_over_http(client):
    assert post(client, valid_body(message="  Hello  ")).status_code == 501


def test_long_message_has_no_length_limit(client):
    assert post(client, valid_body(message="word " * 20000)).status_code == 501


# --- degraded app ----------------------------------------------------------------------


@pytest.fixture
def degraded_client(tmp_path):
    models = tmp_path / "models"
    shutil.copytree(DEFAULT_MODELS_DIR, models)
    path = models / "clf-v1.0.0" / "pipeline.joblib"
    data = bytearray(path.read_bytes())
    data[len(data) // 2] ^= 0x01
    path.write_bytes(bytes(data))
    with TestClient(create_app(models)) as c:
        yield c


def test_degraded_valid_request_is_503(degraded_client):
    assert degraded_client.get("/health").json()["status"] == "degraded"
    r = post(degraded_client, valid_body())
    assert r.status_code == 503
    assert "classifier failed verification" in r.json()["detail"]


def test_degraded_invalid_request_is_still_422(degraded_client):
    assert post(degraded_client, valid_body(topic="nonsense")).status_code == 422
    assert post(degraded_client, valid_body(message="")).status_code == 422


def test_degraded_app_still_serves_topics(degraded_client):
    assert len(degraded_client.get("/topics").json()) == 14

"""GET /topics and the contract-fixture drift guards."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.topics import GENERAL, is_accepted_topic, public_topics

TESTS_DIR = Path(__file__).resolve().parent
FIXTURE = TESTS_DIR / "contract_fixtures" / "topics.json"
# dev/backend/tests -> dev/. Exists in the venv; absent in the Docker image.
FRONTEND_SOURCE = TESTS_DIR.parents[1] / "frontend" / "src" / "features" / "tutor" / "api" / "fixtures" / "topics.json"


@pytest.fixture(scope="module")
def client():
    with TestClient(create_app()) as c:
        yield c


def test_get_topics_equals_the_fixture_exactly_in_order(client):
    expected = json.loads(FIXTURE.read_bytes())
    resp = client.get("/topics")
    assert resp.status_code == 200
    assert resp.json() == expected  # list equality: same items, same order
    assert len(resp.json()) == 14


def test_get_topics_never_contains_general(client):
    assert GENERAL not in [t["id"] for t in client.get("/topics").json()]


def test_in_code_list_equals_the_fixture():
    assert public_topics() == json.loads(FIXTURE.read_bytes())


def test_general_is_accepted_but_not_public():
    assert is_accepted_topic(GENERAL)
    assert GENERAL not in [t["id"] for t in public_topics()]


@pytest.mark.parametrize("slug", ["Loops", "file-io", "", "general ", "nonsense", "1loops", "General"])
def test_is_accepted_topic_rejects_bad_slugs(slug):
    assert not is_accepted_topic(slug)


def test_public_topics_returns_a_fresh_list():
    public_topics().append({"id": "x", "label": "x"})
    assert len(public_topics()) == 14


def test_fixture_copy_matches_frontend_source():
    """Drift guard: the copy must be byte-identical to the frontend's frozen fixture."""
    if not FRONTEND_SOURCE.exists():
        pytest.skip(f"frontend fixture not present in this environment: {FRONTEND_SOURCE}")
    assert FIXTURE.read_bytes() == FRONTEND_SOURCE.read_bytes()

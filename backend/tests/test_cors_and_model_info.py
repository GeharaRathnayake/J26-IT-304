"""S9: CORS for the browser frontend, GET /model-info, the compose project name, text-only wording.

Only browsers enforce CORS, so curl and every other test pass without any of this. These tests pin the
headers the browser needs (07 section 8, 09 D5). The classifier behind /model-info is a prototype proxy
trained on synthetic answers.
"""

import json
import logging
import pathlib
import shutil
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import DEFAULT_MODELS_DIR, Settings
from app.generation.postprocess import strip_think
from app.main import create_app

REAL_META = DEFAULT_MODELS_DIR / "clf-v1.0.0" / "metadata.json"
ALLOWED = "http://localhost:5173"
ALLOWED_IP = "http://127.0.0.1:5173"
BAD_ORIGINS = ["http://localhost:5174", "http://evil.example", "http://localhost:5173/"]
PREFLIGHT = {"Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"}
ACAO = "access-control-allow-origin"
INFO_KEYS = {"version", "trained_at", "dataset", "threshold", "metrics"}
COMPOSE = Path(__file__).resolve().parent.parent / "compose.yaml"
VALID_BODY = {
    "request_id": "r1", "student_id": "s1", "session_id": "x1", "topic": "loops",
    "message": "i do not get it", "history": [], "state": None, "profile": None,
}


@pytest.fixture
def client():
    with TestClient(create_app()) as c:
        yield c


@pytest.fixture
def degraded_client(tmp_path):
    models = tmp_path / "models"
    shutil.copytree(DEFAULT_MODELS_DIR, models)
    pipe = models / "clf-v1.0.0" / "pipeline.joblib"
    data = bytearray(pipe.read_bytes())
    data[len(data) // 2] ^= 0x01
    pipe.write_bytes(bytes(data))
    with TestClient(create_app(models)) as c:
        assert c.app.state.model is None
        yield c


@pytest.fixture
def app_errors(caplog):
    # main._configure_logging() sets propagate=False on 'app', so attach caplog's handler directly.
    app_logger = logging.getLogger("app")
    app_logger.addHandler(caplog.handler)
    caplog.set_level(logging.ERROR, logger="app")
    yield lambda: [r.getMessage() for r in caplog.records if r.levelno == logging.ERROR]
    app_logger.removeHandler(caplog.handler)


# --- CORS: preflight ----------------------------------------------------------------------------


@pytest.mark.parametrize("origin", [ALLOWED, ALLOWED_IP])
def test_preflight_from_allowed_origin(client, origin):
    resp = client.options("/tutor/message", headers={"Origin": origin, **PREFLIGHT})
    assert resp.status_code == 200
    assert resp.headers[ACAO] == origin
    assert "POST" in resp.headers["access-control-allow-methods"]
    assert "content-type" in resp.headers["access-control-allow-headers"].lower()


def test_preflight_rejects_a_header_the_frontend_does_not_send(client):
    """Starlette always allows Content-Type, so allow_headers=[] would still pass the test above. This
    one pins the allow-list itself: an unlisted header is refused, so a stray `["*"]` goes red."""
    resp = client.options(
        "/tutor/message",
        headers={"Origin": ALLOWED, "Access-Control-Request-Method": "POST",
                 "Access-Control-Request-Headers": "content-type, x-custom"},
    )
    assert resp.status_code == 400
    assert "x-custom" not in resp.headers.get("access-control-allow-headers", "").lower()


def test_preflight_rejects_a_method_the_frontend_does_not_use(client):
    resp = client.options(
        "/tutor/message", headers={"Origin": ALLOWED, "Access-Control-Request-Method": "DELETE"}
    )
    assert resp.status_code == 400


@pytest.mark.parametrize("origin", BAD_ORIGINS)
def test_disallowed_origin_gets_no_allow_origin_header(client, origin):
    pre = client.options("/tutor/message", headers={"Origin": origin, **PREFLIGHT})
    assert ACAO not in pre.headers
    for path in ("/health", "/topics", "/model-info"):
        resp = client.get(path, headers={"Origin": origin})
        assert ACAO not in resp.headers, (path, origin)


@pytest.mark.parametrize("path", ["/health", "/topics", "/model-info"])
def test_simple_get_carries_header(client, path):
    resp = client.get(path, headers={"Origin": ALLOWED})
    assert resp.status_code == 200
    assert resp.headers[ACAO] == ALLOWED


def test_no_credentials_header(client):
    resp = client.get("/health", headers={"Origin": ALLOWED})
    assert "access-control-allow-credentials" not in resp.headers


# --- CORS: error paths --------------------------------------------------------------------------


def test_422_carries_header(client):
    resp = client.post("/tutor/message", json={"nonsense": 1}, headers={"Origin": ALLOWED})
    assert resp.status_code == 422
    assert resp.headers[ACAO] == ALLOWED


def test_503_carries_header_on_tutor_message(degraded_client):
    resp = degraded_client.post("/tutor/message", json=VALID_BODY, headers={"Origin": ALLOWED})
    assert resp.status_code == 503
    assert resp.headers[ACAO] == ALLOWED


def test_503_carries_header_on_model_info(degraded_client):
    resp = degraded_client.get("/model-info", headers={"Origin": ALLOWED})
    assert resp.status_code == 503
    assert resp.headers[ACAO] == ALLOWED


def test_unknown_path_404_carries_header(client):
    resp = client.get("/nope", headers={"Origin": ALLOWED})
    assert resp.status_code == 404
    assert resp.headers[ACAO] == ALLOWED


# --- CORS: settings -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    ["*", "http://localhost:5173/", "localhost:5173", "http://localhost:5173/app", "", " , ",
     "http://localhost:5173,*", "http://localhost:5173, http://x:1/"],
)
def test_bad_cors_origins_fail_settings(value):
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        Settings(_env_file=None, CORS_ORIGINS=value)


def test_bad_cors_origins_from_environment_fail(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173/")
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        Settings(_env_file=None)


def test_cors_origins_with_spaces_parse_to_two():
    s = Settings(_env_file=None, CORS_ORIGINS="http://a:1, http://b:2")
    assert s.cors_origin_list() == ["http://a:1", "http://b:2"]


def test_cors_origins_default(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    assert Settings(_env_file=None).cors_origin_list() == ["http://localhost:5173", "http://127.0.0.1:5173"]


def test_custom_origin_is_honoured(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5174")
    with TestClient(create_app()) as c:
        assert c.get("/health", headers={"Origin": "http://localhost:5174"}).headers[ACAO] == "http://localhost:5174"
        assert ACAO not in c.get("/health", headers={"Origin": ALLOWED}).headers


# --- /model-info --------------------------------------------------------------------------------


def test_model_info_equals_metadata_json(client):
    expected = json.loads(REAL_META.read_text(encoding="utf-8"))["model_info"]
    resp = client.get("/model-info")
    assert resp.status_code == 200
    assert resp.json() == expected


def test_model_info_has_exactly_the_five_keys_with_types(client):
    body = client.get("/model-info").json()
    assert set(body) == INFO_KEYS
    assert all(isinstance(body[k], str) for k in ("version", "trained_at", "dataset"))
    assert isinstance(body["threshold"], float)
    assert body["metrics"] and all(isinstance(v, float) for v in body["metrics"].values())


def test_model_info_number_formatting_is_untouched(client):
    raw = client.get("/model-info").text.replace(" ", "")
    assert '"threshold":0.5,' in raw
    assert "0.6629323395830907" in raw


def test_model_info_is_not_reread_from_disk(client, monkeypatch):
    """After startup any read of a metadata.json raises; the endpoint must still answer 200."""
    orig = {n: getattr(pathlib.Path, n) for n in ("read_text", "read_bytes", "open")}

    def guard(original):
        def wrapper(self, *a, **k):
            if self.name == "metadata.json":
                raise AssertionError("metadata.json re-read after startup")
            return original(self, *a, **k)
        return wrapper

    for name, original in orig.items():
        monkeypatch.setattr(pathlib.Path, name, guard(original))
    resp = client.get("/model-info")
    assert resp.status_code == 200
    assert set(resp.json()) == INFO_KEYS


def test_model_info_serves_what_was_loaded(client):
    client.app.state.model.metadata["model_info"]["version"] = "served-from-memory"
    assert client.get("/model-info").json()["version"] == "served-from-memory"


def test_model_info_503_when_degraded(degraded_client):
    resp = degraded_client.get("/model-info")
    assert resp.status_code == 503
    assert resp.json()["detail"]


def test_metadata_json_is_not_in_the_hash_list():
    """The malformed-model_info tests rely on the hash check not tripping first."""
    meta = json.loads(REAL_META.read_text(encoding="utf-8"))
    assert set(meta["files"]) == {"pipeline.joblib", "rules.yaml"}


def _model_copy(tmp_path, mutate):
    models = tmp_path / "models"
    shutil.copytree(DEFAULT_MODELS_DIR, models)
    path = models / "clf-v1.0.0" / "metadata.json"
    meta = json.loads(path.read_text(encoding="utf-8"))
    mutate(meta)
    path.write_text(json.dumps(meta), encoding="utf-8")
    return models


@pytest.mark.parametrize(
    "mutate",
    [
        lambda info: info.pop("dataset"),
        lambda info: info.update(extra_field="x"),
        lambda info: info.update(threshold="0.5"),
        lambda info: info.update(metrics={"macro_f1": "high"}),
    ],
    ids=["missing-key", "extra-key", "threshold-string", "metric-string"],
)
def test_malformed_model_info_degrades_with_one_error(tmp_path, app_errors, mutate):
    models = _model_copy(tmp_path, lambda meta: mutate(meta["model_info"]))
    with TestClient(create_app(models)) as c:
        assert c.app.state.model is None
        assert c.get("/health").json()["status"] == "degraded"
        assert c.get("/model-info").status_code == 503
        assert c.post("/tutor/message", json=VALID_BODY).status_code == 503
    errors = app_errors()
    assert len(errors) == 1, errors
    assert "model_info" in errors[0]


def test_missing_model_info_block_degrades(tmp_path, app_errors):
    models = _model_copy(tmp_path, lambda meta: meta.pop("model_info"))
    with TestClient(create_app(models)) as c:
        assert c.app.state.model is None
    assert len(app_errors()) == 1


# --- text-only, compose name, timeout budget ---------------------------------------------------


def test_strip_think_docstring_does_not_mention_voice():
    assert "voice" not in (strip_think.__doc__ or "").lower()


def test_compose_project_name_is_j26_tutor():
    """Without a top-level `name:` the project is called `backend` after its folder and the
    containers (backend-api-1) can collide with another project's."""
    doc = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    assert doc["name"] == "j26-tutor"


def test_llm_timeout_leaves_headroom_inside_the_client_budget():
    """07 section 5, "Keep generation inside 30 s": the frontend's TURN_TIMEOUT_MS is 30 s. If the
    generation timeout came within 5 s of it, a slow turn would end as a client timeout instead of
    the template fallback. The frontend files are not read (Docker has none)."""
    assert Settings(_env_file=None).LLM_TIMEOUT_S + 5 <= 30

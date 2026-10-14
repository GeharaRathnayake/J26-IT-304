"""Startup verification tests. No network, no Ollama.

The classifier under test is a prototype proxy trained on synthetic answers; these
tests check that the artifact is the right file and the right way round, not that
the classifier is accurate on real students.
"""

import hashlib
import json
import logging
import shutil
from pathlib import Path

import joblib
import pytest
from fastapi.testclient import TestClient

from app.classifier import model as model_mod
from app.classifier.model import (
    CONFUSED_TEXT,
    CORRECT_TEXT,
    ModelLoadError,
    assert_class_order,
    load_model,
)
from app.config import DEFAULT_MODELS_DIR
from app.main import create_app

REAL_DIR = DEFAULT_MODELS_DIR / "clf-v1.0.0"
EXPECTED_HEALTH = {
    "status": "ok",
    "model_loaded": True,
    "llm_reachable": False,
    "model_version": "clf-v1.0.0",
}


def _copy_models(tmp_path: Path) -> Path:
    """Copy the models dir to tmp; returns the temp models dir (never touches the real one)."""
    dest = tmp_path / "models"
    shutil.copytree(DEFAULT_MODELS_DIR, dest)
    return dest


def _flip_one_byte(path: Path) -> None:
    data = bytearray(path.read_bytes())
    data[len(data) // 2] ^= 0x01
    path.write_bytes(bytes(data))


def test_real_model_loads_and_health_is_exact():
    with TestClient(create_app()) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == EXPECTED_HEALTH


def test_health_has_no_extra_fields():
    with TestClient(create_app()) as client:
        body = client.get("/health").json()
    assert set(body) == {"status", "model_loaded", "llm_reachable", "model_version"}


def test_real_hashes_match_metadata():
    meta = json.loads((REAL_DIR / "metadata.json").read_text(encoding="utf-8"))
    # Raw bytes for both files, exactly what `sha256sum` would print.
    for name in ("pipeline.joblib", "rules.yaml"):
        raw = (REAL_DIR / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == meta["files"][name], name
        assert model_mod._sha256(REAL_DIR / name) == meta["files"][name], name
    assert b"\r" not in (REAL_DIR / "rules.yaml").read_bytes()

def test_real_model_passes_class_order_assertion(record_property):
    loaded = load_model(REAL_DIR)
    scores = assert_class_order(loaded.predict_confused)
    record_property("p_correct", scores["p_correct"])
    record_property("p_confused", scores["p_confused"])
    print(f"\nP(confused) correct={scores['p_correct']:.4f} confused={scores['p_confused']:.4f}")
    assert loaded.pipeline.classes_.tolist() == [0, 1]
    assert loaded.proba_index_confused == 1


# --- negative controls: failed verification degrades instead of killing the process --

DEGRADED_HEALTH = {
    "status": "degraded",
    "model_loaded": False,
    "llm_reachable": False,
    "model_version": None,
}


@pytest.fixture
def app_errors(caplog):
    """Capture ERROR records from the 'app' logger tree.

    main._configure_logging() sets propagate=False on the 'app' logger, so caplog's
    root handler never sees its records. Attach caplog's handler to 'app' directly.
    """
    app_logger = logging.getLogger("app")
    app_logger.addHandler(caplog.handler)
    caplog.set_level(logging.ERROR, logger="app")
    yield lambda: [r.getMessage() for r in caplog.records if r.levelno == logging.ERROR]
    app_logger.removeHandler(caplog.handler)


def _assert_degraded(models_dir, errors, *needles):
    with TestClient(create_app(models_dir)) as client:
        resp = client.get("/health")
        assert client.app.state.model is None
    assert resp.status_code == 200
    assert resp.json() == DEGRADED_HEALTH
    msgs = errors()
    assert msgs, "expected an ERROR log record"
    for needle in needles:
        assert any(needle in m for m in msgs), (needle, msgs)


def test_corrupted_pipeline_degrades_and_is_never_unpickled(tmp_path, monkeypatch, app_errors):
    models = _copy_models(tmp_path)
    _flip_one_byte(models / "clf-v1.0.0" / "pipeline.joblib")

    def boom(*a, **k):
        raise AssertionError("joblib.load called on an unverified file")

    monkeypatch.setattr(joblib, "load", boom)
    _assert_degraded(models, app_errors, "hash mismatch for pipeline.joblib")


def test_modified_rules_yaml_degrades(tmp_path, app_errors):
    models = _copy_models(tmp_path)
    with open(models / "clf-v1.0.0" / "rules.yaml", "ab") as fh:
        fh.write(b"# tampered\n")
    _assert_degraded(models, app_errors, "hash mismatch for rules.yaml")


def test_crlf_rules_yaml_degrades(tmp_path, app_errors):
    """A line-ending rewrite (what core.autocrlf does) is caught, not tolerated."""
    models = _copy_models(tmp_path)
    path = models / "clf-v1.0.0" / "rules.yaml"
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    _assert_degraded(models, app_errors, "hash mismatch for rules.yaml")
    with pytest.raises(ModelLoadError, match="rules.yaml"):
        load_model(models / "clf-v1.0.0")


def test_wrong_sklearn_version_degrades(tmp_path, app_errors):
    models = _copy_models(tmp_path)
    meta_path = models / "clf-v1.0.0" / "metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["runtime"]["scikit_learn"] = "0.0.0"
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    _assert_degraded(models, app_errors, "scikit-learn version mismatch")


def test_load_model_still_raises_on_failure(tmp_path):
    models = _copy_models(tmp_path)
    _flip_one_byte(models / "clf-v1.0.0" / "pipeline.joblib")
    with pytest.raises(ModelLoadError, match="pipeline.joblib"):
        load_model(models / "clf-v1.0.0")


def test_unpickle_failure_is_wrapped(monkeypatch):
    def boom(*a, **k):
        raise EOFError("simulated unpickle failure")

    monkeypatch.setattr(joblib, "load", boom)
    with pytest.raises(ModelLoadError, match="cannot unpickle pipeline.joblib"):
        load_model(REAL_DIR)


def test_non_model_load_errors_still_propagate(monkeypatch):
    import app.main as main_mod

    def boom(*a, **k):
        raise RuntimeError("not a verification failure")

    monkeypatch.setattr(main_mod, "load_model", boom)
    with pytest.raises(RuntimeError, match="not a verification failure"):
        with TestClient(create_app()):
            pass

# --- negative controls: the assertion itself can fail ------------------------------


def test_inverted_predictor_fails_assertion():
    loaded = load_model(REAL_DIR)
    inverted = lambda text: 1.0 - loaded.predict_confused(text)  # noqa: E731
    with pytest.raises(ModelLoadError, match="class-order assertion failed"):
        assert_class_order(inverted)


def test_constant_high_predictor_fails_correct_half():
    with pytest.raises(ModelLoadError, match="plainly correct sentence"):
        assert_class_order(lambda text: 0.9)


def test_constant_low_predictor_fails_confused_half():
    with pytest.raises(ModelLoadError, match="i dont get it"):
        assert_class_order(lambda text: 0.1)


def test_assertion_strings_are_the_documented_ones():
    # Raw text, as specified: guards against someone "tidying" them.
    assert CORRECT_TEXT == "A for loop repeats a block of code while its condition is true."
    assert CONFUSED_TEXT == "i dont get it"


def test_settings_defaults_are_host_127_and_port_8001(monkeypatch):
    # 8001 is fixed by the frontend's committed default (VITE_TUTOR_URL).
    for var in ("HOST", "PORT", "MODEL_VERSION", "MODELS_DIR"):
        monkeypatch.delenv(var, raising=False)
    from app.config import Settings

    settings = Settings(_env_file=None)
    assert settings.PORT == 8001
    assert settings.HOST == "127.0.0.1"

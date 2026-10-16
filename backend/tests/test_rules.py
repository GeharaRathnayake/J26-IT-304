"""Rule-layer tests: parser validation, normalisation, matching, parse-what-you-hashed.

Prototype hybrid over a proxy classifier trained on synthetic answers. Tests named
`test_documented_wrong_*` pin CURRENT behaviour that is known to be wrong; they do not
endorse it. Every test string is hand-written (no experiment1 data or probe).
"""

import hashlib
import json
import logging
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.classifier import model as model_mod
from app.classifier.errors import ModelLoadError
from app.classifier.model import load_model
from app.classifier.rules import normalise, parse_rules
from app.config import DEFAULT_MODELS_DIR
from app.main import create_app

REAL_DIR = DEFAULT_MODELS_DIR / "clf-v1.0.0"


@pytest.fixture(scope="module")
def rules():
    return parse_rules((REAL_DIR / "rules.yaml").read_bytes())


# --- the real file ----------------------------------------------------------------


def test_real_rules_counts_and_shape(rules):
    # An unnoticed list change must break a test.
    assert rules.version == "1.0"
    assert len(rules.confusion_phrases) == 51
    assert len(rules.understanding_phrases) == 19
    allp = rules.confusion_phrases + rules.understanding_phrases
    assert len(set(allp)) == len(allp)
    assert all(p == normalise(p) for p in allp)


# --- parser negative controls (in-memory bytes, so the hash check is not involved) --

GOOD = b'version: "1.0"\nconfusion_phrases:\n  - "no idea"\nunderstanding_phrases:\n  - "got it"\n'


def test_parser_accepts_minimal_good_yaml():
    r = parse_rules(GOOD)
    assert r.match("got it")[0] == "understood"


@pytest.mark.parametrize(
    "data",
    [
        b'version: "1.0"\nconfusion_phrases:\n  - "no idea"\n  - "no idea"\nunderstanding_phrases:\n  - "got it"\n',
        b'version: "1.0"\nconfusion_phrases:\n  - "no idea"\nunderstanding_phrases:\n  - "no idea"\n',
        b'version: "1.0"\nconfusion_phrases:\n  - "No idea"\nunderstanding_phrases:\n  - "got it"\n',
        b'version: "1.0"\nconfusion_phrases:\n  - "no  idea"\nunderstanding_phrases:\n  - "got it"\n',
        b'version: "1.0"\nconfusion_phrases: []\nunderstanding_phrases:\n  - "got it"\n',
        b'version: "1.0"\nconfusion_phrases:\n  - "no idea"\n',
        b'version: "1.0"\nconfusion_phrases:\n  - 5\nunderstanding_phrases:\n  - "got it"\n',
        b'confusion_phrases:\n  - "no idea"\nunderstanding_phrases:\n  - "got it"\n',
        b"- just\n- a list\n",
        b"version: [unclosed\n",
    ],
    ids=[
        "duplicate", "duplicate-across-lists", "uppercase", "double-space",
        "empty-list", "missing-key", "non-string", "missing-version", "not-a-mapping",
        "invalid-yaml",
    ],
)
def test_parser_rejects_bad_yaml(data):
    with pytest.raises(ModelLoadError):
        parse_rules(data)


# --- normalisation ------------------------------------------------------------------


@pytest.mark.parametrize(
    "text, phrase",
    [
        ("I don’t understand", "i don't understand"),  # U+2019
        ("I‘m lost", "i'm lost"),  # U+2018
        ("I  DONT   understand ", "i dont understand"),
        ("I dont\tunderstand", "i dont understand"),
        ("I dont\nunderstand", "i dont understand"),
    ],
)
def test_normalisation_matches_confusion_phrase(rules, text, phrase):
    assert rules.match(text) == ("confused", phrase)


# --- matching order and word boundaries ----------------------------------------------


def test_whole_word_no_ideal_is_not_no_idea(rules):
    assert rules.match("no ideal") == (None, None)
    assert rules.match("no idea") == ("confused", "no idea")


def test_makes_no_sense_is_confused(rules):
    assert rules.match("makes no sense")[0] == "confused"


def test_none_of_that_makes_sense_is_confused_not_understanding(rules):
    assert rules.match("none of that makes sense") == ("confused", "none of that makes sense")


@pytest.mark.parametrize("text", ["got it, but now I'm lost", "got it, but now I'm lost again"])
def test_confusion_list_is_checked_before_understanding(rules, text):
    assert rules.match(text) == ("confused", "i'm lost")


def test_fixed_got_it_wrong_is_confused(rules):
    assert rules.match("I got it wrong again") == ("confused", "got it wrong")


# --- documented wrong behaviour (pinned, not endorsed) --------------------------------


def test_documented_wrong_got_it_from_the_docs_is_understood(rules):
    assert rules.match("I got it from the docs") == ("understood", "got it")


def test_documented_wrong_makes_sense_in_theory_is_understood(rules):
    label, phrase = rules.match("that makes sense in theory but how do I code it")
    assert (label, phrase) == ("understood", "that makes sense")


def test_documented_limit_inserted_word_defeats_phrase(rules):
    # "i'm lost" / "i am lost" are listed; "i am so lost" is not matched.
    assert rules.match("I am so lost") == (None, None)


def test_documented_choice_challenge_to_tutor_is_confusion(rules):
    assert rules.match("That doesn't make sense, 2 + 2 is 4") == ("confused", "doesn't make sense")


def test_documented_wrong_i_see_now_that_i_was_right_is_understood(rules):
    assert rules.match("I see now that I was right")[0] == "understood"


# --- load_model integration -----------------------------------------------------------


def _copy_models(tmp_path: Path) -> Path:
    dest = tmp_path / "models"
    shutil.copytree(DEFAULT_MODELS_DIR, dest)
    return dest


def test_load_model_exposes_rules_and_logs_counts(caplog):
    with caplog.at_level(logging.INFO, logger="app.classifier.model"):
        loaded = load_model(REAL_DIR)
    assert loaded.rules.version == "1.0"
    assert "rules 1.0: 51 confusion, 19 understanding" in caplog.text


def test_parse_what_you_hashed(tmp_path, monkeypatch):
    """parse_rules receives exactly the hashed bytes, and later file changes do nothing."""
    models = _copy_models(tmp_path)
    rules_path = models / "clf-v1.0.0" / "rules.yaml"
    meta = json.loads((models / "clf-v1.0.0" / "metadata.json").read_text(encoding="utf-8"))

    seen = []
    real_parse = model_mod.parse_rules
    monkeypatch.setattr(model_mod, "parse_rules", lambda b: (seen.append(b), real_parse(b))[1])
    loaded = load_model(models / "clf-v1.0.0")

    assert hashlib.sha256(seen[0]).hexdigest() == meta["files"]["rules.yaml"]
    before = loaded.rules.match("no idea")
    rules_path.write_bytes(b"garbage: [")
    assert loaded.rules.match("no idea") == before
    rules_path.unlink()
    assert loaded.rules.match("no idea") == before


def test_rules_failure_degrades_startup_like_any_verification_failure(tmp_path, caplog):
    """Valid hash but invalid rules content: degraded start, ERROR log, no model stored."""
    models = _copy_models(tmp_path)
    d = models / "clf-v1.0.0"
    bad = (d / "rules.yaml").read_bytes().replace(b'  - "no idea"\n', b'  - "no idea"\n  - "no idea"\n', 1)
    (d / "rules.yaml").write_bytes(bad)
    meta = json.loads((d / "metadata.json").read_text(encoding="utf-8"))
    meta["files"]["rules.yaml"] = hashlib.sha256(bad).hexdigest()  # hash now passes
    (d / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")

    app_logger = logging.getLogger("app")
    app_logger.addHandler(caplog.handler)
    caplog.set_level(logging.ERROR, logger="app")
    try:
        with TestClient(create_app(models)) as client:
            body = client.get("/health").json()
            assert client.app.state.model is None
    finally:
        app_logger.removeHandler(caplog.handler)
    assert body == {
        "status": "degraded", "model_loaded": False, "llm_reachable": False, "model_version": None,
        "llm_gpu_fraction": None,
    }
    assert "duplicate phrase" in caplog.text

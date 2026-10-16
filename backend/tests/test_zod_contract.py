"""S10: real backend responses through the frontend's own Zod schemas, and the committed captures.

The Zod tests need dev/frontend and Node, which the Docker image does not have: they skip there with a
visible reason (like the fixture drift guards) and FAIL, not skip, in a venv where the frontend is
present but node_modules or node is missing. The classifier behind the labels is a prototype proxy
trained on synthetic answers.
"""

import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]


def _load(name):
    path = BACKEND / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


capture = _load("capture_contract_responses")
zod_check = _load("zod_contract_check")

COMMITTED = BACKEND / "tests" / "contract_captures"
TUTOR_FILES = [
    "explain.cycle1.json", "explain.request.json", "clarify.json", "offer_new_cycle.json",
    "explain.cycle2.json", "resolved.json", "end_unresolved.json",
]


@pytest.fixture(scope="module")
def fresh(tmp_path_factory):
    out = tmp_path_factory.mktemp("captures")
    capture.write_captures(out)
    return out


def _require_zod_environment():
    if not zod_check.FRONTEND_DIR.is_dir():
        pytest.skip(f"frontend not present in this environment: {zod_check.FRONTEND_DIR}")
    reason = zod_check.preflight()
    if reason:
        pytest.fail(f"frontend present but the Zod check cannot run: {reason}")


# --- the Zod check ------------------------------------------------------------------------------------


def test_real_responses_pass_the_frontend_zod_schemas(fresh):
    _require_zod_environment()
    assert zod_check.run_check(fresh) == 0


def test_negative_control_a_broken_response_fails_the_zod_check(fresh, tmp_path):
    """Without this, a runner that always returns 0 would pass the test above."""
    _require_zod_environment()
    broken = tmp_path / "broken"
    shutil.copytree(fresh, broken)
    data = json.loads((broken / "explain.cycle1.json").read_text(encoding="utf-8"))
    del data["meta"]
    (broken / "explain.cycle1.json").write_text(json.dumps(data), encoding="utf-8")
    code = zod_check.run_check(broken)
    assert code != 0 and code != zod_check.EXIT_MISSING


def test_zod_runner_reports_a_missing_frontend_as_exit_2_never_0(tmp_path, monkeypatch):
    monkeypatch.setattr(zod_check, "FRONTEND_DIR", tmp_path / "no_frontend")
    assert zod_check.run_check(tmp_path) == 2
    assert zod_check.main([str(tmp_path)]) == 2  # no manifest either


# --- the committed set --------------------------------------------------------------------------------


def test_committed_captures_equal_a_fresh_rebuild_byte_for_byte(fresh):
    """Needs no frontend, so it runs in Docker too. Regenerate with scripts/capture_contract_responses.py."""
    fresh_names = sorted(p.name for p in fresh.iterdir())
    assert sorted(p.name for p in COMMITTED.iterdir()) == fresh_names
    for name in fresh_names:
        assert (COMMITTED / name).read_bytes() == (fresh / name).read_bytes(), name


def test_captures_have_zeroed_latency_and_lf_endings(fresh):
    for name in TUTOR_FILES:
        raw = (fresh / name).read_bytes()
        assert b"\r" not in raw and raw.endswith(b"\n")
        lat = json.loads(raw)["meta"]["latency_ms"]
        assert lat == {"classify": 0.0, "llm": 0.0, "total": 0.0}


# --- the 07 section 2 rules, in Python, on fresh captures --------------------------------------------------
# tests/test_tutor_message.py asserts them through frontend_sim.contract_violations on real episodes; these
# re-assert them on the capture set itself so they hold where Zod cannot run.


@pytest.mark.parametrize("name", TUTOR_FILES)
def test_rules_hold_on_every_captured_tutor_response(fresh, name):
    res = json.loads((fresh / name).read_text(encoding="utf-8"))
    manifest = json.loads((fresh / "manifest.json").read_text(encoding="utf-8"))
    assert res["request_id"] == manifest[name]["request_id"]  # echoed
    terminal = res["action"] in ("resolved", "end_unresolved")
    assert (res["episode_log"] is not None) == terminal
    if res["action"] == "explain":
        assert res["strategy"]
    p = res["confusion"]["probability"]
    assert isinstance(p, float) and 0 <= p <= 1


def test_every_expected_action_is_in_the_capture_set(fresh):
    actions = {json.loads((fresh / n).read_text(encoding="utf-8"))["action"] for n in TUTOR_FILES}
    assert actions == {"explain", "clarify", "offer_new_cycle", "resolved", "end_unresolved"}
    req = json.loads((fresh / "explain.request.json").read_text(encoding="utf-8"))
    assert req["trigger"] == "request"
    # a rule-decided turn still carries a numeric probability (the model's own)
    clarify = json.loads((fresh / "clarify.json").read_text(encoding="utf-8"))
    assert clarify["confusion"]["source"] == "rule"

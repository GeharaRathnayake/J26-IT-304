"""T1: thinking mode (opt-in, off by default, its own model and timeout). Mock adapters and httpx.MockTransport
only; no real Ollama. Nothing here measures whether thinking replies are more accurate (they are not measured).
"""

import asyncio
import json
import logging

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

import app.orchestrator as orchestrator
from app.config import Settings
from app.generation.adapters import Completion, OllamaAdapter
from app.main import create_app
from frontend_sim import Episode, contract_violations
from test_tutor_message import CONFUSED, make_app

GOOD = "Short reply for testing.\n\n**Check:** Which part is unclear?"
THOUGHT = "SECRET-THOUGHT-zebra-9f3: the student wrote the phrase I must not reveal"


class Recording:
    """An adapter that records the timeout it was called with and returns a good reply (or sleeps/raises)."""

    def __init__(self, label, delay=0.0):
        self.label, self.delay = label, delay
        self.calls: list[tuple[str, float]] = []

    async def complete(self, prompt: str, timeout_s: float) -> Completion:
        self.calls.append((prompt, timeout_s))
        if self.delay:
            await asyncio.sleep(self.delay)
        return Completion(GOOD, False)


def app_with(default, thinking, **settings):
    s = Settings(_env_file=None, LLM_PROVIDER="ollama", **settings)
    return create_app(settings=s, adapter=default, thinking_adapter=thinking)


def post(c, ep, message, **extra):
    body = ep.body(message)
    body.update(extra)
    return c.post("/tutor/message", json=body)


# --- the request bodies -------------------------------------------------------------------------------------------


def _adapter(**kw):
    return OllamaAdapter(None, "http://ollama.test:11434", kw.pop("model", "llama3.2:3b"), kw.pop("max_tokens", 220), **kw)


def test_the_default_request_body_is_byte_identical_to_before_t1():
    """Expected value history: before T1 the body was built inline with KEEP_ALIVE; the key set, key order and
    values must not change (think False, stream False, keep_alive 30m, options.num_predict)."""
    body = _adapter().request_body("PROMPT")
    assert body == {
        "model": "llama3.2:3b", "messages": [{"role": "user", "content": "PROMPT"}], "think": False,
        "stream": False, "keep_alive": "30m", "options": {"num_predict": 220},
    }
    assert list(body) == ["model", "messages", "think", "stream", "keep_alive", "options"]
    assert json.dumps(body) == (
        '{"model": "llama3.2:3b", "messages": [{"role": "user", "content": "PROMPT"}], "think": false, '
        '"stream": false, "keep_alive": "30m", "options": {"num_predict": 220}}'
    )


def test_the_thinking_body_thinks_is_uncapped_and_names_the_thinking_model():
    body = _adapter(model="qwen3:4b", max_tokens=None, think=True, keep_alive="10m").request_body("PROMPT")
    assert body["think"] is True and body["model"] == "qwen3:4b" and body["keep_alive"] == "10m"
    assert "options" not in body and "num_predict" not in json.dumps(body)  # UNCAPPED, by ruling
    assert body["stream"] is False


def test_the_thinking_adapter_is_built_with_the_thinking_settings_and_never_warmed():
    seen = []

    def handler(request):
        seen.append(request)
        if request.url.path == "/api/chat":
            body = json.loads(request.content)
            seen.append(body)
            return httpx.Response(200, json={"message": {"role": "assistant", "content": GOOD}, "done": True, "done_reason": "stop"})
        return httpx.Response(200, json={"models": []})

    s = Settings(_env_file=None, LLM_PROVIDER="ollama", LLM_THINKING_MODEL="qwen3:4b", LLM_THINKING_KEEP_ALIVE="7m")
    with TestClient(create_app(settings=s, ollama_transport=httpx.MockTransport(handler))) as c:
        a = c.app.state.deps.thinking_adapter
        assert (a.model, a.think, a.keep_alive, a.max_tokens) == ("qwen3:4b", True, "7m", None)
        d = c.app.state.deps.adapter
        assert (d.model, d.think, d.keep_alive, d.max_tokens) == ("llama3.2:3b", False, "30m", 220)
    chat_bodies = [x for x in seen if isinstance(x, dict)]
    assert all(b["model"] != "qwen3:4b" for b in chat_bodies)  # no warm-up request ever went to the thinking model


# --- routing ----------------------------------------------------------------------------------------------------


def test_thinking_true_routes_to_the_thinking_adapter_with_its_own_timeout_and_names_its_model():
    default, thinking = Recording("default"), Recording("thinking")
    with TestClient(app_with(default, thinking)) as c:
        ep = Episode(c)
        r = post(c, ep, CONFUSED, thinking=True).json()
    assert len(thinking.calls) == 1 and default.calls == []
    assert thinking.calls[0][1] == 180.0
    assert r["meta"]["thinking"] is True and r["meta"]["llm"] == "ollama:qwen3:4b" and r["meta"]["fallback"] is False


@pytest.mark.parametrize("extra", [{}, {"thinking": False}])
def test_thinking_false_or_absent_routes_to_the_default_adapter_with_18_seconds(extra):
    default, thinking = Recording("default"), Recording("thinking")
    with TestClient(app_with(default, thinking)) as c:
        r = post(c, Episode(c), CONFUSED, **extra).json()
    assert len(default.calls) == 1 and thinking.calls == []
    assert default.calls[0][1] == 18.0
    assert r["meta"]["thinking"] is False and r["meta"]["llm"] == "ollama:llama3.2:3b"


def test_the_prompt_is_the_same_on_a_thinking_turn():
    default, thinking = Recording("d"), Recording("t")
    with TestClient(app_with(default, thinking)) as c:
        post(c, Episode(c, student_id="s1"), CONFUSED)
        post(c, Episode(c, student_id="s1"), CONFUSED, thinking=True)
    assert default.calls[0][0] == thinking.calls[0][0]


def test_a_thinking_timeout_serves_the_template_and_still_says_thinking(caplog):
    app_logger = logging.getLogger("app")
    app_logger.addHandler(caplog.handler)
    caplog.set_level(logging.INFO, logger="app")
    default, thinking = Recording("d"), Recording("t", delay=1.0)
    try:
        with TestClient(app_with(default, thinking, LLM_THINKING_TIMEOUT_S=0.05)) as c:
            r = post(c, Episode(c), CONFUSED, thinking=True).json()
    finally:
        app_logger.removeHandler(caplog.handler)
    assert r["meta"]["fallback"] is True and r["meta"]["thinking"] is True and r["meta"]["llm"] == "ollama:qwen3:4b"
    assert any("timeout" in rec.getMessage() for rec in caplog.records if rec.levelno == logging.WARNING)
    assert default.calls == []


def test_the_would_ship_gate_still_applies_to_a_thinking_reply():
    class Bad(Recording):
        async def complete(self, prompt, timeout_s):
            return Completion("", False)  # an empty reply is not shippable in form

    with TestClient(app_with(Recording("d"), Bad("t"))) as c:
        r = post(c, Episode(c), CONFUSED, thinking=True).json()
    assert r["meta"]["fallback"] is True and r["meta"]["thinking"] is True


@pytest.mark.parametrize("provider", ["template", "mock"])
def test_on_template_and_mock_providers_thinking_changes_only_meta_thinking(provider):
    with TestClient(make_app(LLM_PROVIDER=provider)) as c:
        off = Episode(c, student_id="s1")
        a = post(c, off, CONFUSED).json()
    with TestClient(make_app(LLM_PROVIDER=provider)) as c:
        on = Episode(c, student_id="s1")
        b = post(c, on, CONFUSED, thinking=True).json()
    assert (a["meta"]["thinking"], b["meta"]["thinking"]) == (False, True)
    for r in (a, b):
        r["meta"].pop("thinking"); r["meta"]["latency_ms"] = None
    assert a == b


# --- the contract -----------------------------------------------------------------------------------------------


def test_a_request_without_thinking_is_accepted_and_a_non_boolean_is_rejected():
    with TestClient(make_app()) as c:
        ep = Episode(c)
        body = ep.body(CONFUSED)
        assert "thinking" not in body
        assert c.post("/tutor/message", json=body).status_code == 200  # an old frontend
        assert c.post("/tutor/message", json={**ep.body(CONFUSED), "thinking": "yes"}).status_code == 422
        assert c.post("/tutor/message", json={**ep.body(CONFUSED), "thinking": 1}).status_code == 422
        assert c.post("/tutor/message", json={**ep.body(CONFUSED), "thinking": True}).status_code == 200


def test_responses_stay_contract_valid_with_thinking():
    with TestClient(app_with(Recording("d"), Recording("t"))) as c:
        r = post(c, Episode(c), CONFUSED, thinking=True).json()
    assert contract_violations(r, "req-1") == []


def test_classify_receives_the_current_message_only_on_a_thinking_turn_too(monkeypatch):
    seen = []
    real = orchestrator.classify

    def spy(model, text):
        seen.append(text)
        return real(model, text)

    monkeypatch.setattr(orchestrator, "classify", spy)
    with TestClient(app_with(Recording("d"), Recording("t"))) as c:
        ep = Episode(c)
        ep.send(CONFUSED)
        seen.clear()
        assert post(c, ep, "can you explain differently?", thinking=True).status_code == 200
    assert seen == ["can you explain differently?"] and all(type(t) is str for t in seen)


# --- the thinking text never leaks --------------------------------------------------------------------------------


def _thinking_transport(status=200, content=GOOD):
    def handler(request):
        if request.url.path == "/api/chat":
            body = json.loads(request.content)
            if body["model"] == "qwen3:4b":
                if status != 200:
                    return httpx.Response(status, text=THOUGHT)
                return httpx.Response(200, json={
                    "message": {"role": "assistant", "content": content, "thinking": THOUGHT},
                    "done": True, "done_reason": "stop",
                })
            return httpx.Response(200, json={"message": {"role": "assistant", "content": "ready"}, "done": True})
        return httpx.Response(200, json={"models": [{"name": "llama3.2:3b"}, {"name": "qwen3:4b"}]})

    return httpx.MockTransport(handler)


@pytest.mark.parametrize("status", [200, 500])
def test_the_thinking_text_appears_in_no_response_no_log_and_no_turn_log(tmp_path, caplog, status):
    app_logger = logging.getLogger("app")
    app_logger.addHandler(caplog.handler)
    caplog.set_level(logging.DEBUG)
    caplog.set_level(logging.DEBUG, logger="app")
    log_path = tmp_path / "turns.jsonl"
    s = Settings(_env_file=None, LLM_PROVIDER="ollama", TURN_LOG_PATH=log_path)
    try:
        with TestClient(create_app(settings=s, ollama_transport=_thinking_transport(status))) as c:
            r = post(c, Episode(c), CONFUSED, thinking=True)
    finally:
        app_logger.removeHandler(caplog.handler)
    assert r.status_code == 200
    assert "SECRET-THOUGHT" not in r.text
    assert "SECRET-THOUGHT" not in caplog.text and all("SECRET-THOUGHT" not in rec.getMessage() for rec in caplog.records)
    assert "SECRET-THOUGHT" not in log_path.read_text(encoding="utf-8")
    row = json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])
    assert row["thinking"] is True
    if status == 200:
        assert r.json()["response"] == GOOD and r.json()["meta"]["fallback"] is False
    else:
        assert r.json()["meta"]["fallback"] is True


def test_an_episode_log_never_carries_thinking_text():
    with TestClient(create_app(settings=Settings(_env_file=None, LLM_PROVIDER="ollama"),
                               ollama_transport=_thinking_transport())) as c:
        ep = Episode(c)
        first = post(c, ep, CONFUSED, thinking=True)
        ep.history += [{"role": "student", "text": CONFUSED, "ts": "t"}, {"role": "tutor", "text": first.json()["response"], "strategy": first.json()["strategy"], "ts": "t"}]
        ep.state = first.json()["updated_state"]
        out = [first, ep.send("got it")]  # the second turn resolves: a terminal turn builds an episode log
    assert out[1].json()["action"] == "resolved" and out[1].json()["episode_log"] is not None
    assert all("SECRET-THOUGHT" not in r.text for r in out)


# --- settings ---------------------------------------------------------------------------------------------------


def test_settings_defaults_and_validation():
    s = Settings(_env_file=None)
    assert (s.LLM_THINKING_MODEL, s.LLM_THINKING_TIMEOUT_S, s.LLM_THINKING_KEEP_ALIVE) == ("qwen3:4b", 180.0, "10m")
    assert s.LLM_TIMEOUT_S == 18.0  # untouched
    for bad in ({"LLM_THINKING_TIMEOUT_S": 0}, {"LLM_THINKING_TIMEOUT_S": -5}, {"LLM_THINKING_MODEL": "  "},
                {"LLM_THINKING_KEEP_ALIVE": "soon"}, {"LLM_THINKING_KEEP_ALIVE": ""}):
        with pytest.raises(ValidationError):
            Settings(_env_file=None, **bad)
    for good in ("10m", "30s", "1h", "0", "-1", "1.5h"):
        assert Settings(_env_file=None, LLM_THINKING_KEEP_ALIVE=good).LLM_THINKING_KEEP_ALIVE == good

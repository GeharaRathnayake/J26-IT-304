"""S8: the Ollama adapter, the ollama provider end to end, /health's real check and the warm-up.

No real Ollama is ever contacted: every test talks to httpx.MockTransport (tests/conftest.py also
forces the template provider and a closed port for everything else). The fake replies are
hand-written in the shapes observed in the benchmark (benchmarks/llm/): llama3.2:3b's truncated
example and qwen3:4b's untagged reasoning ("We are given the topic..."). The classifier is a prototype
proxy trained on synthetic answers.
"""

import asyncio
import json
import logging
import os
import re
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.generation.adapters import Completion, OllamaAdapter, OllamaError, TemplateFallback
from app.main import WARMUP_PROMPT, create_app
from frontend_sim import Episode, contract_violations

MODEL = "llama3.2:3b"
LABEL = "ollama:llama3.2:3b"
CONFUSED = "I don't understand"
TEMPLATES = TemplateFallback()
SECRET = "zebra-unique-student-phrase"

GOOD = {
    "theory": "Inheritance lets a class reuse the fields and methods of another class. The child extends the "
              "parent.\n\n**Check:** What does a child class get from its parent?",
    "example": "Here is a short example.\n\n```java\nclass Dog extends Animal {\n    void bark() {}\n}\n```\n\n"
               "Dog gets everything Animal has.\n\n**Check:** What else can a Dog do?",
    "simplified": "A child class copies what its parent can do. Then it adds more.\n\n**Check:** Which part is new?",
    "analogy": "A child class is like a child who inherits a family recipe book. They can add new recipes.\n\n"
               "**Check:** What is the recipe book in Java?",
}
# llama3.2:3b at the token cap: the code block is cut mid-block (benchmark shape).
TRUNCATED_EXAMPLE = "**Inheritance Example**\n=================\n\n```java\npublic class Dog extends Animal {\n    void bark() {\n        System.out"
# Truncated prose: shippable only when trimmed back to the last full sentence.
TRUNCATED_THEORY = (
    "**Inheritance in Java**\n======================\n\nInheritance is a fundamental concept in object-oriented "
    "programming. The child class inherits from the parent class.\n\nThe key rules of inheritance are"
)
# qwen3:4b's untagged reasoning (the exact opening the lead observed).
LEAKED = ("We are given the topic: Inheritance. We are to provide: theory. We must follow the instructions exactly. "
          "MODEL-OUTPUT-MARKER")


def chat_response(text, done_reason="stop"):
    return httpx.Response(200, json={
        "model": MODEL, "created_at": "2026-10-15T10:00:00Z",
        "message": {"role": "assistant", "content": text}, "done": True, "done_reason": done_reason,
    })


def tags_response(*names):
    return httpx.Response(200, json={"models": [{"name": n, "model": n} for n in names]})


class FakeOllama:
    """An async httpx.MockTransport handler shaped like Ollama 0.40's /api/chat and /api/tags."""

    def __init__(self, replies=None, tags=(MODEL,), warmup="ok", delay_s=0.0):
        self.replies = replies or {}  # strategy -> (text, done_reason)
        self.tags = tags
        self.warmup = warmup  # "ok" | "fail" | "hang"
        self.delay_s = delay_s
        self.requests: list[httpx.Request] = []
        self.chat_bodies: list[dict] = []
        self.warmup_bodies: list[dict] = []

    async def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.path == "/api/tags":
            if self.tags is None:
                raise httpx.ConnectError("connection refused", request=request)
            return tags_response(*self.tags)
        body = json.loads(request.content)
        prompt = body["messages"][0]["content"]
        if prompt == WARMUP_PROMPT:
            self.warmup_bodies.append(body)
            if self.warmup == "fail":
                raise httpx.ConnectError("connection refused", request=request)
            if self.warmup == "hang":
                await asyncio.sleep(3600)
            return chat_response("ready")
        self.chat_bodies.append(body)
        if self.delay_s:
            await asyncio.sleep(self.delay_s)
        strategy = re.search(r"^Strategy: (\w+)", prompt, re.MULTILINE).group(1)
        text, reason = self.replies.get(strategy, (GOOD[strategy], "stop"))
        if "Explanation cycle: 2" in prompt:  # the r2 prompt asks for a different angle in cycle 2
            text = "Put another way: " + text
        return chat_response(text, reason)


def make(fake=None, *, adapter=None, **settings):
    s = Settings(_env_file=None, **{"LLM_PROVIDER": "ollama", **settings})
    return create_app(settings=s, adapter=adapter, ollama_transport=httpx.MockTransport(fake) if fake else None)


@pytest.fixture
def app_log(caplog):
    """The 'app' logger sets propagate=False, so attach the capture handler directly."""
    app_logger = logging.getLogger("app")
    app_logger.addHandler(caplog.handler)
    caplog.set_level(logging.INFO, logger="app")
    yield caplog
    app_logger.removeHandler(caplog.handler)


def warnings_of(caplog):
    return [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]


def run(coro):
    return asyncio.run(coro)


async def _complete_with(handler, prompt="Topic: x\nStrategy: theory\n", timeout_s=5.0, **kw):
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        return await OllamaAdapter(client, "http://ollama.test:11434/", MODEL, kw.get("max_tokens", 110)).complete(prompt, timeout_s)


# --- the adapter ------------------------------------------------------------------------------------------------


def test_the_request_has_exactly_the_benchmarked_parameters():
    seen = []

    def handler(request):
        seen.append(request)
        return chat_response("Fine. **Check:** Ok?")

    run(_complete_with(handler, prompt="THE PROMPT", timeout_s=14.0))
    (req,) = seen
    assert req.method == "POST" and str(req.url) == "http://ollama.test:11434/api/chat"
    assert json.loads(req.content) == {
        "model": "llama3.2:3b",
        "messages": [{"role": "user", "content": "THE PROMPT"}],  # the prompt as ONE user message
        "think": False,
        "stream": False,
        "keep_alive": "30m",
        "options": {"num_predict": 110},
    }
    assert req.extensions["timeout"]["read"] == 14.0


@pytest.mark.parametrize("done_reason, truncated", [("length", True), ("stop", False), (None, False)])
def test_done_reason_length_and_only_length_means_truncated(done_reason, truncated):
    got = run(_complete_with(lambda r: chat_response("Some text.", done_reason)))
    assert got == Completion(text="Some text.", truncated=truncated)


@pytest.mark.parametrize("status", [400, 404, 500, 503])
def test_a_non_2xx_response_raises(status):
    with pytest.raises(OllamaError, match=str(status)):
        run(_complete_with(lambda r: httpx.Response(status, json={"error": "model 'llama3.2:3b' not found"})))


def test_a_connection_error_raises():
    def refused(request):
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(httpx.ConnectError):
        run(_complete_with(refused))


@pytest.mark.parametrize("response", [
    httpx.Response(200, content=b"not json"),
    httpx.Response(200, json={"done": True}),  # no message
    httpx.Response(200, json={"message": {"role": "assistant"}}),  # no content
    httpx.Response(200, json={"message": {"content": None}}),  # content not a string
    httpx.Response(200, json=["a", "list"]),
], ids=["not-json", "no-message", "no-content", "content-null", "list-body"])
def test_a_malformed_body_raises(response):
    with pytest.raises(OllamaError, match="malformed"):
        run(_complete_with(lambda r: response))


# --- the orchestrator under the ollama provider -------------------------------------------------------------------


def test_a_good_reply_is_served_with_fallback_false_and_the_model_label(app_log):
    fake = FakeOllama()
    with TestClient(make(fake)) as c:
        res = Episode(c).play(f"{SECRET} {CONFUSED}", CONFUSED)
    for i, r in enumerate(res, start=1):
        assert contract_violations(r, f"req-{i}") == []
        assert r["meta"]["fallback"] is False and r["meta"]["llm"] == LABEL
    assert res[0]["response"] == GOOD["theory"] and res[1]["response"] == GOOD["example"]
    assert res[1]["updated_state"]["prior_explanations"] == [GOOD["theory"], GOOD["example"]]
    assert len(fake.chat_bodies) == 2
    assert not [w for w in warnings_of(app_log) if "LLM reply not served" in w]


def test_a_truncated_example_serves_the_template_with_a_not_usable_warning(app_log):
    fake = FakeOllama(replies={"example": (TRUNCATED_EXAMPLE, "length")})
    with TestClient(make(fake)) as c:
        theory, example = Episode(c).play(CONFUSED, f"{SECRET} {CONFUSED}")
    assert theory["meta"]["fallback"] is False
    assert example["strategy"] == "example"
    assert example["response"] == TEMPLATES.get("inheritance", "example", 1)
    assert example["meta"]["fallback"] is True and example["meta"]["llm"] == LABEL  # the label stays on a fallback turn
    assert example["updated_state"]["prior_explanations"][-1] == example["response"]  # what was actually served
    assert "System.out" not in example["response"]
    served = [w for w in warnings_of(app_log) if "LLM reply not served" in w]
    assert len(served) == 1 and "(not_usable)" in served[0]


def test_a_truncated_theory_is_trimmed_to_its_last_full_sentence_and_served():
    fake = FakeOllama(replies={"theory": (TRUNCATED_THEORY, "length")})
    with TestClient(make(fake)) as c:
        (r,) = Episode(c).play(CONFUSED)
    assert r["meta"]["fallback"] is False
    assert "The key rules of inheritance are" not in r["response"] and "=====" not in r["response"]
    assert r["response"].startswith("Inheritance is a fundamental concept")
    assert r["response"].splitlines()[-1].startswith("**Check:**")


def test_a_leaked_reply_serves_the_template_with_a_reasoning_leak_warning(app_log):
    fake = FakeOllama(replies={"theory": (LEAKED, "length")})
    with TestClient(make(fake)) as c:
        (r,) = Episode(c).play(f"{SECRET} {CONFUSED}")
    assert r["response"] == TEMPLATES.get("inheritance", "theory", 1)
    assert r["meta"]["fallback"] is True and r["meta"]["llm"] == LABEL
    served = [w for w in warnings_of(app_log) if "LLM reply not served" in w]
    assert len(served) == 1 and "(reasoning_leak)" in served[0]


def test_a_slow_model_is_cut_off_at_the_timeout_and_the_template_served(app_log):
    fake = FakeOllama(delay_s=5.0)
    started = time.perf_counter()
    with TestClient(make(fake, LLM_TIMEOUT_S=0.3)) as c:
        (r,) = Episode(c).play(CONFUSED)
    assert time.perf_counter() - started < 4.0  # did not wait the 5 s
    assert r["meta"]["fallback"] is True and r["meta"]["llm"] == LABEL
    assert r["response"] == TEMPLATES.get("inheritance", "theory", 1)
    assert r["meta"]["latency_ms"]["llm"] < 2000
    served = [w for w in warnings_of(app_log) if "LLM reply not served" in w]
    assert len(served) == 1 and "(timeout)" in served[0]


def test_an_ollama_error_names_the_error_type(app_log):
    async def boom(request):
        if request.url.path == "/api/chat" and WARMUP_PROMPT not in request.content.decode():
            return httpx.Response(500, json={"error": f"{SECRET} echoed back"})
        return chat_response("ready")

    with TestClient(make(boom)) as c:
        (r,) = Episode(c).play(CONFUSED)
    assert r["meta"]["fallback"] is True
    served = [w for w in warnings_of(app_log) if "LLM reply not served" in w]
    assert len(served) == 1 and "(OllamaError)" in served[0]
    assert SECRET not in app_log.text


def test_no_warning_ever_contains_the_student_message_or_the_model_output(app_log):
    fake = FakeOllama(replies={"theory": (LEAKED, "stop"), "example": (TRUNCATED_EXAMPLE, "length"),
                               "simplified": ("half a sent", "length")})
    with TestClient(make(fake)) as c:
        res = Episode(c).play(*[f"{SECRET} {CONFUSED}"] * 3)
    assert [r["meta"]["fallback"] for r in res] == [True, True, True]
    assert len([w for w in warnings_of(app_log) if "LLM reply not served" in w]) == 3
    everything = "\n".join(r.getMessage() for r in app_log.records)
    assert SECRET not in everything
    for fragment in ("MODEL-OUTPUT-MARKER", "We are given", "System.out", "half a sent", "Dog extends"):
        assert fragment not in everything


def test_fixed_copy_turns_carry_the_label_and_are_not_a_fallback():
    with TestClient(make(FakeOllama())) as c:
        res = Episode(c).play(*[CONFUSED] * 5)
    assert res[-1]["action"] == "offer_new_cycle"
    assert res[-1]["meta"]["llm"] == LABEL and res[-1]["meta"]["fallback"] is False
    assert res[-1]["meta"]["latency_ms"]["llm"] == 0


def test_the_prompt_sent_to_ollama_is_the_r2_prompt_with_the_raw_student_message():
    fake = FakeOllama()
    msg = "  I DON'T understand\tthis  "
    with TestClient(make(fake)) as c:
        Episode(c).play(msg)
    content = fake.chat_bodies[0]["messages"][0]["content"]
    assert f"<student_message>\n{msg}\n</student_message>" in content
    assert "Do not use headings, titles or bold title lines." in content


# --- /health ----------------------------------------------------------------------------------------------------------


def test_health_is_reachable_when_ollama_answers_with_the_model_listed():
    fake = FakeOllama(tags=("qwen3:4b", MODEL))
    with TestClient(make(fake)) as c:
        body = c.get("/health").json()
    assert body["llm_reachable"] is True and body["status"] == "ok"
    tags = [r for r in fake.requests if r.url.path == "/api/tags"]
    assert len(tags) == 1 and tags[0].method == "GET"
    assert tags[0].extensions["timeout"]["read"] == 1.0  # a cheap check


def test_health_checks_on_every_call():
    fake = FakeOllama()
    with TestClient(make(fake)) as c:
        first = c.get("/health").json()["llm_reachable"]
        fake.tags = None  # Ollama goes away mid-session
        second = c.get("/health").json()["llm_reachable"]
    assert (first, second) == (True, False)


@pytest.mark.parametrize("tags", [("qwen3:4b",), (), ("llama3.2:1b", "llama3.2")], ids=["other-model", "none", "near-miss"])
def test_health_is_unreachable_when_the_model_is_not_pulled(tags):
    with TestClient(make(FakeOllama(tags=tags))) as c:
        body = c.get("/health").json()
    assert body["llm_reachable"] is False and body["status"] == "ok"


def test_health_is_unreachable_when_the_connection_is_refused():
    with TestClient(make(FakeOllama(tags=None, warmup="fail"))) as c:
        body = c.get("/health").json()
    assert body == {**body, "llm_reachable": False, "status": "ok", "model_loaded": True}


@pytest.mark.parametrize("response", [httpx.Response(500), httpx.Response(200, content=b"<html>"),
                                      httpx.Response(200, json={"models": "nope"})], ids=["500", "html", "bad-shape"])
def test_health_is_unreachable_on_a_bad_tags_answer(response):
    async def handler(request):
        return response if request.url.path == "/api/tags" else chat_response("ready")

    with TestClient(make(handler)) as c:
        assert c.get("/health").json()["llm_reachable"] is False


@pytest.mark.parametrize("provider", ["template", "mock"])
def test_health_is_unreachable_under_the_template_and_mock_providers(provider):
    fake = FakeOllama()
    with TestClient(make(fake, LLM_PROVIDER=provider)) as c:
        assert c.get("/health").json()["llm_reachable"] is False
    assert fake.requests == []  # not even asked


# --- warm-up ------------------------------------------------------------------------------------------------------------


def _wait_for_warm_up(c: TestClient):
    async def wait(task):
        await asyncio.wait_for(asyncio.shield(task), 5.0)

    c.portal.call(wait, c.app.state.warm_up)


def test_a_successful_warm_up_logs_its_duration_at_info(app_log):
    fake = FakeOllama()
    with TestClient(make(fake)) as c:
        _wait_for_warm_up(c)
    assert len(fake.warmup_bodies) == 1
    assert fake.warmup_bodies[0]["keep_alive"] == "30m" and fake.warmup_bodies[0]["model"] == MODEL
    infos = [r.getMessage() for r in app_log.records if r.levelno == logging.INFO]
    assert any(re.fullmatch(r"LLM warm-up done: llama3\.2:3b loaded in \d+\.\d s", m) for m in infos)


def test_a_failing_warm_up_does_not_fail_startup_and_logs_a_warning(app_log):
    fake = FakeOllama(warmup="fail")
    with TestClient(make(fake)) as c:
        _wait_for_warm_up(c)
        assert c.get("/health").status_code == 200
        (r,) = Episode(c).play(CONFUSED)  # the service still answers
    assert r["meta"]["fallback"] is False  # chat itself works in this fake; only the warm-up failed
    assert any(w.startswith("LLM warm-up failed (ConnectError)") for w in warnings_of(app_log))


def test_startup_does_not_wait_for_the_warm_up():
    fake = FakeOllama(warmup="hang")  # the warm-up never finishes
    started = time.perf_counter()
    with TestClient(make(fake)) as c:
        assert time.perf_counter() - started < 10.0
        assert c.app.state.warm_up is not None and not c.app.state.warm_up.done()
        assert c.get("/health").json()["status"] == "ok"
        (r,) = Episode(c).play(CONFUSED)
        assert r["meta"]["fallback"] is False
    assert c.app.state.warm_up.cancelled()  # cancelled cleanly on shutdown


def test_no_warm_up_under_the_template_and_mock_providers():
    for provider in ("template", "mock"):
        with TestClient(make(FakeOllama(), LLM_PROVIDER=provider)) as c:
            assert c.app.state.warm_up is None


def test_the_http_client_is_created_once_and_closed_on_shutdown():
    with TestClient(make(FakeOllama())) as c:
        adapter = c.app.state.adapter
        assert isinstance(adapter, OllamaAdapter) and not adapter.client.is_closed
        Episode(c).play(CONFUSED, CONFUSED)
        c.get("/health")
        assert c.app.state.adapter.client is adapter.client
    assert adapter.client.is_closed


# --- the test guard (tests/conftest.py) -------------------------------------------------------------------------------------


def test_the_guard_forces_the_template_provider_and_a_closed_port():
    assert os.environ["LLM_PROVIDER"] == "template"
    assert os.environ["OLLAMA_URL"] == "http://127.0.0.1:9"
    s = Settings()
    assert (s.LLM_PROVIDER, s.OLLAMA_URL) == ("template", "http://127.0.0.1:9")


def test_with_the_guard_active_no_request_reaches_the_network(monkeypatch):
    """A default app (no settings, no injection) runs its whole lifespan, /health and a full explain
    turn, and httpx's real transports are never used."""
    attempts = []

    async def no_async(self, request):
        attempts.append(str(request.url))
        raise AssertionError(f"network request attempted: {request.url}")

    def no_sync(self, request):
        attempts.append(str(request.url))
        raise AssertionError(f"network request attempted: {request.url}")

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", no_async)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", no_sync)
    with TestClient(create_app()) as c:
        health = c.get("/health").json()
        (r,) = Episode(c).play(CONFUSED)
    assert attempts == []
    assert health["llm_reachable"] is False
    assert r["meta"]["llm"] == "template" and r["meta"]["fallback"] is True


# --- the smoke script under the ollama provider -------------------------------------------------------------------------------------


def load_smoke():
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "scripts" / "smoke_episode.py"
    spec = importlib.util.spec_from_file_location("smoke_episode", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_smoke_script_accepts_the_ollama_provider_with_generated_and_fallen_back_turns():
    smoke = load_smoke()
    fake = FakeOllama(replies={"example": (TRUNCATED_EXAMPLE, "length")})  # one explain falls back
    with TestClient(make(fake)) as c:
        rows, violations, log = smoke.run_episode(c)
    assert violations == [] and log is not None
    explains = [r for r in rows if r["action"] == "explain"]
    assert [r["fallback"] for r in explains] == [False, True, False, False, False]
    assert {r["llm_label"] for r in rows} == {LABEL}
    assert all(r["wall"] > 0 for r in rows)


def test_smoke_script_flags_a_fixed_copy_turn_marked_as_fallback_under_ollama():
    smoke = load_smoke()
    res = {"action": "offer_new_cycle", "meta": {"llm": LABEL, "fallback": True}}
    assert smoke.expected_fallback("offer_new_cycle", LABEL, smoke.AUTO) is False
    assert any("meta.fallback is True, expected False" in v for v in smoke.contract_violations(res, "x", smoke.AUTO))


def test_smoke_script_can_require_every_explain_turn_to_fall_back():
    smoke = load_smoke()
    with TestClient(make(FakeOllama())) as c:  # everything generates
        _, violations, _ = smoke.run_episode(c, expect_fallback=True)
    assert any("meta.fallback is False, expected True (explain" in v for v in violations)


def test_the_fixture_readme_lists_every_fixture_file():
    from pathlib import Path

    folder = Path(__file__).resolve().parent / "contract_fixtures"
    readme = (folder / "README.md").read_text(encoding="utf-8")
    names = sorted(p.name for p in folder.glob("*.json"))
    assert len(names) == 4
    for name in names:
        assert f"| `{name}` | `dev/frontend/src/features/tutor/api/fixtures/{name}` |" in readme

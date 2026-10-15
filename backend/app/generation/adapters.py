"""LLM adapter protocol, the Ollama adapter, a mock for tests, and the validated template fallback.

The template replies are a fallback, not the research contribution. Under the default `ollama`
provider every reply that would not ship (see `postprocess.would_ship`) is replaced by a template.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, get_args

import httpx
import yaml

from app.generation.postprocess import CHECK
from app.schemas import Strategy
from app.topics import GENERAL, public_topics

DEFAULT_TEMPLATES = Path(__file__).resolve().parent / "fallbacks.yaml"
STRATEGIES: tuple[str, ...] = get_args(Strategy)
_WEAK = re.compile(r"\bweak\b", re.IGNORECASE)
_JAVA_BLOCK = re.compile(r"^```java[^\n]*\n.*?^```[ \t]*$", re.DOTALL | re.MULTILINE)
_FENCE_LINE = re.compile(r"^\s*```", re.MULTILINE)


@dataclass(frozen=True)
class Completion:
    """One generation: the raw text and whether the model stopped at the token cap."""

    text: str
    truncated: bool


class LLMAdapter(Protocol):
    async def complete(self, prompt: str, timeout_s: float) -> Completion: ...


class MockAdapter:
    """Deterministic, no network, no model. Output obeys the format (ends with a Check line).
    `raw` makes it return that exact string instead, and `truncated` sets the cap flag, so tests can
    feed it malformed or cut-off output."""

    def __init__(self, raw: str | None = None, truncated: bool = False) -> None:
        self.raw = raw
        self.truncated = truncated
        self.prompts: list[str] = []

    async def complete(self, prompt: str, timeout_s: float) -> Completion:
        self.prompts.append(prompt)
        if self.raw is not None:
            return Completion(self.raw, self.truncated)
        if re.search(r"^Strategy: example\b", prompt, re.MULTILINE):
            return Completion(
                "Here is a mock example for testing:\n\n"
                "```java\nint x = 1;\n```\n\n"
                "It declares one variable.\n\n"
                f"{CHECK} What value does x hold?",
                self.truncated,
            )
        return Completion(
            "This is a mock explanation used for testing, with no model involved. "
            "It always follows the output format.\n\n"
            f"{CHECK} Can you say that back in your own words?",
            self.truncated,
        )


class OllamaError(RuntimeError):
    """Ollama answered, but not with a usable /api/chat body (non-2xx or malformed)."""


# Must match the benchmark's call (scripts/benchmark_llm.py `call_parameters`) except `stream`:
# the benchmark streams to time the first token; the service waits for the whole reply.
KEEP_ALIVE = "30m"  # the model stays loaded through a demo


class OllamaAdapter:
    """POST {base_url}/api/chat, non-streaming. The httpx.AsyncClient is owned by the caller (created
    once in the lifespan, closed on shutdown), so tests can build one on httpx.MockTransport.
    Any failure RAISES; the orchestrator turns an exception into the template fallback."""

    def __init__(self, client: httpx.AsyncClient, base_url: str, model: str, max_tokens: int) -> None:
        self.client = client
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.max_tokens = max_tokens

    def request_body(self, prompt: str) -> dict[str, Any]:
        return {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "think": False,
            "stream": False,
            "keep_alive": KEEP_ALIVE,
            "options": {"num_predict": self.max_tokens},
        }

    async def complete(self, prompt: str, timeout_s: float) -> Completion:
        resp = await self.client.post(f"{self.base_url}/api/chat", json=self.request_body(prompt), timeout=timeout_s)
        if not resp.is_success:
            raise OllamaError(f"/api/chat answered HTTP {resp.status_code}")
        try:
            body = resp.json()
            text = body["message"]["content"]
            done_reason = body.get("done_reason")
        except (ValueError, KeyError, TypeError) as exc:
            raise OllamaError(f"malformed /api/chat body ({type(exc).__name__})") from exc
        if not isinstance(text, str):
            raise OllamaError("malformed /api/chat body (content is not a string)")
        return Completion(text=text, truncated=done_reason == "length")

    async def reachable(self, timeout_s: float = 1.0) -> bool:
        """GET /api/tags: True only if Ollama answers AND the model is pulled. Never raises."""
        try:
            resp = await self.client.get(f"{self.base_url}/api/tags", timeout=timeout_s)
            if not resp.is_success:
                return False
            names = {m.get("name") for m in resp.json().get("models", []) if isinstance(m, dict)}
        except Exception:
            return False
        return self.model in names


class TemplateError(ValueError):
    """fallbacks.yaml is missing an entry or an entry breaks the output format."""


def _validate_variant(where: str, strategy: str, text: object) -> str:
    if not isinstance(text, str) or not text.strip():
        raise TemplateError(f"{where}: variant must be a non-empty string")
    text = text.strip()
    non_empty = [line for line in text.splitlines() if line.strip()]
    if not non_empty[-1].startswith(CHECK):
        raise TemplateError(f"{where}: last non-empty line must start with {CHECK}")
    if text.count(CHECK) != 1:
        raise TemplateError(f"{where}: must contain exactly one {CHECK} line")
    if len(_FENCE_LINE.findall(text)) % 2 != 0:
        raise TemplateError(f"{where}: unclosed code fence")
    if strategy == "example" and not _JAVA_BLOCK.search(text):
        raise TemplateError(f"{where}: an example needs a closed ```java block")
    if _WEAK.search(text):
        raise TemplateError(f"{where}: contains a word that must never be shown to students")
    if re.search(r"</?think>", text, re.IGNORECASE):
        raise TemplateError(f"{where}: contains a <think> tag")
    return text


def parse_templates(data: bytes) -> dict[str, dict[str, list[str]]]:
    try:
        doc = yaml.safe_load(data)
    except yaml.YAMLError as exc:
        raise TemplateError(f"fallbacks.yaml is not valid YAML: {exc!r}") from exc
    if not isinstance(doc, dict) or not isinstance(doc.get("templates"), dict):
        raise TemplateError("fallbacks.yaml must have a top-level 'templates' mapping")
    raw = doc["templates"]
    expected_topics = [t["id"] for t in public_topics()] + [GENERAL]
    unknown = set(raw) - set(expected_topics)
    if unknown:
        raise TemplateError(f"unknown topic(s) in fallbacks.yaml: {sorted(unknown)}")
    out: dict[str, dict[str, list[str]]] = {}
    for topic in expected_topics:
        if topic not in raw or not isinstance(raw[topic], dict):
            raise TemplateError(f"missing topic: {topic}")
        unknown_s = set(raw[topic]) - set(STRATEGIES)
        if unknown_s:
            raise TemplateError(f"{topic}: unknown strategy {sorted(unknown_s)}")
        out[topic] = {}
        for strategy in STRATEGIES:
            variants = raw[topic].get(strategy)
            if variants is None:
                raise TemplateError(f"missing strategy: {topic}/{strategy}")
            if not isinstance(variants, list) or not variants:
                raise TemplateError(f"{topic}/{strategy}: needs at least one variant")
            out[topic][strategy] = [
                _validate_variant(f"{topic}/{strategy}[{i}]", strategy, v) for i, v in enumerate(variants)
            ]
    return out


class TemplateFallback:
    """Loads and validates the templates once, at construction."""

    def __init__(self, data: bytes | None = None) -> None:
        self._templates = parse_templates(DEFAULT_TEMPLATES.read_bytes() if data is None else data)

    def get(self, topic: str, strategy: str, cycle: int) -> str:
        if cycle < 1:
            raise ValueError("cycle must be >= 1")
        try:
            variants = self._templates[topic][strategy]
        except KeyError:
            raise KeyError(f"no template for {topic}/{strategy}") from None
        return variants[(cycle - 1) % len(variants)]

    def variants(self, topic: str, strategy: str) -> list[str]:
        return list(self._templates[topic][strategy])

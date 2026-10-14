"""LLM adapter protocol, a mock for tests, and the validated template fallback.

No Ollama adapter yet (a later stage, after the model benchmark). The template replies are a
fallback, not the research contribution.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Protocol, get_args

import yaml

from app.generation.postprocess import CHECK
from app.schemas import Strategy
from app.topics import GENERAL, public_topics

DEFAULT_TEMPLATES = Path(__file__).resolve().parent / "fallbacks.yaml"
STRATEGIES: tuple[str, ...] = get_args(Strategy)
_WEAK = re.compile(r"\bweak\b", re.IGNORECASE)
_JAVA_BLOCK = re.compile(r"^```java[^\n]*\n.*?^```[ \t]*$", re.DOTALL | re.MULTILINE)
_FENCE_LINE = re.compile(r"^\s*```", re.MULTILINE)


class LLMAdapter(Protocol):
    async def complete(self, prompt: str, timeout_s: float) -> str: ...


class MockAdapter:
    """Deterministic, no network, no model. Output obeys the format (ends with a Check line).
    `raw` makes it return that exact string instead, so tests can feed it malformed output."""

    def __init__(self, raw: str | None = None) -> None:
        self.raw = raw
        self.prompts: list[str] = []

    async def complete(self, prompt: str, timeout_s: float) -> str:
        self.prompts.append(prompt)
        if self.raw is not None:
            return self.raw
        if re.search(r"^Strategy: example\b", prompt, re.MULTILINE):
            return (
                "Here is a mock example for testing:\n\n"
                "```java\nint x = 1;\n```\n\n"
                "It declares one variable.\n\n"
                f"{CHECK} What value does x hold?"
            )
        return (
            "This is a mock explanation used for testing, with no model involved. "
            "It always follows the output format.\n\n"
            f"{CHECK} Can you say that back in your own words?"
        )


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

"""Explicit-phrase rule layer (models/clf-v1.0.0/rules.yaml), a port of the reference.

This is a prototype hybrid over a proxy classifier trained on synthetic answers; it is
not a validated confusion detector. The rule layer exists because that classifier is
badly wrong on the messages that matter most (it scores "that makes sense" at ~0.99
confused), so without rules a student who says "got it" would never resolve an episode.

Matching rule, exactly (ported from experiment1/confusion_baseline/rules.py, not imported):

    normalise = lowercase; replace U+2018 / U+2019 with "'"; collapse whitespace; strip.
    Each phrase is matched as a whole-word sequence: regex \\b<phrase>\\b on the normalised text.
    confusion_phrases are checked first, then understanding_phrases, each in file order.
    The first match decides; no match means fall through to the model.

Normalisation is for the rules ONLY. The classifier always receives the raw text.

NOTE 1, the asymmetry. When the phrase list changes, prefer adding CONFUSION phrases over
understanding phrases. A false "understood" means the tutor moves on while the student is
lost; a false "confused" costs one unnecessary explanation. Any list change is a new model
version directory owned by another workstream, never an edit here.

NOTE 2, deliberately not built. A negation guard on understanding phrases (it would fix
"that makes sense in theory but ...") and treating short unmatched messages as uncertain are
both WAITING FOR EVIDENCE, not rejected. Per-turn logging, which arrives with the tutoring
endpoint, will show whether those cases are common. Do not add either without that evidence,
because each changes behaviour that tests pin.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import yaml

from app.classifier.errors import ModelLoadError

_WS = re.compile(r"\s+")
_LISTS = (("confusion_phrases", "confused"), ("understanding_phrases", "understood"))


def normalise(text: str) -> str:
    t = str(text).lower().replace("‘", "'").replace("’", "'")
    return _WS.sub(" ", t).strip()


@dataclass(frozen=True)
class Rules:
    version: str
    confusion_phrases: tuple[str, ...]
    understanding_phrases: tuple[str, ...]
    # (label, phrase, compiled regex) in decision order: confusion first, then understanding.
    compiled: tuple[tuple[str, str, re.Pattern], ...]

    def match(self, text: str) -> tuple[str | None, str | None]:
        """Return ('confused' | 'understood' | None, matched_phrase). None means: ask the model."""
        t = normalise(text)
        for label, phrase, rx in self.compiled:
            if rx.search(t):
                return label, phrase
        return None, None


def parse_rules(data: bytes) -> Rules:
    """Parse and validate rules.yaml bytes. Raises ModelLoadError (never `assert`).

    Callers pass the same bytes that were hashed, so the file cannot change between
    check and use.
    """
    try:
        doc = yaml.safe_load(data)
    except yaml.YAMLError as exc:
        raise ModelLoadError(f"rules.yaml is not valid YAML: {exc!r}") from exc
    if not isinstance(doc, dict):
        raise ModelLoadError("rules.yaml must be a mapping")
    version = doc.get("version")
    if not isinstance(version, str) or not version:
        raise ModelLoadError("rules.yaml 'version' must be a non-empty string")

    compiled: list[tuple[str, str, re.Pattern]] = []
    seen: set[str] = set()
    lists: dict[str, tuple[str, ...]] = {}
    for key, label in _LISTS:
        phrases = doc.get(key)
        if not isinstance(phrases, list) or not phrases:
            raise ModelLoadError(f"rules.yaml {key} must be a non-empty list")
        for p in phrases:
            if not isinstance(p, str) or not p or p != normalise(p):
                raise ModelLoadError(f"rules.yaml phrase not in normalised form: {p!r}")
            if p in seen:
                raise ModelLoadError(f"rules.yaml duplicate phrase: {p!r}")
            seen.add(p)
            compiled.append((label, p, re.compile(r"\b" + re.escape(p) + r"\b")))
        lists[key] = tuple(phrases)
    return Rules(
        version=version,
        confusion_phrases=lists["confusion_phrases"],
        understanding_phrases=lists["understanding_phrases"],
        compiled=tuple(compiled),
    )

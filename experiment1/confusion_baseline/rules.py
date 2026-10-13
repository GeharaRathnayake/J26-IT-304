"""Reference implementation of the explicit-phrase rule layer (models/clf-v1.0.0/rules.yaml).

The matching rule is documented in the header of rules.yaml; this module implements it exactly:

    normalise = lowercase; replace U+2018 / U+2019 with "'"; collapse whitespace; strip.
    Each phrase is matched as a whole-word sequence: regex \\b<phrase>\\b on the normalised text.
    confusion_phrases are checked first, then understanding_phrases, each in file order.
    The first match decides; no match means fall through to the model.
"""

import re
from pathlib import Path

import yaml

from confusion_baseline import MODELS_DIR

RULES_PATH = MODELS_DIR / "clf-v1.0.0" / "rules.yaml"
_WS = re.compile(r"\s+")


def normalise(text: str) -> str:
    t = str(text).lower().replace("‘", "'").replace("’", "'")
    return _WS.sub(" ", t).strip()


def load_rules(path: Path = RULES_PATH) -> dict:
    """Load and validate rules.yaml. Phrases must already be in normalised form and unique."""
    doc = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    compiled, seen = [], set()
    for key, label in [("confusion_phrases", "confused"), ("understanding_phrases", "understood")]:
        phrases = doc[key]
        assert isinstance(phrases, list) and phrases, f"{key} must be a non-empty list"
        for p in phrases:
            assert isinstance(p, str) and p and p == normalise(p), f"phrase not in normalised form: {p!r}"
            assert p not in seen, f"duplicate phrase: {p!r}"
            seen.add(p)
            compiled.append((label, p, re.compile(r"\b" + re.escape(p) + r"\b")))
    return {"version": doc["version"], "confusion_phrases": doc["confusion_phrases"],
            "understanding_phrases": doc["understanding_phrases"], "_compiled": compiled}


def match(text: str, rules: dict) -> tuple[str | None, str | None]:
    """Return ('confused' | 'understood' | None, matched_phrase). None means: ask the model."""
    t = normalise(text)
    for label, phrase, rx in rules["_compiled"]:
        if rx.search(t):
            return label, phrase
    return None, None

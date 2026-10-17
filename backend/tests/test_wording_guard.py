"""Wording guard (lead ruling 2026-10-16, R3): `would_ship` checks FORM only, never truth, so a percentage
may not sit next to the word "usable" in the two READMEs unless the same line also says "in form"
("shippable in form"). The column name `usable (would ship)` is pinned elsewhere and has no percentage.
"""

import re
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
DOCS = [BACKEND / "README.md", BACKEND / "benchmarks" / "llm" / "README.md"]

PCT = r"\d+(?:\.\d+)?\s*%"
# a percentage after "usable" ("usable (would ship) 85%", "usable in **88%**") or before it ("88% usable")
NEAR_USABLE = re.compile(rf"\busable\b[^|\n]{{0,40}}?{PCT}|{PCT}[^|\n]{{0,20}}?\busable\b", re.IGNORECASE)


def violations(text: str) -> list[str]:
    return [
        line.strip() for line in text.splitlines()
        if NEAR_USABLE.search(line) and "in form" not in line.lower()
    ]


def test_no_percentage_next_to_usable_without_in_form():
    for doc in DOCS:
        assert violations(doc.read_text(encoding="utf-8")) == [], doc.name


def test_the_guard_catches_the_old_phrasings():
    """The guard can fail: each of these pre-R3 lines must be flagged."""
    old = [
        "**usable (would ship) 85% (41/48)**; **over the 18 s service timeout 0% (0/48)**, wall p95 14.6 s;",
        "| `LLM_MAX_TOKENS` | `110` | `num_predict`. Measured 88% usable at 110 against 81% at 80. |",
        "wall p95 of 11.0 s, but its replies were usable in **88%** of cases against a **90%** bar; theory,",
        "The quality columns in the new files (usable 88% in both, 79% and",
    ]
    for line in old:
        assert violations(line) != [], line


def test_the_guard_accepts_the_new_phrasings():
    for line in [
        "r3 @220: 100% (cycle 1) / 97.9% (cycle 2) shippable in form - MEETS criterion 2.",
        "the column `usable (would ship)` keeps its name; read it as shippable in form",
        "usable in form: 87.5%",
    ]:
        assert violations(line) == [], line

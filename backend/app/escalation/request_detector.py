"""Tier 2 request detection and cycle-intent detection. Pure: no I/O, no logging.

DESIGN RULE: bias toward MISSING a request, not toward detecting one (claim C6).
A detected request is delivered with trigger "request", and that delivery then does NOT
count toward the student's difficulty. A FALSE request therefore under-reports the
struggle and corrupts the weakness data; a missed request costs one student one
less-preferred explanation. So patterns use request framing ("give me an example"),
never a bare noun or adjective that turns up in ordinary answers ("example") or in
statements of understanding ("it's clearer now"), and never a confused question
("what is a constructor?"), which must go through the classifier like any other message.

Matching: normalise with the rule layer's `normalise` (imported, not reimplemented),
then each pattern as a whole-word sequence `\\b<pattern>\\b`.

Residual false triggers are documented in tests (`test_documented_wrong_*`), not hidden.
"""

from __future__ import annotations

import re
from typing import Literal

from app.classifier.rules import normalise
from app.schemas import Strategy

CycleIntent = Literal["accept", "decline", "unclear"]

# Priority order when several strategies match: example, simplified, analogy, theory
# (the prototype's order).
_REQUEST_PATTERNS: tuple[tuple[Strategy, tuple[str, ...]], ...] = (
    (
        "example",
        (
            "show me",
            "give me an example",
            "can i see an example",
            "can i have an example",
            "example please",
            "demonstrate",
        ),
    ),
    (
        "simplified",
        (
            "simplify",
            "make it simpler",
            "make it easier",
            "make it easy",
            "make it clearer",
            "in simpler terms",
            "explain it simpler",
        ),
    ),
    (
        "analogy",
        ("analogy", "real world example", "real life example", "compare it to", "like what"),
    ),
    ("theory", ("define", "explain the concept", "explain the theory")),
)

# A hedge anywhere in the message means "unclear", checked BEFORE accept and decline.
# "unclear" costs one re-ask and corrupts nothing; a false accept adds a delivery and a
# cycle to the episode log, and a false decline ends the episode. Not a general negation
# guard: one detector's ambiguous branch doing its job.
_HEDGE = ("not sure", "maybe", "i guess", "dunno")
_ACCEPT = ("yes", "sure", "okay", "ok", "again", "explain it another way")
_DECLINE = ("no", "move on", "skip", "later")


def _whole_word(phrase: str) -> re.Pattern:
    return re.compile(r"\b" + re.escape(phrase) + r"\b")


_COMPILED_REQUESTS = tuple(
    (strategy, tuple(_whole_word(p) for p in patterns)) for strategy, patterns in _REQUEST_PATTERNS
)
_COMPILED_HEDGE = tuple(_whole_word(p) for p in _HEDGE)
_COMPILED_ACCEPT = tuple(_whole_word(p) for p in _ACCEPT)
_COMPILED_DECLINE = tuple(_whole_word(p) for p in _DECLINE)


def detect_request(message: str) -> Strategy | None:
    """The strategy the student explicitly asked for, or None."""
    text = normalise(message)
    for strategy, patterns in _COMPILED_REQUESTS:
        if any(rx.search(text) for rx in patterns):
            return strategy
    return None


def detect_cycle_intent(message: str) -> CycleIntent:
    """Answer to "explain it another way?". Hedge first, then accept, then decline."""
    text = normalise(message)
    if any(rx.search(text) for rx in _COMPILED_HEDGE):
        return "unclear"
    if any(rx.search(text) for rx in _COMPILED_ACCEPT):
        return "accept"
    if any(rx.search(text) for rx in _COMPILED_DECLINE):
        return "decline"
    return "unclear"

"""Fixed student-facing copy for the non-explanation actions. A lead decision: used exactly as
written. Never show the student the word that labels them as struggling; `is_weak` belongs in the
episode log and the research panel for the lecturer, not in front of a novice mid-struggle.
"""

from __future__ import annotations

OFFER_NEW_CYCLE = "This one is tricky, and that's completely normal. Would you like me to explain it another way?"
END_UNRESOLVED = (
    "Let's pause here. I've noted this topic so we can come back to it — "
    "it may also help to go over it with your lecturer."
)
CLARIFY = "Would you like me to explain it another way?\n\n**Check:** Please answer yes or no."
_RESOLVED = "Nice work! The **{strategy}** explanation did the trick."

STRATEGY_DISPLAY = {
    "theory": "Theory",
    "example": "Example",
    "simplified": "Simplified",
    "analogy": "Analogy",
}


def resolved_text(strategy: str) -> str:
    """`strategy` is the winning (last delivered) strategy."""
    return _RESOLVED.format(strategy=STRATEGY_DISPLAY[strategy])

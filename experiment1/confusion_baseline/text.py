"""Text helpers shared by notebooks and scripts."""

import re
import string

_WS = re.compile(r"\s+")


def normalize_key(text: str) -> str:
    """Lowercase, collapse whitespace, strip, strip trailing punctuation.

    Used to compare Question / Answer strings for grouping and duplicate checks.
    """
    t = _WS.sub(" ", str(text).lower()).strip()
    return t.rstrip(string.punctuation + " ")

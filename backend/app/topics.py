"""The authoritative Java topic list (owned by the tutor service; see GET /topics).

Pure data and two functions: no FastAPI import, no I/O.
"""

from __future__ import annotations

import re

# Slugs sent in TutorRequest.topic.
SLUG_PATTERN = re.compile(r"[a-z][a-z0-9_]*")

# Reserved slug: accepted by request validation, never listed by GET /topics, so a
# student who types without choosing a topic does not get a 422.
GENERAL = "general"

# (id, label) in the order GET /topics returns them.
_TOPICS: tuple[tuple[str, str], ...] = (
    ("variables_and_data_types", "Variables & Data Types"),
    ("conditional_statements", "Conditional Statements"),
    ("loops", "Loops"),
    ("arrays", "Arrays"),
    ("methods_and_functions", "Methods & Functions"),
    ("classes_and_objects", "Classes & Objects"),
    ("inheritance", "Inheritance"),
    ("polymorphism", "Polymorphism"),
    ("encapsulation", "Encapsulation"),
    ("abstraction", "Abstraction"),
    ("exception_handling", "Exception Handling"),
    ("collections", "Collections"),
    ("recursion", "Recursion"),
    ("file_io", "File I/O"),
)

_ACCEPTED = frozenset(slug for slug, _ in _TOPICS) | {GENERAL}


def public_topics() -> list[dict[str, str]]:
    """The 14 topics for GET /topics, in order, without `general`. A fresh list each call."""
    return [{"id": slug, "label": label} for slug, label in _TOPICS]


def is_accepted_topic(slug: str) -> bool:
    """True for a well-formed slug that is one of the 14 topics or `general`."""
    return SLUG_PATTERN.fullmatch(slug) is not None and slug in _ACCEPTED

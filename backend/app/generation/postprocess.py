"""Enforce the output format on any LLM output. Small models drop instructions, so the format is
enforced AFTER generation, not merely requested.

The format: Markdown, Java only in fenced blocks, and exactly one `**Check:**` line which is the
final non-empty line (the frontend splits the check question out on that marker).

Known limits (not handled, by design): a plain "Check:" without the bold markers is not recognised
(a second, bold check line is appended); a lone `</think>` with no opener cannot tell us what was
reasoning, so only the stray tag is removed, not the text before it.
"""

from __future__ import annotations

import re

CHECK = "**Check:**"

DEFAULT_CHECKS = {
    "theory": "In your own words, what is the main idea here?",
    "example": "What do you think would happen if you changed one line of this example?",
    "simplified": "Which step of that explanation would you like me to go over again?",
    "analogy": "How would you map this comparison back to the Java code?",
}

_THINK_CLOSED = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_THINK_UNCLOSED = re.compile(r"<think>.*\Z", re.DOTALL | re.IGNORECASE)
_THINK_STRAY = re.compile(r"</?think>", re.IGNORECASE)
_FENCE_LINE = re.compile(r"^\s*```")


def strip_think(text: str) -> str:
    """Remove every <think>...</think> span (multi-line too), an unclosed trailing <think>... to the
    end of the text, and any stray tag. Model-agnostic: Qwen3 reasons inside these tags and the
    voice phase would otherwise speak that monologue aloud."""
    text = _THINK_CLOSED.sub("", text)
    text = _THINK_UNCLOSED.sub("", text)
    return _THINK_STRAY.sub("", text)


def _fence_is_open(lines: list[str]) -> bool:
    return sum(1 for line in lines if _FENCE_LINE.match(line)) % 2 == 1


def ensure_check(text: str, strategy: str) -> str:
    """Return text with exactly one `**Check:**` line, and it is the final non-empty line.

    - none (or an empty one): append a default question for the strategy;
    - several: keep only the LAST, remove the marker from the others (their text stays as prose);
    - one, but followed by more text: move it to the end;
    - a marker in the middle of a line is put on its own line first;
    - an unclosed code fence is closed first, so the check line cannot end up inside the code block.
    """
    if strategy not in DEFAULT_CHECKS:
        raise ValueError(f"unknown strategy: {strategy!r}")
    text = re.sub(r"(?<=\S)[ \t]*(\*\*Check:\*\*)", r"\n\1", text)  # marker mid-line -> its own line
    lines = text.strip().splitlines()

    check_idx = [i for i, line in enumerate(lines) if line.strip().startswith(CHECK)]
    question = ""
    if check_idx:
        last = check_idx[-1]
        question = lines[last].strip()[len(CHECK):].strip()
        for i in check_idx[:-1]:  # earlier markers become plain prose
            lines[i] = lines[i].replace(CHECK, "", 1).strip()
        del lines[last]
    if not question:
        question = DEFAULT_CHECKS[strategy]

    if _fence_is_open(lines):
        lines.append("```")
    body = "\n".join(lines).strip()
    return f"{body}\n\n{CHECK} {question}" if body else f"{CHECK} {question}"


def finalise(text: str, strategy: str) -> str:
    return ensure_check(strip_think(text), strategy).strip()

"""Enforce the output format on any LLM output. Small models drop instructions, so the format is
enforced AFTER generation, not merely requested.

The format: Markdown, Java only in fenced blocks, and exactly one `**Check:**` line which is the
final non-empty line (the frontend splits the check question out on that marker).

The prompt ASKS (no headings, at most 60 words, a final Check line); this module GUARANTEES. Small
models ignore instructions (llama3.2:3b opens with a heading and is cut off mid-sentence), and a
broken reply must never reach the student: `would_ship` (usable AND no untagged reasoning) says
whether a reply would ship, and the caller serves the template instead when it would not.

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


# --- headings, truncation, usability (S7b) ---------------------------------------------------------

_FENCE = re.compile(r"^[ \t]*```")
_ATX = re.compile(r"^ {0,3}#{1,6}(?:[ \t]+.*)?$")
_SETEXT_UNDERLINE = re.compile(r"^ {0,3}(?:={3,}|-{3,})[ \t]*$")
_BOLD_ONLY = re.compile(r"^\s*(?:\*\*[^*\n]+\*\*|__[^_\n]+__):?\s*$")
_SENTENCE_END = re.compile(r"""[.!?]["')\]*_`]*(?=\s|$)""")
_JAVA_BLOCK = re.compile(r"^[ \t]*```java[^\n]*\n.*?^[ \t]*```[ \t]*$", re.DOTALL | re.MULTILINE)
_CLOSED_FENCED = re.compile(r"^[ \t]*```[^\n]*\n.*?^[ \t]*```[ \t]*$", re.DOTALL | re.MULTILINE)


def _looks_like_a_title(line: str) -> bool:
    """A setext title line is short and does not end like a sentence, so a real sentence that happens
    to sit above a `---` rule is never deleted."""
    s = line.strip()
    return bool(s) and len(s) <= 100 and not re.search(r"[.!?]\s*$", s)


def strip_headings(text: str) -> str:
    """Remove ATX heading lines (`# ...`), setext underlines (`===`, `---`) TOGETHER with the title
    line above them, and a leading line that is only bold text. Code blocks are left untouched."""
    lines = text.replace("\r\n", "\n").split("\n")
    kept: list[tuple[str, bool]] = []  # (line, is_code)
    in_fence = False
    prev_kept_index = -2  # index in `lines` of the line most recently kept
    for i, line in enumerate(lines):
        if _FENCE.match(line):
            in_fence = not in_fence
            kept.append((line, True))
            prev_kept_index = i
            continue
        if in_fence:
            kept.append((line, True))
            prev_kept_index = i
            continue
        if _ATX.match(line):
            continue
        if (
            _SETEXT_UNDERLINE.match(line)
            and kept
            and not kept[-1][1]
            and prev_kept_index == i - 1
            and _looks_like_a_title(kept[-1][0])
        ):
            kept.pop()  # the title line above the underline goes too
            continue
        if not line.strip() and kept and not kept[-1][1] and not kept[-1][0].strip():
            continue  # a removed heading must not leave a double blank line behind (prose only, never code)
        kept.append((line, False))
        prev_kept_index = i
    for idx, (line, is_code) in enumerate(kept):  # a leading bold-only line is a title
        if line.strip():
            if not is_code and _BOLD_ONLY.match(line):
                kept.pop(idx)
            break
    return "\n".join(line for line, _ in kept).lstrip("\n")


def has_heading(text: str) -> bool:
    return strip_headings(text).strip() != text.replace("\r\n", "\n").strip()


def drop_unclosed_code(text: str) -> str:
    """A half code block is broken Java on screen: drop an UNCLOSED trailing block entirely."""
    lines = text.split("\n")
    fences = [i for i, ln in enumerate(lines) if _FENCE.match(ln)]
    if len(fences) % 2 == 1:
        return "\n".join(lines[: fences[-1]]).rstrip()
    return text


def trim_to_last_sentence(text: str) -> str:
    """For a reply cut off at the token cap: cut the prose after the last closed code block back to
    its last complete sentence (`.`, `!` or `?` followed by whitespace or the end). Code is never cut."""
    last_close_end = 0
    for m in _CLOSED_FENCED.finditer(text):
        last_close_end = m.end()
    prefix, trailing = text[:last_close_end], text[last_close_end:]
    if not trailing.strip():
        return text.rstrip()
    ends = list(_SENTENCE_END.finditer(trailing))
    trailing = trailing[: ends[-1].end()] if ends else ""
    return (prefix + trailing).rstrip()


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


def finalise(text: str, strategy: str, truncated: bool = False) -> str:
    """strip_think, strip_headings, (if the model stopped at the token cap: drop an unclosed code
    block and trim back to the last complete sentence), then ensure_check. A reply that was not
    truncated is never trimmed."""
    text = strip_headings(strip_think(text))
    if truncated:
        text = trim_to_last_sentence(drop_unclosed_code(text))
    return ensure_check(text, strategy).strip()


def usable(text: str, strategy: str, truncated: bool = False) -> bool:
    """Would this reply ship? After post-processing it needs at least one complete prose sentence
    outside code and outside the Check line, and an `example` needs a closed ```java block. When this
    is False the service serves the template (meta.fallback: true) instead."""
    final = finalise(text, strategy, truncated)
    prose = _CLOSED_FENCED.sub("", final)
    prose = "\n".join(ln for ln in prose.splitlines() if not ln.strip().startswith(CHECK))
    prose = re.sub(r"`[^`\n]*`", "X", prose)
    if not _SENTENCE_END.search(prose):
        return False
    if strategy == "example" and not _JAVA_BLOCK.search(final):
        return False
    return True


# --- untagged reasoning, and the one definition of "would it ship?" (S8) ---------------------------

# THE UNTAGGED REASONING LEAK is a deliberately simple HEURISTIC, reported as one: a line of the
# output starts with a phrase that small "thinking" models use when they narrate their plan instead
# of answering ("We are explaining...", "Let me write in 2-4 sentences:"). Known limits:
#  - false negatives: reasoning that does not start a line with one of these phrases;
#  - false positives: a legitimate reply that happens to start a line with one ("We are going to
#    look at an example."), which then falls back to the template: safe, just less helpful.
# One place. Matched case-insensitively at the START of a line (after leading whitespace), as a
# whole phrase. Add phrases here, nowhere else.
LEAK_PHRASES = ("We are", "We need to", "Let me", "Okay, so", "First, I", "The user")

_LEAK_RE = re.compile(
    r"^[ \t]*(?:" + "|".join(re.escape(p) for p in LEAK_PHRASES) + r")\b", re.IGNORECASE | re.MULTILINE
)


def reasoning_leak(text: str) -> bool:
    """HEURISTIC (see LEAK_PHRASES)."""
    return _LEAK_RE.search(text) is not None


def would_ship(raw: str, strategy: str, truncated: bool) -> bool:
    """The decisive question, used by BOTH the service and the benchmark: would this reply be served
    to a student? It must be `usable` after the deterministic post-processing AND must not be an
    untagged reasoning leak (lead ruling: a leak disqualifies, and `usable` alone is a format check
    that a leaked sentence would pass)."""
    return usable(raw, strategy, truncated) and not reasoning_leak(finalise(raw, strategy, truncated))

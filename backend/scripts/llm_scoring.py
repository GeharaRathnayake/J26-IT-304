"""Pure scoring and aggregation for the LLM benchmark (decision D2). No I/O, no network, no
side effects on import, so it is unit-tested without Ollama.

These are mechanical checks on the output FORMAT. Whether an explanation is good is a human
judgement (the rating sheet), not something this module claims to measure. The tutor itself is a
prototype; the classifier behind it is a proxy trained on synthetic answers.

THE UNTAGGED REASONING LEAK is a deliberately simple HEURISTIC, reported as one: a line of the
output starts with a phrase that small "thinking" models use when they narrate their plan instead
of answering ("We are explaining...", "Let me write in 2-4 sentences:"). Known limits:
 - false negatives: reasoning that does not start a line with one of these phrases;
 - false positives: a legitimate reply that happens to start a line with one ("We are going to
   look at an example.").
That is why the human rating exists. The phrase list lives in LEAK_PHRASES, in one place.
"""

from __future__ import annotations

import math
import re
import statistics
from typing import Any

CHECK = "**Check:**"

# The service's fallback timeout (seconds). A REFERENCE for the "% over 12 s" column, not a pass mark;
# nothing in the benchmark is ever stopped at it.
SERVICE_TIMEOUT_S = 12.0

# One place. Matched case-insensitively at the START of a line (after leading whitespace), as a
# whole phrase. Add phrases here, nowhere else.
LEAK_PHRASES = ("We are", "We need to", "Let me", "Okay, so", "First, I", "The user")

_LEAK_RE = re.compile(
    r"^[ \t]*(?:" + "|".join(re.escape(p) for p in LEAK_PHRASES) + r")\b", re.IGNORECASE | re.MULTILINE
)
_THINK_RE = re.compile(r"</?think>", re.IGNORECASE)
_FENCED_CLOSED = re.compile(r"^[ \t]*```[^\n]*\n.*?^[ \t]*```[ \t]*$", re.DOTALL | re.MULTILINE)
_JAVA_BLOCK = re.compile(r"^[ \t]*```java[^\n]*\n.*?^[ \t]*```[ \t]*$", re.DOTALL | re.MULTILINE)
_FENCE_LINE = re.compile(r"^[ \t]*```", re.MULTILINE)
_CODE_LINE = re.compile(
    r"^\s*(?:(?:public|private|protected|static|final|class|interface|import|package)\b"
    r"|(?:int|long|double|float|boolean|char|String|var|void)\s+\w+\s*(?:=|\(|;)"
    r"|(?:for|while|if|switch|try|catch)\s*[\({]"
    r"|return\b.*;|System\.out\.|[\w.\[\]<>]+\s*=\s*[^=].*;)"
    r"|.*[;{}]\s*$"
)


def _strip_fences(text: str) -> str:
    """Remove closed fenced blocks, and an UNCLOSED trailing fence to the end (cut-off output)."""
    text = _FENCED_CLOSED.sub("", text)
    fences = list(_FENCE_LINE.finditer(text))
    if len(fences) % 2 == 1:
        text = text[: fences[-1].start()]
    return text


# --- per-output checks -------------------------------------------------------------------------


def check_ok(text: str) -> bool:
    """Exactly one `**Check:**` marker, and it starts the last non-empty line."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    return bool(lines) and text.count(CHECK) == 1 and lines[-1].lstrip().startswith(CHECK)


def sentence_count(text: str) -> int:
    """Sentences outside code blocks and the Check line. Inline code is blanked first (so a full
    stop inside `code` does not count); a line ending in ':' is a lead-in and counts as one."""
    body = _strip_fences(text)
    body = "\n".join(ln for ln in body.splitlines() if not ln.strip().startswith(CHECK))
    body = re.sub(r"`[^`\n]*`", "X", body)
    return len(re.findall(r"[.!?](?=\s|$)|:[ \t]*$", body, re.MULTILINE))


def sentences_ok(text: str) -> bool:
    return 2 <= sentence_count(text) <= 4


def has_java_block(text: str) -> bool:
    return _JAVA_BLOCK.search(text) is not None


def unfenced_code_lines(text: str) -> list[str]:
    """Lines outside fenced blocks that look like code (heuristic). Inline `code` is fine."""
    outside = _strip_fences(text)
    found = []
    for line in outside.splitlines():
        if not line.strip() or line.strip().startswith(CHECK):
            continue
        without_inline = re.sub(r"`[^`\n]*`", "", line)
        # prose that ends a sentence with ':' or '.' is not code; code ends in ; { } or is an assignment
        if _CODE_LINE.match(without_inline) and not re.search(r"[.!?:]\s*$", without_inline):
            found.append(line)
    return found


def java_ok(text: str, strategy: str) -> bool:
    """example: has a closed ```java block. Other strategies: no unfenced code."""
    if strategy == "example":
        return has_java_block(text)
    return not unfenced_code_lines(text)


def has_think_tag(text: str) -> bool:
    return _THINK_RE.search(text) is not None


def reasoning_leak(text: str) -> bool:
    """HEURISTIC (see the module docstring)."""
    return _LEAK_RE.search(text) is not None


def truncated(done_reason: str | None) -> bool:
    return done_reason == "length"


# --- scoring one generation -------------------------------------------------------------------------


def score_raw(raw: str, strategy: str, done_reason: str | None) -> dict[str, Any]:
    return {
        "empty": not raw.strip(),
        "check_ok": check_ok(raw),
        "sentence_count": sentence_count(raw),
        "sentences_ok": sentences_ok(raw),
        "java_ok": java_ok(raw, strategy),
        "think_tag": has_think_tag(raw),
        "reasoning_leak": reasoning_leak(raw),
        "truncated": truncated(done_reason),
    }


def score_final(final: str) -> dict[str, Any]:
    """After `finalise`: Check, sentences, think tags (must be zero) and the leak heuristic."""
    return {
        "check_ok": check_ok(final),
        "sentence_count": sentence_count(final),
        "sentences_ok": sentences_ok(final),
        "think_tag": has_think_tag(final),
        "reasoning_leak": reasoning_leak(final),
    }


def score_generation(raw: str, final: str, strategy: str, done_reason: str | None) -> dict[str, Any]:
    return {"score_raw": score_raw(raw, strategy, done_reason), "score_final": score_final(final)}


# --- aggregation --------------------------------------------------------------------------------------------


def percentile(values: list[float], pct: float) -> float | None:
    """Nearest-rank percentile (no interpolation): honest for small samples."""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(pct / 100.0 * len(ordered)))
    return ordered[rank - 1]


def _pct(flags: list[bool]) -> float | None:
    return None if not flags else 100.0 * sum(1 for f in flags if f) / len(flags)


def _median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def aggregate(generations: list[dict], cold_start_s: float | None) -> dict[str, Any]:
    """Summary numbers over successful generations (an errored generation has no measurements and is
    counted separately)."""
    ok = [g for g in generations if not g.get("error")]
    walls = [g["wall_s"] for g in ok if g.get("wall_s") is not None]
    ttfts = [g["ttft_s"] for g in ok if g.get("ttft_s") is not None]
    toks = [g["tok_s"] for g in ok if g.get("tok_s") is not None]
    examples = [g for g in ok if g["strategy"] == "example"]
    others = [g for g in ok if g["strategy"] != "example"]

    # per-prompt spread across the runs (max - min wall time)
    by_prompt: dict[tuple[str, str], list[float]] = {}
    for g in ok:
        if g.get("wall_s") is not None:
            by_prompt.setdefault((g["topic"], g["strategy"]), []).append(g["wall_s"])
    spreads = [max(v) - min(v) for v in by_prompt.values() if len(v) > 1]

    return {
        "generations": len(generations),
        "errors": len(generations) - len(ok),
        "cold_start_s": cold_start_s,
        "wall_median_s": _median(walls),
        "wall_p95_s": percentile(walls, 95),
        "pct_over_service_timeout": _pct([g["wall_s"] > SERVICE_TIMEOUT_S for g in generations if g.get("wall_s") is not None]),
        "wall_spread_median_s": _median(spreads),
        "ttft_median_s": _median(ttfts),
        "tok_s_median": _median(toks),
        "pct_truncated": _pct([g["score_raw"]["truncated"] for g in ok]),
        "pct_empty_raw": _pct([g["score_raw"]["empty"] for g in ok]),
        "pct_check_raw": _pct([g["score_raw"]["check_ok"] for g in ok]),
        "pct_check_final": _pct([g["score_final"]["check_ok"] for g in ok]),
        "pct_sentences_raw": _pct([g["score_raw"]["sentences_ok"] for g in ok]),
        "pct_sentences_final": _pct([g["score_final"]["sentences_ok"] for g in ok]),
        "pct_java_example": _pct([g["score_raw"]["java_ok"] for g in examples]),
        "pct_no_unfenced_code_other": _pct([g["score_raw"]["java_ok"] for g in others]),
        "pct_think_raw": _pct([g["score_raw"]["think_tag"] for g in ok]),
        "pct_think_final": _pct([g["score_final"]["think_tag"] for g in ok]),
        "pct_leak_raw": _pct([g["score_raw"]["reasoning_leak"] for g in ok]),
        "pct_leak_final": _pct([g["score_final"]["reasoning_leak"] for g in ok]),
    }


# --- SUMMARY.md ------------------------------------------------------------------------------------------------------


def _f(value: float | None, digits: int = 1, unit: str = "") -> str:
    return "n/a" if value is None else f"{value:.{digits}f}{unit}"


def summary_markdown(results: list[dict]) -> str:
    """One row per result file, regenerated from the result JSONs (each carries its aggregates,
    recomputed here from the raw generations so a stale number can never survive)."""
    header = (
        "| model (run date) | cold start | wall median | wall p95 | over 12 s | wall spread | TTFT median | tok/s median "
        "| truncated | empty | Check ok raw / final | 2-4 sentences raw / final | java fenced (example) "
        "| no unfenced code (others) | `<think>` raw / final | untagged leak raw / final | human rating (mean) |"
    )
    sep = "|" + "---|" * 17
    rows = []
    for r in sorted(results, key=lambda r: (r["model"], r["date"])):
        a = aggregate(r["generations"], (r.get("cold_start") or {}).get("wall_s"))
        rows.append(
            f"| {r['model']} ({r['date']}) | {_f(a['cold_start_s'], 1, ' s')} | {_f(a['wall_median_s'], 1, ' s')} "
            f"| {_f(a['wall_p95_s'], 1, ' s')} | {_f(a['pct_over_service_timeout'], 0, '%')} | {_f(a['wall_spread_median_s'], 1, ' s')} "
            f"| {_f(a['ttft_median_s'], 2, ' s')} | {_f(a['tok_s_median'], 1)} "
            f"| {_f(a['pct_truncated'], 0, '%')} | {_f(a['pct_empty_raw'], 0, '%')} "
            f"| {_f(a['pct_check_raw'], 0, '%')} / {_f(a['pct_check_final'], 0, '%')} "
            f"| {_f(a['pct_sentences_raw'], 0, '%')} / {_f(a['pct_sentences_final'], 0, '%')} "
            f"| {_f(a['pct_java_example'], 0, '%')} | {_f(a['pct_no_unfenced_code_other'], 0, '%')} "
            f"| {_f(a['pct_think_raw'], 0, '%')} / {_f(a['pct_think_final'], 0, '%')} "
            f"| {_f(a['pct_leak_raw'], 0, '%')} / {_f(a['pct_leak_final'], 0, '%')} | |"
        )
    notes = (
        "\n\nHow to read this table:\n\n"
        "- Every number is over the successful generations of that run (16 prompts x runs). Timings are wall "
        "clock on the benchmark machine, with whatever else it was running.\n"
        "- **over 12 s** is the share of generations the service would have replaced with a template (its "
        "fallback timeout). It is a reference, not a pass mark, and no generation is stopped at 12 s.\n"
        "- **Untagged preamble disqualifies a model** (lead ruling): a reasoning leak is a reliability "
        "criterion, not something to patch at runtime. Read the leak and truncated columns first.\n"
        "- **The format scores are mechanical.** They say nothing about whether an explanation is correct or "
        "good; that is the human rating, filled in from the `*_outputs.md` sheets.\n"
        "- **Untagged leak is a heuristic** (a line starting with a phrase such as `We are`, `Let me`, "
        "`The user`); it has false positives and false negatives.\n"
        "- `finalise` always appends a Check line when one is missing, so \"Check ok final\" is near 100% by "
        "construction; read it together with `empty` and the raw columns. A reply that was entirely reasoning "
        "becomes a bare default question.\n"
        "- Call parameters are fixed and recorded in each result JSON: `/api/chat`, one user message, "
        "`think: false`, `stream: true`, `num_predict: 80`, 60 s client timeout. The service's adapter must "
        "use the same.\n"
    )
    return "# LLM benchmark summary\n\n" + header + "\n" + sep + "\n" + "\n".join(rows) + notes

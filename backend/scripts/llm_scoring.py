"""Pure scoring and aggregation for the LLM benchmark (decision D2). No I/O, no network, no
side effects on import, so it is unit-tested without Ollama.

These are mechanical checks on the output FORMAT. Whether an explanation is good is a human
judgement (the rating sheet), not something this module claims to measure. The tutor itself is a
prototype; the classifier behind it is a proxy trained on synthetic answers.

THE UNTAGGED REASONING LEAK is a deliberately simple HEURISTIC, reported as one (known limits in
app/generation/postprocess.py). That is why the human rating exists.

`reasoning_leak`, `LEAK_PHRASES` and `would_ship` are IMPORTED from the service (S8), never copied:
the benchmark and the service must judge "would it ship?" by the same function.
"""

from __future__ import annotations

import math
import re
import statistics
import sys
from pathlib import Path
from typing import Any

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))
from app.generation.postprocess import (  # noqa: E402  (pure functions; one definition, shared with the service)
    LEAK_PHRASES,
    finalise,
    has_heading,
    reasoning_leak,
    would_ship,
)

CHECK = "**Check:**"

# The service's fallback timeout (seconds). A REFERENCE for the "% over 12 s" column, not a pass mark;
# nothing in the benchmark is ever stopped at it.
SERVICE_TIMEOUT_S = 12.0

__all__ = ["LEAK_PHRASES", "reasoning_leak", "would_ship"]  # re-exported for the benchmark script

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
        "heading": has_heading(raw),
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
    """`final` is the SHIPPED text: finalise(raw, strategy, truncated=done_reason == "length")."""
    shipped = score_final(final)
    shipped["usable"] = would_ship(raw, strategy, truncated(done_reason))
    shipped["java_complete"] = has_java_block(final)
    return {"score_raw": score_raw(raw, strategy, done_reason), "score_final": shipped}


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


def _usable_of(g: dict) -> bool | None:
    """Stored value, else recomputed from the raw text (result files from before S7b lack it)."""
    if "usable" in g["score_final"]:
        return g["score_final"]["usable"]
    if g.get("raw_text") is None:
        return None
    return would_ship(g["raw_text"], g["strategy"], truncated(g.get("done_reason")))


def _java_complete_of(g: dict) -> bool | None:
    if "java_complete" in g["score_final"]:
        return g["score_final"]["java_complete"]
    if g.get("raw_text") is None:
        return None
    return has_java_block(finalise(g["raw_text"], g["strategy"], truncated(g.get("done_reason"))))


def _heading_of(g: dict) -> bool | None:
    if "heading" in g["score_raw"]:
        return g["score_raw"]["heading"]
    return None if g.get("raw_text") is None else has_heading(g["raw_text"])


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
        "pct_usable": _pct([x for x in (_usable_of(g) for g in ok) if x is not None]),
        "pct_example_java_complete": _pct([x for x in (_java_complete_of(g) for g in examples) if x is not None]),
        "pct_headings_raw": _pct([x for x in (_heading_of(g) for g in ok) if x is not None]),
    }


# --- SUMMARY.md ------------------------------------------------------------------------------------------------------


def _f(value: float | None, digits: int = 1, unit: str = "") -> str:
    return "n/a" if value is None else f"{value:.{digits}f}{unit}"


def _num_predict(result: dict) -> int:
    """The token cap of a run (older result files carry it only inside call_parameters)."""
    if "num_predict" in result:
        return result["num_predict"]
    return result.get("call_parameters", {}).get("options", {}).get("num_predict", 0)


def _revision(result: dict) -> str:
    """The prompt revision of a run. Result files from before S7b predate the field: that was r1."""
    return result.get("prompt_revision", "r1")


def _cycle(result: dict) -> int:
    """The explanation cycle a run's prompts were built for. Result files from before S8b predate
    the field: that was cycle 1."""
    return result.get("cycle", 1)


def _cycle_suffix(result: dict) -> str:
    """' c2same' / ' c2all' from cycle 2, else '' (S8b). Cycle-1 labels are unchanged on purpose:
    the committed cycle-1 rows are evidence."""
    cycle = _cycle(result)
    if cycle < 2:
        return ""
    return f" c{cycle}{result.get('priors') or 'same'}"


def median_prompt_chars(prompt_set: list) -> float | None:
    """Median character length of a run's prompts (S8b): measures the cycle-2 prompt-size change
    instead of asserting it. The PRIOR BLOCK shrinks fourfold between `c2all` and `c2same` (one
    cycle-1 template instead of four), but the whole prompt only about 1.9x, since the fixed
    instructions, topic and student message cost the same either way."""
    lengths = [len(item["prompt"]) for item in (prompt_set or []) if isinstance(item, dict) and "prompt" in item]
    return _median(lengths)


def summary_markdown(results: list[dict]) -> str:
    """One row per result file, regenerated from the result JSONs (each carries its aggregates,
    recomputed here from the raw generations so a stale number can never survive)."""
    header = (
        "| model @num_predict prompt-revision (run date) | cold start | wall median | wall p95 | over 12 s | wall spread "
        "| TTFT median | tok/s median | truncated | empty | **usable (would ship)** | example complete java "
        "| headings (raw) | Check ok raw / final | 2-4 sentences raw / final | java fenced (example) "
        "| no unfenced code (others) | `<think>` raw / final | untagged leak raw / final | human rating (mean) "
        "| prompt length (median chars) |"
    )
    sep = "|" + "---|" * 21
    rows = []
    for r in sorted(results, key=lambda r: (r["model"], _num_predict(r), _revision(r), _cycle(r), r.get("priors") or "", r["date"])):
        a = aggregate(r["generations"], (r.get("cold_start") or {}).get("wall_s"))
        label = f"{r['model']} @{_num_predict(r)} {_revision(r)}{_cycle_suffix(r)} ({r['date']})"
        rows.append(
            f"| {label} | {_f(a['cold_start_s'], 1, ' s')} | {_f(a['wall_median_s'], 1, ' s')} "
            f"| {_f(a['wall_p95_s'], 1, ' s')} | {_f(a['pct_over_service_timeout'], 0, '%')} | {_f(a['wall_spread_median_s'], 1, ' s')} "
            f"| {_f(a['ttft_median_s'], 2, ' s')} | {_f(a['tok_s_median'], 1)} "
            f"| {_f(a['pct_truncated'], 0, '%')} | {_f(a['pct_empty_raw'], 0, '%')} "
            f"| **{_f(a['pct_usable'], 0, '%')}** | {_f(a['pct_example_java_complete'], 0, '%')} "
            f"| {_f(a['pct_headings_raw'], 0, '%')} "
            f"| {_f(a['pct_check_raw'], 0, '%')} / {_f(a['pct_check_final'], 0, '%')} "
            f"| {_f(a['pct_sentences_raw'], 0, '%')} / {_f(a['pct_sentences_final'], 0, '%')} "
            f"| {_f(a['pct_java_example'], 0, '%')} | {_f(a['pct_no_unfenced_code_other'], 0, '%')} "
            f"| {_f(a['pct_think_raw'], 0, '%')} / {_f(a['pct_think_final'], 0, '%')} "
            f"| {_f(a['pct_leak_raw'], 0, '%')} / {_f(a['pct_leak_final'], 0, '%')} | "
            f"| {_f(median_prompt_chars(r.get('prompt_set')), 0)} |"
        )
    notes = (
        "\n\nHow to read this table:\n\n"
        "- Every number is over the successful generations of that run (16 prompts x runs). Timings are wall "
        "clock on the benchmark machine, with whatever else it was running.\n"
        "- **over 12 s** is a FIXED REFERENCE carried from S7, not the service's timeout: `LLM_TIMEOUT_S` "
        "(`app/config.py`) was 14 s in S8 and is 18 s since S8b. It is a reference point, not a pass mark, "
        "and no generation is stopped at 12 s; read `LLM_TIMEOUT_S` for what the service actually falls back at.\n"
        "- **usable (would ship)** is the decisive column for the template fallback, and it checks FORM only, "
        "never truth: read it as \"shippable in form\", not accuracy or quality. The reply, after the "
        "deterministic post-processing (headings stripped; if the model stopped at the token cap, an unclosed "
        "code block dropped and the prose trimmed to the last complete sentence), has at least one complete prose "
        "sentence, an `example` has a closed java block, and it is not an untagged reasoning leak. A reply that "
        "does not ship is replaced by the template (`meta.fallback: true`), never served. Content accuracy is "
        "measured only by the blind rating (D2 criterion 5).\n"
        "- **r1 / r2 / r3** is the prompt revision (r1 = the original prompt, r2 = the S7b revision, r3 = the "
        "2026-10-17 length revision); **@N** is `num_predict`. For r1 rows the shippable-in-form / headings / "
        "example columns are recomputed from the stored raw "
        "text with today's post-processing, so they show what post-processing alone would have achieved.\n"
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
        "`think: false`, `stream: true`, `num_predict` as in the row label, 60 s client timeout. The service's adapter must "
        "use the same.\n"
        "- **c2same / c2all** (S8b) marks a cycle-2 row: `same` carries only the earlier explanation(s) of the "
        "same strategy (what the service now sends); `all` carries all four cycle-1 templates (what S8 sent, "
        "kept as the before case). No suffix means cycle 1; those rows and files are unchanged.\n"
        "- **prompt length (median chars)** is the median character length of that run's 16 prompts. "
        "Comparing `c2same` against `c2all`: the prior block itself shrinks fourfold (one cycle-1 template "
        "instead of four), but the whole prompt only about 1.9x (1352 vs 2562 median characters), since the "
        "fixed instructions, topic and student message are the same size either way.\n"
    )
    return "# LLM benchmark summary\n\n" + header + "\n" + sep + "\n" + "\n".join(rows) + notes

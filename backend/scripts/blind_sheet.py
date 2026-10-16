"""Blind rating sheet for D2 criterion 5: "blind quality rating >= 3/5, and not below templates",
rated by a human. This script builds a sheet of 24 items (12 LLM generations, 12 matching
templates), shuffled and unlabelled so a human rater cannot tell which side an item came from, and
scores a completed sheet against the key.

This script NEVER rates anything. The rating is filled in by hand by a human (Yasindu or the lead);
`score_sheet` only turns a completed sheet into numbers. The verdict (`criterion_5`) is evidence for
the lead to read, not a gate this script enforces.

llama3.2:3b did NOT pass D2 overall (it missed the 90% usability bar at 88% and ships with a
template fallback); this sheet is one more piece of evidence, read by a human, not a decision.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPTS_DIR.parent
for _p in (str(SCRIPTS_DIR), str(BACKEND_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from app.generation.adapters import TemplateFallback  # noqa: E402
from app.generation.postprocess import finalise  # noqa: E402

# Pre-registered. Do not pick another seed after seeing an ordering.
SEED = 20261015
SHEET_DATE = "2026-10-15"  # fixed: part of the committed filenames, not a generation timestamp
SOURCE_FILE = "llama3.2_3b_2026-10-15_np110_r2.json"
TOPICS = ("inheritance", "loops", "exception_handling")
STRATEGIES = ("theory", "example", "simplified", "analogy")
DEFAULT_RESULTS_DIR = Path("benchmarks/llm")

SHEET_NAME = f"blind_rating_{SHEET_DATE}.md"
KEY_NAME = f"blind_key_{SHEET_DATE}.json"

RATING_PROMPT = (
    "How well does this reply explain the topic to a beginner, using the named strategy? "
    "1 = poor, 5 = excellent."
)
RATING_LABEL = "Rating (1-5): "

# Nothing in the sheet may reveal which side an item came from (case-insensitive).
_FORBIDDEN_WORDS = ("llm", "template", "fallback", "ollama", "llama", "model")
_FORBIDDEN_RE = re.compile("|".join(re.escape(w) for w in _FORBIDDEN_WORDS), re.IGNORECASE)

_TRAILING_WS_RE = re.compile(r"[ \t]+$", re.MULTILINE)
_MULTI_BLANK_RE = re.compile(r"\n{3,}")
_BEFORE_CHECK_RE = re.compile(r"\n*(\*\*Check:\*\*)")
_ITEM_HEADING_RE = re.compile(r"(?m)^## (R\d{2}):")
_RATING_LINE_RE = re.compile(r"(?m)^Rating \(1-5\):[ \t]?(.*)$")


# --- selection -----------------------------------------------------------------------------------


def select_llm_items(result: dict) -> dict[tuple[str, str], str]:
    """The 12 run-1, three-topic generations: (topic, strategy) -> final_text. Recomputes
    `finalise` from `raw_text` and raises ValueError (never silently) if it disagrees with the
    stored `final_text`. The reply that fails `would_ship` is included as-is: the rating judges
    what the model produced, not what the fallback hides."""
    picked: dict[tuple[str, str], str] = {}
    for g in result.get("generations", []):
        if g.get("run") != 1 or g.get("topic") not in TOPICS:
            continue
        key = (g["topic"], g["strategy"])
        if key in picked:
            raise ValueError(f"duplicate LLM generation for {key[0]}/{key[1]} at run 1")
        truncated = g.get("done_reason") == "length"
        recomputed = finalise(g["raw_text"], g["strategy"], truncated)
        if recomputed != g["final_text"]:
            raise ValueError(
                f"finalise() mismatch for {key[0]}/{key[1]} run 1: stored final_text is stale "
                "against today's postprocess.finalise()"
            )
        picked[key] = g["final_text"]
    _require_exactly_one_each(picked, "LLM")
    return picked


def select_template_items(templates: TemplateFallback) -> dict[tuple[str, str], str]:
    """The matching 12 cycle-1 templates: (topic, strategy) -> text."""
    picked = {(t, s): templates.get(t, s, 1) for t in TOPICS for s in STRATEGIES}
    _require_exactly_one_each(picked, "template")
    return picked


def _require_exactly_one_each(picked: dict[tuple[str, str], str], label: str) -> None:
    expected = {(t, s) for t in TOPICS for s in STRATEGIES}
    missing = expected - set(picked)
    if missing:
        raise ValueError(f"{label} selection is missing {sorted(missing)}")
    extra = set(picked) - expected
    if extra:
        raise ValueError(f"{label} selection has unexpected pair(s) {sorted(extra)}")


# --- normalisation ---------------------------------------------------------------------------------


def normalise(text: str) -> str:
    """Strip trailing whitespace on every line, collapse 3+ newlines to one blank line, force
    exactly one blank line before the `**Check:**` line, and end with exactly one newline. Wording
    and length are never changed: they are part of what is being rated."""
    text = _TRAILING_WS_RE.sub("", text)
    text = _MULTI_BLANK_RE.sub("\n\n", text)
    text = _BEFORE_CHECK_RE.sub(r"\n\n\1", text)
    return text.rstrip("\n") + "\n"


# --- shuffle, label, no-tells check -----------------------------------------------------------------


def build_rows(llm_items: dict, template_items: dict, seed: int) -> list[dict]:
    rows = [
        {"topic": t, "strategy": s, "side": "llm", "text": normalise(text)}
        for (t, s), text in llm_items.items()
    ] + [
        {"topic": t, "strategy": s, "side": "template", "text": normalise(text)}
        for (t, s), text in template_items.items()
    ]
    # a fixed input order before shuffling, so the shuffle (not dict/file ordering) is the only
    # source of the final order
    rows.sort(key=lambda r: (r["side"], r["topic"], r["strategy"]))
    random.Random(seed).shuffle(rows)
    for i, row in enumerate(rows, start=1):
        row["id"] = f"R{i:02d}"
    return rows


def check_no_tells(sheet_text: str) -> None:
    m = _FORBIDDEN_RE.search(sheet_text)
    if m:
        raise ValueError(
            f"forbidden word {m.group()!r} found in the rendered sheet (position {m.start()}); "
            "stop and report it, do not edit the text to hide it"
        )


# --- rendering -------------------------------------------------------------------------------------


def render_sheet(rows: list[dict]) -> str:
    parts = [
        "# Blind rating sheet (D2 criterion 5)",
        "",
        RATING_PROMPT,
        "",
        f"**Do not open `{KEY_NAME}` until every item is rated.**",
        "",
        "The 24 items below appear in random order.",
        "",
    ]
    for row in rows:
        parts.append(f"## {row['id']}: {row['topic']} / {row['strategy']}")
        parts.append("")
        parts.append(row["text"].rstrip("\n"))
        parts.append("")
        parts.append(RATING_LABEL)
        parts.append("")
    return "\n".join(parts).rstrip("\n") + "\n"


def render_key(rows: list[dict], seed: int, source: str) -> dict:
    return {"seed": seed, "source": source, "items": {row["id"]: row["side"] for row in rows}}


def build_sheet_and_key(
    seed: int = SEED, results_dir: Path = DEFAULT_RESULTS_DIR, source_name: str = SOURCE_FILE
) -> tuple[str, dict]:
    result = json.loads((results_dir / source_name).read_text(encoding="utf-8"))
    llm_items = select_llm_items(result)
    template_items = select_template_items(TemplateFallback())
    rows = build_rows(llm_items, template_items, seed)
    sheet_text = render_sheet(rows)
    check_no_tells(sheet_text)
    key = render_key(rows, seed, source_name)
    return sheet_text, key


# --- scoring -----------------------------------------------------------------------------------------


def _parse_ratings(sheet_text: str) -> dict[str, str]:
    """{item_id: raw rating string (possibly blank)}, in the order items appear in the sheet."""
    ids = _ITEM_HEADING_RE.findall(sheet_text)
    if len(ids) != len(set(ids)):
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        raise ValueError(f"duplicate item id(s) in sheet: {dupes}")
    blocks = _ITEM_HEADING_RE.split(sheet_text)[1:]  # alternating: id, body, id, body, ...
    ratings: dict[str, str] = {}
    for item_id, body in zip(blocks[0::2], blocks[1::2]):
        m = _RATING_LINE_RE.search(body)
        if not m:
            raise ValueError(f"{item_id}: no 'Rating (1-5):' line found")
        ratings[item_id] = m.group(1).strip()
    return ratings


def score_sheet(sheet_text: str, key: dict) -> dict:
    """Scores a COMPLETED sheet. Raises ValueError, naming the item id, for an unrated item, a
    rating that is not an integer 1-5, or an id that is missing, duplicated, or not in the key.
    A partially rated sheet is never scored."""
    ratings = _parse_ratings(sheet_text)
    key_items = key["items"]
    expected_ids = set(key_items)
    sheet_ids = set(ratings)
    missing = sorted(expected_ids - sheet_ids)
    if missing:
        raise ValueError(f"item(s) missing from the sheet: {missing}")
    unknown = sorted(sheet_ids - expected_ids)
    if unknown:
        raise ValueError(f"item id(s) not in the key: {unknown}")

    scores: dict[str, list[int]] = {"llm": [], "template": []}
    for item_id, raw in ratings.items():
        if raw == "":
            raise ValueError(f"{item_id}: rating is blank")
        if not re.fullmatch(r"[1-5]", raw):
            raise ValueError(f"{item_id}: rating {raw!r} is not an integer from 1 to 5")
        scores[key_items[item_id]].append(int(raw))

    n_llm, n_template = len(scores["llm"]), len(scores["template"])
    mean_llm = sum(scores["llm"]) / n_llm
    mean_template = sum(scores["template"]) / n_template
    llm_ge_3 = mean_llm >= 3
    llm_ge_template = mean_llm >= mean_template
    return {
        "n_llm": n_llm,
        "n_template": n_template,
        "mean_llm": mean_llm,
        "mean_template": mean_template,
        "llm_ge_3": llm_ge_3,
        "llm_ge_template": llm_ge_template,
        "criterion_5": "PASS" if (llm_ge_3 and llm_ge_template) else "FAIL",
    }


# --- CLI ---------------------------------------------------------------------------------------------


def sheet_path(out_dir: Path) -> Path:
    return out_dir / SHEET_NAME


def key_path(out_dir: Path) -> Path:
    return out_dir / KEY_NAME


def write_files(out_dir: Path, sheet_text: str, key: dict, *, force: bool = False) -> None:
    sheet_p, key_p = sheet_path(out_dir), key_path(out_dir)
    if not force:
        existing = [str(p) for p in (sheet_p, key_p) if p.exists()]
        if existing:
            raise FileExistsError(
                f"already exists, use --force to overwrite: {', '.join(existing)}"
            )
    out_dir.mkdir(parents=True, exist_ok=True)
    sheet_p.write_text(sheet_text, encoding="utf-8")
    key_p.write_text(json.dumps(key, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def cmd_build(args: argparse.Namespace) -> int:
    out_dir = Path(args.out)
    sheet_text, key = build_sheet_and_key(results_dir=Path(args.results_dir))
    try:
        write_files(out_dir, sheet_text, key, force=args.force)
    except FileExistsError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"wrote {sheet_path(out_dir)} and {key_path(out_dir)}")
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    sheet_text = Path(args.sheet).read_text(encoding="utf-8")
    key = json.loads(Path(args.key).read_text(encoding="utf-8"))
    try:
        result = score_sheet(sheet_text, key)
    except ValueError as exc:
        print(f"ValueError: {exc}", file=sys.stderr)
        return 1
    print(result)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Blind rating sheet for D2 criterion 5.")
    sub = ap.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="write the sheet and the key")
    b.add_argument("--out", default=str(DEFAULT_RESULTS_DIR), help="output directory")
    b.add_argument("--results-dir", default=str(DEFAULT_RESULTS_DIR), help="where the source result JSON lives")
    b.add_argument("--force", action="store_true", help="overwrite an existing sheet/key")

    s = sub.add_parser("score", help="score a completed sheet against its key")
    s.add_argument("sheet")
    s.add_argument("key")

    args = ap.parse_args(argv)
    if args.command == "build":
        return cmd_build(args)
    return cmd_score(args)


if __name__ == "__main__":
    sys.exit(main())

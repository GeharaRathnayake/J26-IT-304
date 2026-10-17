"""M1 measurement: what does giving the generator the episode so far cost? (A: no history, B: history.)

Reuses `benchmark_llm`'s call path and `llm_scoring` (no copy of the scoring). The set is fixed and committed
in this file: the benchmark's 16 topic x strategy prompts, each with a scripted 4-turn episode history built
from the cycle-1 TEMPLATES (`fallbacks.yaml`) as the tutor turns and two fixed student turns. Run twice in one
session with the same cap and the same prompt revision:

    A: conversation=None   (byte-identical to the r3 prompts `benchmark_llm.prompt_set` builds)
    B: conversation=<the scripted 4 turns>

There is NO pass bar: the numbers are reported for the lead and the owner to judge. Results go to
`benchmarks/llm/memory/` (new files only; nothing existing is touched). The classifier is a prototype proxy and
plays no part here. Run from dev/backend:

    .venv\\Scripts\\python scripts\\benchmark_memory.py --num-predict 220
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

import httpx

SCRIPTS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPTS_DIR.parent
for _p in (str(SCRIPTS_DIR), str(BACKEND_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import benchmark_llm as bench  # noqa: E402
import llm_scoring  # noqa: E402
from app.generation.postprocess import would_ship  # noqa: E402
from app.generation.prompts import PROMPT_REVISION, build_prompt  # noqa: E402
from app.schemas import HistoryTurn  # noqa: E402

DEFAULT_OUT = "benchmarks/llm/memory"
STUDENT_TURNS = ("I don't understand", "can you explain differently?")
TS = "2026-10-17T10:00:00Z"


def scripted_conversation(topic: str, strategy: str) -> list[HistoryTurn]:
    """student, tutor, student, tutor: the tutor turns are the first two cycle-1 templates (in the default order
    theory, example, simplified, analogy) that are NOT the strategy being asked for now."""
    others = [s for s in bench.STRATEGIES if s != strategy][:2]
    turns = []
    for student_text, other in zip(STUDENT_TURNS, others):
        turns.append(HistoryTurn(role="student", text=student_text, ts=TS))
        turns.append(HistoryTurn(role="tutor", text=bench._TEMPLATES.get(topic, other, 1), strategy=other, ts=TS))
    return turns


def memory_prompt_set(with_history: bool) -> list[dict]:
    items = []
    for topic in bench.TOPICS:
        for strategy in bench.STRATEGIES:
            items.append({
                "topic": topic, "strategy": strategy,
                "prompt": build_prompt(
                    topic=topic, strategy=strategy, cycle=1, student_message=bench.STUDENT_MESSAGE,
                    prior_explanations=[],
                    conversation=scripted_conversation(topic, strategy) if with_history else None,
                ),
            })
    return items


def shipped_words(text: str) -> int:
    """Prose outside fenced code (closed or unclosed), without the `**Check:**` line, whitespace-split."""
    t = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    t = re.sub(r"```.*\Z", " ", t, flags=re.DOTALL)
    return len(" ".join(l for l in t.splitlines() if not l.strip().startswith("**Check:**")).split())


def summarise(result: dict) -> dict:
    """The M1 figures, recomputed from a result dict's generations (not from the stored aggregates)."""
    gens = [g for g in result["generations"] if not g.get("error")]
    shipped = [would_ship(g["raw_text"], g["strategy"], llm_scoring.truncated(g["done_reason"])) for g in gens]
    walls = [g["wall_s"] for g in gens]
    return {
        "n": len(gens),
        "prompt_chars_median": statistics.median(len(i["prompt"]) for i in result["prompt_set"]),
        "wall_p50_s": statistics.median(walls),
        "wall_p95_s": llm_scoring.percentile(walls, 95),
        "wall_max_s": max(walls),
        "shippable_in_form_pct": 100.0 * sum(shipped) / len(shipped),
        "median_shipped_words": statistics.median(shipped_words(g["final_text"]) for g, s in zip(gens, shipped) if s),
        "untagged_leak_pct": 100.0 * sum(llm_scoring.reasoning_leak(g["final_text"]) for g in gens) / len(gens),
        "tok_s_median": result["aggregates"]["tok_s_median"],
        "cap_stops_pct": 100.0 * sum(llm_scoring.truncated(g["done_reason"]) for g in gens) / len(gens),
    }


def comparison_markdown(a: dict, b: dict) -> str:
    rows = [
        ("median prompt characters", "prompt_chars_median", "{:.0f}"),
        ("wall p50 (s)", "wall_p50_s", "{:.2f}"),
        ("wall p95 (s)", "wall_p95_s", "{:.2f}"),
        ("wall max (s)", "wall_max_s", "{:.2f}"),
        ("shippable in form (%)", "shippable_in_form_pct", "{:.1f}"),
        ("median shipped words", "median_shipped_words", "{:.0f}"),
        ("untagged leak (%)", "untagged_leak_pct", "{:.1f}"),
        ("cap-stops (%)", "cap_stops_pct", "{:.1f}"),
        ("median tok/s", "tok_s_median", "{:.1f}"),
    ]
    lines = ["| metric | A: no history | B: with history | B - A |", "|---|---|---|---|"]
    for label, key, fmt in rows:
        lines.append(f"| {label} | {fmt.format(a[key])} | {fmt.format(b[key])} | {fmt.format(b[key] - a[key])} |")
    return "\n".join(lines)


def main(argv: list[str] | None = None, transport: httpx.BaseTransport | None = None) -> int:
    ap = argparse.ArgumentParser(description="M1: the cost of giving the generator the episode so far (A/B).")
    ap.add_argument("--model", default="llama3.2:3b")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--base", default="http://127.0.0.1:11434")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--num-predict", type=int, default=220)
    ap.add_argument("--no-unload", action="store_true")
    ap.add_argument("--variants", default="AB", choices=("AB", "A", "B"),
                    help="run both variants back to back (default), or one at a time so the GPU can cool in between")
    ap.add_argument("--compare", action="store_true",
                    help="no Ollama: write the A/B table from the newest A and B result files already in --out")
    args = ap.parse_args(argv)
    log = lambda msg: print(msg, flush=True)  # noqa: E731
    out_dir = Path(args.out)
    if args.compare:
        a_file = max(out_dir.glob("*_memory_A.json"), key=lambda p: p.stat().st_mtime)
        b_file = max(out_dir.glob("*_memory_B.json"), key=lambda p: p.stat().st_mtime)
        a_res, b_res = (json.loads(p.read_text(encoding="utf-8")) for p in (a_file, b_file))
        table = comparison_markdown(summarise(a_res), summarise(b_res))
        name = f"memory_comparison_{b_res['date']}_np{b_res['num_predict']}_{b_res['prompt_revision']}.md"
        (out_dir / name).write_text(
            "# M1 memory A/B\n\nA = no history, B = scripted 4-turn episode history. No pass bar.\n\n" + table + "\n",
            encoding="utf-8")
        print(f"A: {a_file.name}\nB: {b_file.name}\n\n{table}")
        return bench.EXIT_OK
    original_prompt_set = bench.prompt_set
    try:
        with httpx.Client(base_url=args.base, timeout=httpx.Timeout(bench.TIMEOUT_S), transport=transport) as client:
            version = client.get("/api/version").json().get("version", "unknown")
            model = bench.normalise_model(args.model)
            if model not in bench.installed_models(client):
                print(f"{args.model} is not installed; this script never pulls models", file=sys.stderr)
                return bench.EXIT_NO_MODEL
            out_dir.mkdir(parents=True, exist_ok=True)
            summaries: dict[str, dict] = {}
            for variant, with_history in (("A", False), ("B", True)):
                if variant not in args.variants:
                    continue
                log(f"\n== variant {variant} ({'with' if with_history else 'without'} history): {args.runs} runs x 16 prompts, "
                    f"num_predict={args.num_predict}, prompt revision {PROMPT_REVISION} ==")
                bench.prompt_set = lambda cycle=1, priors="same", _w=with_history: memory_prompt_set(_w)  # noqa: E731
                result = bench.benchmark_model(
                    client, model, args.runs, args.base, version, not args.no_unload, log, args.num_predict,
                )
                result["memory_variant"] = variant
                result["conversation"] = (
                    {"turns": 4, "student": list(STUDENT_TURNS), "tutor": "cycle-1 templates (fallbacks.yaml)",
                     "max_turns": 6, "max_chars_per_turn": 600} if with_history else None
                )
                stem = f"{bench.safe_name(model)}_{result['date']}_np{args.num_predict}_{PROMPT_REVISION}_memory_{variant}"
                (out_dir / f"{stem}.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
                summaries[variant] = summarise(result)
                log(f"  placement: {result['placement']}; wrote {stem}.json")
            if len(summaries) < 2:
                print("\n" + json.dumps(summaries, indent=2))
                return bench.EXIT_OK
            table = comparison_markdown(summaries["A"], summaries["B"])
            (out_dir / f"memory_comparison_{result['date']}_np{args.num_predict}_{PROMPT_REVISION}.md").write_text(
                "# M1 memory A/B\n\nA = no history, B = scripted 4-turn episode history. No pass bar.\n\n" + table + "\n",
                encoding="utf-8")
            print("\n" + table)
    except httpx.HTTPError as exc:
        print(f"Ollama is unreachable at {args.base}: {exc!r}", file=sys.stderr)
        return bench.EXIT_UNREACHABLE
    finally:
        bench.prompt_set = original_prompt_set
    return bench.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())

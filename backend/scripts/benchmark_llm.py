"""Reproducible LLM benchmark for decision D2 (which local model generates the tutor's explanations).

    .venv\\Scripts\\python scripts\\benchmark_llm.py --models qwen3:4b llama3.2:3b qwen3:4b-instruct --runs 3

Benchmarks the requested models that are ALREADY INSTALLED (it never pulls, deletes or modifies a
model), skips and reports the rest, and exits non-zero if Ollama is unreachable, no requested model
is installed, or any generation failed. Run it again later after installing another candidate: one
command, no code change. Results go to benchmarks/llm/ (committed evidence):

    <model>_<date>.json           every generation with measurements, scores, raw + finalised text
    <model>_<date>_outputs.md     the human rating sheet (ratings are NOT automated)
    SUMMARY.md                    one table, regenerated from ALL result JSONs

THE PROTOCOL (decision D2): 16 prompts = 4 strategies x 4 topics, each built with the real
`build_prompt` (cycle 1, no prior explanations, student message "I don't understand"); identical for
every model; no per-model tuning. 3 runs per prompt. One throwaway warm-up generation per model
(its wall time is recorded as cold start). CALL PARAMETERS, FIXED (the next stage's adapter must use
these same ones): Ollama /api/chat, the prompt as a single user message, think=false, stream=true,
options.num_predict=80, 60 s client timeout (a slow model is measured, not cut off).

The tutor is a prototype; these are mechanical format checks plus timings, not a judgement of
explanation quality.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

import httpx

SCRIPTS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPTS_DIR.parent
for _p in (str(SCRIPTS_DIR), str(BACKEND_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import llm_scoring  # noqa: E402
from app.generation.postprocess import finalise  # noqa: E402
from app.generation.prompts import build_prompt  # noqa: E402

STRATEGIES = ("theory", "example", "simplified", "analogy")
TOPICS = ("inheritance", "loops", "exception_handling", "polymorphism")
STUDENT_MESSAGE = "I don't understand"
TIMEOUT_S = 60.0
NUM_PREDICT = 80  # a spoken reply (2-4 sentences + the Check line) is about 50-70 tokens
CALL_PARAMETERS = {
    "endpoint": "/api/chat",
    "messages": "one user message containing the prompt",
    "think": False,
    "stream": True,
    "options": {"num_predict": NUM_PREDICT},
    "client_timeout_s": TIMEOUT_S,
}
# The service will fall back to a template after 12 s. That is the service's timeout, NOT a pass mark:
# the benchmark never stops a generation at 12 s, it records what happens (% over 12 s).
SERVICE_TIMEOUT_S = llm_scoring.SERVICE_TIMEOUT_S
EXIT_OK, EXIT_ERRORS, EXIT_UNREACHABLE, EXIT_NO_MODEL = 0, 1, 2, 3


def prompt_set() -> list[dict]:
    items = []
    for topic in TOPICS:
        for strategy in STRATEGIES:
            items.append(
                {
                    "topic": topic,
                    "strategy": strategy,
                    "prompt": build_prompt(
                        topic=topic, strategy=strategy, cycle=1,
                        student_message=STUDENT_MESSAGE, prior_explanations=[],
                    ),
                }
            )
    return items


def safe_name(model: str) -> str:
    return model.replace(":", "_").replace("/", "_")


def normalise_model(name: str) -> str:
    return name if ":" in name else f"{name}:latest"


def chat_payload(model: str, prompt: str) -> dict:
    return {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "think": False,
        "stream": True,
        "options": {"num_predict": NUM_PREDICT},
    }


def generate_once(client: httpx.Client, model: str, prompt: str) -> dict:
    """One streamed generation. Returns the measurements, or {"error": ...}."""
    start = time.perf_counter()
    ttft = None
    parts: list[str] = []
    thinking_chars = 0
    final: dict = {}
    try:
        with client.stream("POST", "/api/chat", json=chat_payload(model, prompt)) as resp:
            if resp.status_code != 200:
                resp.read()
                return {"error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
            for line in resp.iter_lines():
                if not line.strip():
                    continue
                chunk = json.loads(line)
                msg = chunk.get("message") or {}
                content = msg.get("content") or ""
                thinking_chars += len(msg.get("thinking") or "")
                if content and ttft is None:
                    ttft = time.perf_counter() - start
                parts.append(content)
                if chunk.get("done"):
                    final = chunk
    except httpx.TimeoutException:
        return {"error": f"timeout after {TIMEOUT_S:.0f}s without data", "wall_s": time.perf_counter() - start}
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}
    wall = time.perf_counter() - start
    eval_count = final.get("eval_count")
    eval_duration = final.get("eval_duration")
    tok_s = (eval_count / (eval_duration / 1e9)) if eval_count and eval_duration else None
    return {
        "text": "".join(parts),
        "ttft_s": ttft,
        "wall_s": wall,
        "eval_count": eval_count,
        "tok_s": tok_s,
        "done_reason": final.get("done_reason"),
        "prompt_eval_count": final.get("prompt_eval_count"),
        "load_duration_s": (final.get("load_duration") or 0) / 1e9,
        "thinking_chars": thinking_chars,
    }


def installed_models(client: httpx.Client) -> set[str]:
    data = client.get("/api/tags").json()
    return {m["name"] for m in data.get("models", [])}


def unload(client: httpx.Client, model: str) -> dict:
    """Evict the model from memory (NOT a modification of the model) so the warm-up measures a true
    cold start. Returns what happened, for the record."""
    info = {"was_resident": False, "unloaded": False}
    try:
        resident = {m["name"] for m in client.get("/api/ps").json().get("models", [])}
        info["was_resident"] = model in resident
        if not info["was_resident"]:
            return info
        client.post("/api/generate", json={"model": model, "keep_alive": 0})
        for _ in range(20):
            if model not in {m["name"] for m in client.get("/api/ps").json().get("models", [])}:
                info["unloaded"] = True
                break
            time.sleep(0.5)
    except httpx.HTTPError as exc:
        info["error"] = f"{type(exc).__name__}: {exc}"
    return info


def rating_sheet(model: str, run_date: str, generations: list[dict]) -> str:
    lines = [
        f"# Rating sheet: {model} ({run_date})",
        "",
        "Rate each **finalised** reply (what a student would see) from 1 (misleading or unusable) to 5",
        "(correct, clear, the right length, a good check question). Fill in the `Rating:` line. The raw text is",
        "shown so you can see what the model actually said. These ratings are human; nothing here is automated.",
        "",
    ]
    for g in generations:
        lines += [
            f"## {g['id']}: {g['topic']} / {g['strategy']} (run {g['run']})",
            "",
        ]
        if g.get("error"):
            lines += [f"_Generation failed: {g['error']}_", "", "Rating:", ""]
            continue
        s = g["score_raw"]
        lines += [
            f"wall {g['wall_s']:.1f} s, {g['eval_count']} tokens, done_reason `{g['done_reason']}`; raw: "
            f"check_ok={s['check_ok']} sentences={s['sentence_count']} leak={s['reasoning_leak']} "
            f"truncated={s['truncated']}",
            "",
            "Raw:",
            "",
            "~~~~text",
            g["raw_text"],
            "~~~~",
            "",
            "After finalise (what the student sees):",
            "",
            "~~~~markdown",
            g["final_text"],
            "~~~~",
            "",
            "Rating:",
            "",
        ]
    return "\n".join(lines)


def benchmark_model(client: httpx.Client, model: str, runs: int, base: str, ollama_version: str, unload_first: bool, log) -> dict:
    items = prompt_set()
    cold = {"wall_s": None, "unload_first": unload_first}
    if unload_first:
        cold.update(unload(client, model))
        log(f"  cold start: model was resident={cold.get('was_resident')}, unloaded={cold.get('unloaded')}")
    warm = generate_once(client, model, items[0]["prompt"])  # throwaway
    cold["wall_s"] = warm.get("wall_s")
    cold["load_duration_s"] = warm.get("load_duration_s")
    cold["error"] = warm.get("error")
    log(f"  warm-up (cold start): {cold['wall_s'] if cold['wall_s'] is None else round(cold['wall_s'], 1)} s"
        f"{'  ERROR ' + warm['error'] if warm.get('error') else ''}")

    generations = []
    for run in range(1, runs + 1):  # run-major, so identical prompts are never back to back
        for idx, item in enumerate(items):
            gid = f"{safe_name(model)}_p{idx + 1:02d}_r{run}"
            base_rec = {"id": gid, "topic": item["topic"], "strategy": item["strategy"], "run": run, "prompt_index": idx + 1}
            out = generate_once(client, model, item["prompt"])
            if out.get("error"):
                generations.append({**base_rec, "error": out["error"], "wall_s": out.get("wall_s")})
                log(f"  {gid} {item['topic']}/{item['strategy']}: ERROR {out['error']}")
                continue
            raw = out["text"]
            final = finalise(raw, item["strategy"])
            score = llm_scoring.score_generation(raw, final, item["strategy"], out["done_reason"])
            rec = {
                **base_rec,
                "ttft_s": out["ttft_s"], "wall_s": out["wall_s"], "eval_count": out["eval_count"],
                "tok_s": out["tok_s"], "done_reason": out["done_reason"],
                "prompt_eval_count": out["prompt_eval_count"], "thinking_chars": out["thinking_chars"],
                "raw_text": raw, "final_text": final, **score,
            }
            generations.append(rec)
            flags = [k for k, v in (("trunc", score["score_raw"]["truncated"]), ("leak", score["score_raw"]["reasoning_leak"]),
                                    ("nocheck", not score["score_raw"]["check_ok"]), ("empty", score["score_raw"]["empty"])) if v]
            log(f"  {gid} {item['topic']}/{item['strategy']}: wall {out['wall_s']:.1f}s "
                f"ttft {out['ttft_s'] if out['ttft_s'] is None else round(out['ttft_s'], 2)}s "
                f"{(out['tok_s'] or 0):.1f} tok/s {out['eval_count']} tok {out['done_reason']} {' '.join(flags)}")
    return {
        "schema": 1,
        "model": model,
        "date": date.today().isoformat(),
        "ollama_version": ollama_version,
        "base_url": base,
        "call_parameters": CALL_PARAMETERS,
        "service_timeout_s_reference": SERVICE_TIMEOUT_S,
        "service_timeout_note": "the service falls back to a template after this; a reference, not a pass mark, and no generation is stopped at it",
        "student_message": STUDENT_MESSAGE,
        "runs_per_prompt": runs,
        "leak_phrases": list(llm_scoring.LEAK_PHRASES),
        "leak_heuristic_note": "heuristic: a line starting with one of leak_phrases; has false positives and negatives",
        "prompt_set": items,
        "cold_start": cold,
        "generations": generations,
        "aggregates": llm_scoring.aggregate(generations, cold["wall_s"]),
    }


def load_results(out_dir: Path) -> list[dict]:
    results = []
    for path in sorted(out_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and data.get("schema") == 1 and "generations" in data:
            results.append(data)
    return results


def regenerate_summary(out_dir: Path) -> Path:
    path = out_dir / "SUMMARY.md"
    path.write_text(llm_scoring.summary_markdown(load_results(out_dir)), encoding="utf-8")
    return path


def main(argv: list[str] | None = None, transport: httpx.BaseTransport | None = None) -> int:
    ap = argparse.ArgumentParser(description="Benchmark local Ollama models for the tutor (decision D2).")
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--base", default="http://127.0.0.1:11434")
    ap.add_argument("--out", default="benchmarks/llm/")
    ap.add_argument("--no-unload", action="store_true", help="do not evict a resident model before the warm-up")
    args = ap.parse_args(argv)
    log = lambda msg: print(msg, flush=True)  # noqa: E731
    out_dir = Path(args.out)

    try:
        with httpx.Client(base_url=args.base, timeout=httpx.Timeout(TIMEOUT_S), transport=transport) as client:
            version = client.get("/api/version").json().get("version", "unknown")
            have = installed_models(client)
            log(f"Ollama {version} at {args.base}; installed: {sorted(have) or 'none'}")
            wanted = []
            for requested in args.models:
                name = normalise_model(requested)
                if name in have:
                    wanted.append(name)
                else:
                    log(f"SKIPPED {requested}: not installed (this script never pulls models)")
            if not wanted:
                print("no requested model is installed; nothing to benchmark", file=sys.stderr)
                return EXIT_NO_MODEL
            out_dir.mkdir(parents=True, exist_ok=True)
            errors = 0
            for model in wanted:
                log(f"\n== {model}: {args.runs} runs x 16 prompts, num_predict={NUM_PREDICT}, think=false ==")
                result = benchmark_model(client, model, args.runs, args.base, version, not args.no_unload, log)
                stem = f"{safe_name(model)}_{result['date']}"
                (out_dir / f"{stem}.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
                (out_dir / f"{stem}_outputs.md").write_text(
                    rating_sheet(model, result["date"], result["generations"]), encoding="utf-8")
                errors += result["aggregates"]["errors"] + (1 if result["cold_start"].get("error") else 0)
                log(f"  wrote {stem}.json and {stem}_outputs.md")
            summary = regenerate_summary(out_dir)
            log(f"\nwrote {summary}")
    except httpx.HTTPError as exc:
        print(f"Ollama is unreachable at {args.base}: {exc!r}", file=sys.stderr)
        return EXIT_UNREACHABLE
    if errors:
        print(f"{errors} generation(s) failed; see the result JSON", file=sys.stderr)
        return EXIT_ERRORS
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())

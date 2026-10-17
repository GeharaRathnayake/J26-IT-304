"""Exploratory probe (not a benchmark, not D2): qwen3:4b with think=True on the GPU.
Uses the service's own build_prompt and would_ship. Run from dev/backend."""
import json, sys, time
import httpx

sys.path.insert(0, ".")
from app.generation.prompts import build_prompt
from app.generation.postprocess import would_ship, finalise, reasoning_leak

BASE = "http://127.0.0.1:11434"
CASES = [
    ("inheritance", "theory", "I don't understand how super works"),
    ("inheritance", "example", "If Dog extends Animal, does Dog automatically get the name 'Buddy'?"),
    ("loops", "simplified", "I still don't get the difference between while and do-while"),
    ("exception_handling", "analogy", "why do we need try and catch at all"),
    ("inheritance", "theory", "ask me questions related the topic"),
]


def run(model, think, num_predict):
    out = []
    for topic, strategy, msg in CASES:
        prompt = build_prompt(topic=topic, strategy=strategy, cycle=1, student_message=msg, prior_explanations=[])
        body = {"model": model, "messages": [{"role": "user", "content": prompt}], "stream": False,
                "think": think, "keep_alive": "10m", "options": {"num_predict": num_predict}}
        t = time.perf_counter()
        r = httpx.post(f"{BASE}/api/chat", json=body, timeout=180).json()
        wall = time.perf_counter() - t
        m = r.get("message", {})
        content, thinking = m.get("content", ""), m.get("thinking", "") or ""
        trunc = r.get("done_reason") == "length"
        ps = httpx.get(f"{BASE}/api/ps", timeout=5).json()["models"]
        frac = next((p["size_vram"] / p["size"] for p in ps if p["name"].startswith(model.split(":")[0])), None)
        out.append(dict(topic=topic, strategy=strategy, msg=msg, wall_s=round(wall, 2),
                        load_s=round(r.get("load_duration", 0) / 1e9, 2), eval_count=r.get("eval_count"),
                        tok_s=round(r["eval_count"] / (r["eval_duration"] / 1e9), 1) if r.get("eval_duration") else None,
                        thinking_chars=len(thinking), content_words=len(content.split()), truncated=trunc,
                        would_ship=would_ship(content, strategy, trunc),
                        leak=reasoning_leak(finalise(content, strategy, trunc)) if content else None,
                        gpu_fraction=frac, content=content))
        print(json.dumps({k: v for k, v in out[-1].items() if k != "content"}), flush=True)
    return out


if __name__ == "__main__":
    model, think, npred = sys.argv[1], sys.argv[2] == "true", int(sys.argv[3])
    res = run(model, think, npred)
    with open(sys.argv[4], "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)

"""Smoke test: drive a full tutoring episode against a RUNNING server, as the frontend would.

    .venv\\Scripts\\python scripts\\smoke_episode.py [--url http://127.0.0.1:8001] [--expect-fallback auto|true|false|any]

It keeps `history` and `state` exactly as the frontend's reducer.ts does (the current message is
not in `history`; a tutor reply carries `strategy` only when it delivered one; `state` is the
reply's `updated_state`, verbatim), prints one line per turn (with `meta.llm`, `meta.fallback` and
the latencies) and the final episode-log summary, and exits NON-ZERO if any contract item is
violated. Also a rehearsal tool for the demo (B10).

`meta.fallback` on `explain` turns: `auto` (the default) requires true under the template provider
and accepts either under ollama (a reply that would not ship is replaced by the template) or mock;
`true` / `false` require that value on every explain turn; `any` accepts either. Fixed-copy turns
(offer, clarify, resolved, end) always carry `fallback == (meta.llm == "template")`.

The classifier behind the labels is a prototype proxy trained on synthetic answers, not a
validated confusion detector. Depends on httpx only (no app imports), so it works against any
running instance.
"""

from __future__ import annotations

import argparse
import copy
import sys
import time

import httpx

TOPIC = "inheritance"
STATE_KEYS = {"episode_id", "cycle", "strategies_used", "awaiting_cycle_confirmation", "prior_explanations"}
RESPONSE_KEYS = {
    "request_id", "confusion", "detected_request", "action", "strategy", "trigger",
    "response", "updated_state", "episode_log", "meta",
}
# confused turns until the offer, an unclear reply, "yes" into cycle 2, then "got it"
EPISODE = (
    "I don't understand",
    "I don't understand",
    "I don't understand",
    "I don't understand",
    "I don't understand",
    "wait, what do you mean?",
    "yes",
    "got it",
)
TS = "2026-10-14T10:00:00Z"


AUTO = "auto"


def expected_fallback(action: str | None, llm: str | None, expect_fallback) -> bool | None:
    """The meta.fallback this turn must carry, or None when either value is acceptable."""
    if action != "explain":
        return llm == "template"  # fixed copy: a "fallback" only in the sense that no LLM is configured
    if expect_fallback == AUTO:
        return True if llm == "template" else None
    return expect_fallback


def contract_violations(res: dict, request_id: str, expect_fallback) -> list[str]:
    bad: list[str] = []
    if set(res) != RESPONSE_KEYS:
        bad.append(f"response keys differ from the contract: {sorted(set(res) ^ RESPONSE_KEYS)}")
    if res.get("request_id") != request_id:
        bad.append("request_id was not echoed exactly")
    state = res.get("updated_state") or {}
    if set(state) != STATE_KEYS:
        bad.append(f"updated_state incomplete: {sorted(state)}")
    action = res.get("action")
    flag = state.get("awaiting_cycle_confirmation")
    if action in ("offer_new_cycle", "clarify") and flag is not True:
        bad.append(f"{action} without awaiting_cycle_confirmation=true")
    ended = action in ("resolved", "end_unresolved")
    if ended != (res.get("episode_log") is not None):
        bad.append("episode_log must be non-null if and only if the action is terminal")
    if action == "explain":
        if not res.get("strategy") or not res.get("trigger"):
            bad.append("explain without strategy/trigger")
        lines = [ln for ln in (res.get("response") or "").splitlines() if ln.strip()]
        if not lines or not lines[-1].startswith("**Check:**") or res["response"].count("**Check:**") != 1:
            bad.append("explain reply must end with exactly one **Check:** line")
    elif res.get("strategy") is not None or res.get("trigger") is not None:
        bad.append("strategy/trigger must be null unless the action is explain")
    meta = res.get("meta") or {}
    llm = meta.get("llm")
    if not isinstance(llm, str) or not llm:
        bad.append("meta.llm missing")
    if "fallback" not in meta:
        bad.append("meta.fallback missing")
    else:
        want = expected_fallback(action, llm, expect_fallback)
        if want is not None and meta["fallback"] is not want:
            bad.append(f"meta.fallback is {meta['fallback']}, expected {want} ({action}, llm={llm})")
    prob = (res.get("confusion") or {}).get("probability")
    if not isinstance(prob, (int, float)) or isinstance(prob, bool) or not 0 <= prob <= 1:
        bad.append("confusion.probability is not a number in [0, 1]")
    lat = meta.get("latency_ms") or {}
    if set(lat) != {"classify", "llm", "total"} or any(not isinstance(v, (int, float)) or v < 0 for v in lat.values()):
        bad.append("meta.latency_ms malformed")
    return bad


def run_episode(client, topic: str = TOPIC, expect_fallback=AUTO, messages=EPISODE):
    """Returns (rows, violations, final_log). `client` is an httpx.Client-like object."""
    history: list[dict] = []
    state = None
    rows: list[dict] = []
    violations: list[str] = []
    final_log = None
    for n, message in enumerate(messages, start=1):
        request_id = f"smoke-{n}"
        body = {
            "request_id": request_id, "student_id": "stu_smoke", "session_id": "sess_smoke",
            "topic": topic, "message": message,
            "history": copy.deepcopy(history), "state": copy.deepcopy(state),
        }
        history.append({"role": "student", "text": message, "ts": TS})  # SEND_STARTED
        sent = time.perf_counter()
        r = client.post("/tutor/message", json=body)
        wall_ms = (time.perf_counter() - sent) * 1000.0
        if r.status_code != 200:
            violations.append(f"turn {n}: HTTP {r.status_code}: {r.text[:200]}")
            break
        res = r.json()
        violations += [f"turn {n}: {v}" for v in contract_violations(res, request_id, expect_fallback)]
        turn = {"role": "tutor", "text": res["response"], "ts": TS}  # SEND_SUCCEEDED
        if res.get("strategy"):
            turn["strategy"] = res["strategy"]
        history.append(turn)
        state = res["updated_state"]
        meta = res["meta"]
        rows.append({
            "n": n, "message": message, "action": res["action"], "strategy": res["strategy"],
            "trigger": res["trigger"], "cycle": state["cycle"],
            "flag": state["awaiting_cycle_confirmation"], "fallback": meta.get("fallback"),
            "llm_label": meta.get("llm"),
            "classify": meta["latency_ms"]["classify"], "llm": meta["latency_ms"]["llm"],
            "total": meta["latency_ms"]["total"], "wall": wall_ms, "text": res["response"],
        })
        if res.get("episode_log"):
            final_log = res["episode_log"]

    # episode-level expectations for the scripted conversation
    if messages is EPISODE and len(rows) == len(EPISODE):
        actions = [r["action"] for r in rows]
        want = ["explain"] * 4 + ["offer_new_cycle", "clarify", "explain", "resolved"]
        if actions != want:
            violations.append(f"unexpected action sequence: {actions}")
        else:
            if rows[3]["flag"] or not (rows[4]["flag"] and rows[5]["flag"]) or rows[6]["flag"]:
                violations.append("awaiting_cycle_confirmation did not follow offer -> clarify -> accept")
            if rows[6]["cycle"] != 2 or rows[6]["strategy"] != "theory":
                violations.append("accepting the offer did not deliver theory in cycle 2")
            if topic == TOPIC and rows[6]["text"] == rows[0]["text"]:
                violations.append("cycle 2 theory repeats the cycle 1 text")
    if final_log is None:
        violations.append("the episode never produced an episode_log")
    return rows, violations, final_log


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--url", default="http://127.0.0.1:8001")
    ap.add_argument("--expect-fallback", choices=["auto", "true", "false", "any"], default="auto")
    args = ap.parse_args(argv)
    expect = {"auto": AUTO, "true": True, "false": False, "any": None}[args.expect_fallback]
    try:
        # 30 s: above the service's own LLM_TIMEOUT_S, so a slow model shows up as a fallback, not here.
        with httpx.Client(base_url=args.url, timeout=30.0) as client:
            health = client.get("/health").json()
            print(f"health: {health}")
            rows, violations, log = run_episode(client, expect_fallback=expect)
    except httpx.HTTPError as exc:
        print(f"cannot reach the server at {args.url}: {exc!r}", file=sys.stderr)
        return 2

    print(f"{'#':>2} {'action':<16} {'strategy':<10} {'trigger':<10} {'cycle':>5} {'flag':<5} {'meta.llm':<19} "
          f"{'fallback':<8} {'classify':>9} {'llm':>10} {'total':>10} {'wall':>10}  message")
    for r in rows:
        print(f"{r['n']:>2} {r['action']:<16} {str(r['strategy']):<10} {str(r['trigger']):<10} {r['cycle']:>5} "
              f"{str(r['flag']):<5} {str(r['llm_label']):<19} {str(r['fallback']):<8} {r['classify']:>7.2f}ms "
              f"{r['llm']:>8.1f}ms {r['total']:>8.1f}ms {r['wall']:>8.1f}ms  {r['message']!r}")
    explains = [r for r in rows if r["action"] == "explain"]
    print(f"\nexplain turns: {len(explains)}; generated (fallback false): "
          f"{sum(1 for r in explains if r['fallback'] is False)}; fell back to the template (fallback true): "
          f"{sum(1 for r in explains if r['fallback'] is True)}")
    if log:
        print("\nepisode log: outcome={outcome} cycles={cycles} deliveries={n} counted={counted} "
              "requested={requested} winning={winning} is_weak={weak}".format(
                  outcome=log["outcome"], cycles=log["cycles"], n=len(log["deliveries"]),
                  counted=log["counted_strategies"], requested=log["requested_strategies"],
                  winning=log["winning_strategy"], weak=log["is_weak"]))
        print(f"weak_rule: {log['weak_rule']}")
        for d in log["deliveries"]:
            print(f"  #{d['seq']} cycle {d['cycle']} {d['strategy']}/{d['trigger']} -> "
                  f"{d['student_label']} p={d['probability']:.3f} ({d['source']})")
    if violations:
        print("\nCONTRACT VIOLATIONS:", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        return 1
    print("\nOK: every contract item held on every turn.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

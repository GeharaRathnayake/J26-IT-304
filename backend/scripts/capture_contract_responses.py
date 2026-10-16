r"""Capture REAL service responses, in-process, for the frontend's Zod schemas to check (S10, 08 section 3).

Builds the app (FastAPI TestClient, LLM_PROVIDER=template, the real clf-v1.0.0, a fixed clock and
deterministic episode ids) and writes one JSON file per case plus a manifest.json that names, for each
file, the frontend parser that must accept it. The classifier is a prototype proxy trained on synthetic
answers; the captures say nothing about its accuracy.

Determinism: meta.latency_ms values differ per run, so every latency value is written as 0.0. Nothing
else is altered: the files are exactly what the service returned.

    .venv\Scripts\python scripts\capture_contract_responses.py --out <folder>

Exit code: 0 on success; non-zero if any capture is not HTTP 200 or an expected action is not reached.
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
for _p in (str(BACKEND_DIR), str(BACKEND_DIR / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi.testclient import TestClient  # noqa: E402

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from frontend_sim import Episode  # noqa: E402  (the helper that plays turns the way the frontend does)

FIXED_NOW = datetime(2026, 10, 14, 12, 0, 0, tzinfo=timezone.utc)
CONFUSED = "I don't understand"
TO_OFFER = [CONFUSED] * 5
README = r"""# Contract captures

Real responses of the tutor service (template provider, real `clf-v1.0.0`, fixed clock, deterministic
episode ids), one file per case, plus `manifest.json` naming the frontend parser that must accept each.

- Regenerate: `.venv\Scripts\python scripts\capture_contract_responses.py --out tests\contract_captures`
- Check against the frontend's own Zod schemas: `.venv\Scripts\python scripts\zod_contract_check.py tests\contract_captures`
- `meta.latency_ms` values are zeroed (`0.0`) because they vary per run; nothing else is altered.
- The classifier behind the labels is a prototype proxy trained on synthetic answers.
- The frontend team may copy these into its own test suite (08 section 3: a drift breaks a test on both
  sides). Copying them is the frontend's decision.
"""


class CaptureError(Exception):
    pass


def _zero_latency(obj):
    if isinstance(obj, dict):
        return {k: ({kk: 0.0 for kk in v} if k == "latency_ms" and isinstance(v, dict) else _zero_latency(v))
                for k, v in obj.items()}
    if isinstance(obj, list):
        return [_zero_latency(x) for x in obj]
    return obj


def build_captures(zero_latency: bool = True) -> dict[str, tuple[object, dict]]:
    """filename -> (content, manifest entry), in a fixed order. Raises CaptureError on a non-200 or an
    unexpected action. `zero_latency=False` exists only so a mutation check can prove the byte-for-byte
    test notices."""
    ids = itertools.count(1)
    app = create_app(
        settings=Settings(_env_file=None, LLM_PROVIDER="template", OLLAMA_URL="http://127.0.0.1:9"),
        now=lambda: FIXED_NOW,
        new_episode_id=lambda: f"ep_{next(ids)}",
    )
    out: dict[str, tuple[object, dict]] = {}

    def get(client, path, name, parser):
        r = client.get(path)
        if r.status_code != 200:
            raise CaptureError(f"GET {path}: HTTP {r.status_code}")
        out[name] = (r.json(), {"parser": parser})

    def turns(client, prefix, topic, messages, expected):
        ep = Episode(client, topic=topic, prefix=prefix)
        res = []
        for message in messages:
            r = ep.send(message)
            if r.status_code != 200:
                raise CaptureError(f"POST /tutor/message ({prefix}): HTTP {r.status_code} {r.text[:200]}")
            res.append(r.json())
        actual = [(x["action"], x["trigger"]) for x in res]
        if actual != expected:
            raise CaptureError(f"{prefix}: expected {expected}, got {actual}")
        return res

    with TestClient(app) as client:
        get(client, "/topics", "topics.json", "parseTopics")
        get(client, "/health", "health.json", "parseHealth")
        get(client, "/model-info", "model-info.json", "parseModelInfo")

        # one full episode: cycle 1 -> offer -> clarify -> accept -> cycle 2 -> resolved
        a = turns(client, "cap-a", "inheritance", [*TO_OFFER, "wait, what do you mean?", "yes", "got it"], [
            ("explain", "default"), ("explain", "confusion"), ("explain", "confusion"), ("explain", "confusion"),
            ("offer_new_cycle", None), ("clarify", None), ("explain", "confusion"), ("resolved", None),
        ])
        # an explicit request for a strategy
        r = turns(client, "cap-r", "loops", ["show me an example"], [("explain", "request")])
        # a decline ends the episode unresolved
        e = turns(client, "cap-e", "polymorphism", [*TO_OFFER, "no"], [
            ("explain", "default"), ("explain", "confusion"), ("explain", "confusion"), ("explain", "confusion"),
            ("offer_new_cycle", None), ("end_unresolved", None),
        ])

    def tutor(name, res, prefix_index):
        out[name] = (res, {"parser": "parseTutorResponse", "request_id": res["request_id"]})

    order = [
        ("explain.cycle1.json", a[0]), ("explain.request.json", r[0]), ("clarify.json", a[5]),
        ("offer_new_cycle.json", a[4]), ("explain.cycle2.json", a[6]), ("resolved.json", a[7]),
        ("end_unresolved.json", e[5]),
    ]
    for name, res in order:
        tutor(name, res, 0)
    if zero_latency:
        out = {k: (_zero_latency(v), m) for k, (v, m) in out.items()}
    return out


def write_captures(out_dir: Path, zero_latency: bool = True) -> list[str]:
    """Write the files and manifest.json (and a README.md). Returns the file names written."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    captures = build_captures(zero_latency)

    def dump(path: Path, obj) -> None:
        path.write_bytes((json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=False) + "\n").encode("utf-8"))

    for name, (content, _) in captures.items():
        dump(out_dir / name, content)
    dump(out_dir / "manifest.json", {name: entry for name, (_, entry) in captures.items()})
    (out_dir / "README.md").write_bytes(README.encode("utf-8"))
    return list(captures)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True, help="output folder")
    args = ap.parse_args(argv)
    try:
        names = write_captures(Path(args.out))
    except CaptureError as exc:
        print(f"capture failed: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {len(names)} captures + manifest.json to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

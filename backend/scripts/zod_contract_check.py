r"""Run the frontend's Zod parsers over a folder of captured backend responses (S10).

    .venv\Scripts\python scripts\zod_contract_check.py <capture folder>

Runs the frontend's own vitest binary (dev/frontend/node_modules/.bin) against
tests/zod/zod_contract.test.ts. Nothing is written inside dev/frontend/. Exit code: vitest's, unchanged;
2 if the frontend folder, its node_modules or node is missing. Never 0 in those cases.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"
ZOD_DIR = BACKEND_DIR / "tests" / "zod"
EXIT_MISSING = 2


def vitest_binary() -> Path:
    return FRONTEND_DIR / "node_modules" / ".bin" / ("vitest.cmd" if os.name == "nt" else "vitest")


def preflight() -> str | None:
    """A reason the check cannot run, or None."""
    if not FRONTEND_DIR.is_dir():
        return f"frontend folder not found: {FRONTEND_DIR}"
    if not vitest_binary().is_file():
        return f"vitest not found at {vitest_binary()} (run npm install in the frontend, outside this stage)"
    if shutil.which("node") is None:
        return "node is not on the PATH"
    return None


def run_check(capture_dir: Path) -> int:
    reason = preflight()
    if reason:
        print(f"zod contract check cannot run: {reason}", file=sys.stderr)
        return EXIT_MISSING
    env = {**os.environ, "CAPTURE_DIR": str(Path(capture_dir).resolve())}
    cmd = [
        str(vitest_binary()), "run",
        "--root", str(ZOD_DIR),
        "--config", str(ZOD_DIR / "vitest.config.mjs"),
    ]
    return subprocess.run(cmd, env=env, cwd=str(ZOD_DIR)).returncode


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Zod contract check on captured backend responses")
    ap.add_argument("capture_dir", type=Path)
    args = ap.parse_args(argv)
    if not (args.capture_dir / "manifest.json").is_file():
        print(f"no manifest.json in {args.capture_dir}", file=sys.stderr)
        return EXIT_MISSING
    return run_check(args.capture_dir)


if __name__ == "__main__":
    sys.exit(main())

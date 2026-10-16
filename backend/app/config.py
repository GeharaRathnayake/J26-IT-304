"""Environment-driven settings."""

import re
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings

# scheme://host[:port] and nothing else: the browser's `Origin` header never has a path or a trailing slash.
_ORIGIN = re.compile(r"^https?://(?:[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?|\[[0-9A-Fa-f:.]+\])(?::\d{1,5})?$")

# dev/backend/models, resolved from this file so the working directory is irrelevant.
DEFAULT_MODELS_DIR = Path(__file__).resolve().parent.parent / "models"


class Settings(BaseSettings):
    MODEL_VERSION: str = "clf-v1.0.0"
    MODELS_DIR: Path = DEFAULT_MODELS_DIR
    HOST: str = "127.0.0.1"
    # 8001 is fixed by the frontend's committed default (VITE_TUTOR_URL=http://localhost:8001).
    PORT: int = 8001

    # Escalation engine (S4). Tier 3 (personalised ordering) is a seam only, off in PP1.
    MAX_CYCLES: int = 2
    PERSONALISE: bool = False
    # Episode log (S5): is_weak when counted_strategies >= WEAK_THRESHOLD or the episode ended unresolved.
    WEAK_THRESHOLD: int = 3

    # Generation (S8, decision D2). Project owner's decision: the LLM is the default and the template is
    # the deterministic safety net. Benchmarked in benchmarks/llm/SUMMARY.md: llama3.2:3b was usable in
    # 88% of replies against a 90% bar (it did NOT meet the bar), so every reply that would not ship is
    # replaced by the template (meta.fallback: true). An unknown value fails at startup.
    LLM_PROVIDER: Literal["template", "mock", "ollama"] = "ollama"
    # D2: qwen3:4b disqualified (100% untagged reasoning leak, qwen3_4b_2026-10-15_np80_r2.json and
    # qwen3_4b_2026-10-15_np110_r2.json); llama3.2:3b 0% leak (llama3.2_3b_2026-10-15_np110_r2.json).
    LLM_MODEL: str = "llama3.2:3b"
    # 127.0.0.1, not localhost: avoids an IPv6 lookup delay on Windows. Docker sets host.docker.internal.
    OLLAMA_URL: str = "http://127.0.0.1:11434"
    # num_predict. Measured: 88% usable at 110 (llama3.2_3b_2026-10-15_np110_r2.json) against 81% at 80
    # (llama3.2_3b_2026-10-15_np80_r2.json).
    LLM_MAX_TOKENS: int = 110
    # S8b: cycle-2 prompts (from `app/orchestrator.py` passing only the same strategy's priors) are
    # LONGER than cycle-1 prompts and their measured p95 is the binding one. T = ceil(max(p95_cycle1,
    # p95_cycle2_same) x 1.2) at num_predict 110: cycle-1 p95 11.0 s (llama3.2_3b_2026-10-15_np110_r2.json),
    # cycle-2-same p95 14.6 s (llama3.2_3b_2026-10-15_np110_r2_c2same.json); max x 1.2 = 17.52, rounded up.
    # Set from measurement, never from the 3-second latency figure (that is a measurement target).
    LLM_TIMEOUT_S: float = 18.0

    # Browser origins allowed to call this service (CORS). Decision D5 chose the `direct` transport: the
    # browser at http://localhost:5173 (Vite) calls this service cross-origin, and vite.config.ts has no
    # dev proxy (07 section 8, 09 D5). Comma-separated so it works as a plain environment variable.
    # 127.0.0.1:5173 is included because a person may open the frontend by IP, which is a different
    # origin. Exact origins only: no `*`, no trailing slash, no path (validated below).
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Per-turn research log (R4). OFF by default: it records real student messages, which needs
    # ethics approval first. When set, one JSON line is appended per turn.
    TURN_LOG_PATH: Path | None = None

    @field_validator("LLM_PROVIDER", mode="before")
    @classmethod
    def _known_provider(cls, v):
        if v not in ("template", "mock", "ollama"):
            raise ValueError(f"LLM_PROVIDER={v!r} is not supported; use 'ollama', 'template' or 'mock'")
        return v

    @field_validator("CORS_ORIGINS")
    @classmethod
    def _valid_origins(cls, v: str) -> str:
        entries = [part.strip() for part in v.split(",") if part.strip()]
        if not entries:
            raise ValueError("CORS_ORIGINS is empty; list at least one origin such as http://localhost:5173")
        for origin in entries:
            if origin == "*":
                raise ValueError("CORS_ORIGINS must not contain '*'; list exact origins")
            if not _ORIGIN.match(origin):
                raise ValueError(
                    f"CORS_ORIGINS entry {origin!r} is not scheme://host[:port] "
                    "(no path, no trailing slash, scheme required)"
                )
        return v

    def cors_origin_list(self) -> list[str]:
        """The parsed CORS_ORIGINS: split on commas, each stripped, empties dropped."""
        return [part.strip() for part in self.CORS_ORIGINS.split(",") if part.strip()]

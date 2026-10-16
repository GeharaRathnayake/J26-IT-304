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
    # the deterministic safety net, so every reply that would not ship is replaced by the template
    # (meta.fallback: true). Where D2 stands for llama3.2:3b (r2 and r3, both results, one criterion still
    # unrated) is the block "D2, as at 2026-10-17" in benchmarks/llm/README.md; it is not paraphrased here.
    # "Shippable in form" is a format check, not accuracy. An unknown value fails at startup.
    LLM_PROVIDER: Literal["template", "mock", "ollama"] = "ollama"
    # D2: qwen3:4b disqualified (100% untagged reasoning leak, qwen3_4b_2026-10-15_np80_r2.json and
    # qwen3_4b_2026-10-15_np110_r2.json); llama3.2:3b 0% leak (llama3.2_3b_2026-10-15_np110_r2.json).
    LLM_MODEL: str = "llama3.2:3b"
    # 127.0.0.1, not localhost: avoids an IPv6 lookup delay on Windows. Docker sets host.docker.internal.
    OLLAMA_URL: str = "http://127.0.0.1:11434"
    # num_predict. r3, owner decision B, 2026-10-17: 220 (was 110 under r2). The owner found r2's replies too
    # short; r3 asks for about 80 to 120 words and needs the room. Measured on the GPU
    # (llama3.2_3b_2026-10-17_np220_r3.json and _c2same.json): 100% / 97.9% shippable in form, 33.3% / 39.6%
    # of replies stopped at this cap (bar 6, cycle 1 <= 25%, MISSED), median shipped words 110 / 119, wall
    # p95 5.87 s / 5.97 s. r2 at 110 (llama3.2_3b_2026-10-15_np110_r2.json): 87.5% shippable in form.
    LLM_MAX_TOKENS: int = 220
    # S8b (r2, 110 tokens, dGPU OFF): cycle-2 prompts (from `app/orchestrator.py` passing only the same
    # strategy's priors) are LONGER than cycle-1 prompts and their measured p95 is the binding one.
    # T = ceil(max(p95_cycle1, p95_cycle2_same) x 1.2): cycle-1 p95 11.0 s
    # (llama3.2_3b_2026-10-15_np110_r2.json), cycle-2-same p95 14.6 s (..._np110_r2_c2same.json);
    # max x 1.2 = 17.52, rounded up. NOT re-derived for r3 (lead ruling): it guards the dGPU-off case,
    # and r3's GPU p95 is about 6 s. Never derive it from the 3-second latency figure.
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

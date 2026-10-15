"""Environment-driven settings."""

from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings

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
    # Measured wall p95 11.0 s at 110 tokens (llama3.2_3b_2026-10-15_np110_r2.json) x 1.2, rounded up.
    # Set from measurement, never from the 3-second latency figure (that is a measurement target).
    LLM_TIMEOUT_S: float = 14.0

    # Per-turn research log (R4). OFF by default: it records real student messages, which needs
    # ethics approval first. When set, one JSON line is appended per turn.
    TURN_LOG_PATH: Path | None = None

    @field_validator("LLM_PROVIDER", mode="before")
    @classmethod
    def _known_provider(cls, v):
        if v not in ("template", "mock", "ollama"):
            raise ValueError(f"LLM_PROVIDER={v!r} is not supported; use 'ollama', 'template' or 'mock'")
        return v

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

    # Generation (S6b). `ollama` arrives in a later stage, after the model benchmark; until
    # then an unknown value fails at startup instead of silently falling back.
    LLM_PROVIDER: Literal["template", "mock"] = "template"
    # A cutoff, never to be derived from the 3-second latency figure (that is a measurement target).
    LLM_TIMEOUT_S: float = 8.0

    # Per-turn research log (R4). OFF by default: it records real student messages, which needs
    # ethics approval first. When set, one JSON line is appended per turn.
    TURN_LOG_PATH: Path | None = None

    @field_validator("LLM_PROVIDER", mode="before")
    @classmethod
    def _known_provider(cls, v):
        if v not in ("template", "mock"):
            raise ValueError(
                f"LLM_PROVIDER={v!r} is not supported yet; use 'template' or 'mock' "
                "(the 'ollama' provider arrives in a later stage)"
            )
        return v

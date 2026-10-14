"""Environment-driven settings."""

from pathlib import Path

from pydantic_settings import BaseSettings

# dev/backend/models, resolved from this file so the working directory is irrelevant.
DEFAULT_MODELS_DIR = Path(__file__).resolve().parent.parent / "models"


class Settings(BaseSettings):
    MODEL_VERSION: str = "clf-v1.0.0"
    MODELS_DIR: Path = DEFAULT_MODELS_DIR
    HOST: str = "127.0.0.1"
    # 8001 is fixed by the frontend's committed default (VITE_TUTOR_URL=http://localhost:8001).
    PORT: int = 8001

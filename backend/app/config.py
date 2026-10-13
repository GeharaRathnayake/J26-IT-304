"""Environment-driven settings."""

from pathlib import Path

from pydantic_settings import BaseSettings

# dev/backend/models, resolved from this file so the working directory is irrelevant.
DEFAULT_MODELS_DIR = Path(__file__).resolve().parent.parent / "models"


class Settings(BaseSettings):
    MODEL_VERSION: str = "clf-v1.0.0"
    MODELS_DIR: Path = DEFAULT_MODELS_DIR

"""Tutor service entry point (S1: verified model load and /health only).

The classifier is a prototype proxy trained on synthetic answers, not a
validated confusion detector.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from pydantic import BaseModel, ConfigDict

from app.classifier.model import ModelLoadError, load_model
from app.config import Settings

logger = logging.getLogger("app")


def _configure_logging() -> None:
    """Uvicorn only configures its own loggers; make the 'app' INFO lines visible."""
    app_logger = logging.getLogger("app")
    app_logger.setLevel(logging.INFO)
    if not app_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s:     [%(name)s] %(message)s"))
        app_logger.addHandler(handler)
        app_logger.propagate = False


class HealthResponse(BaseModel):
    """Mirrors HealthResponse in frontend/src/features/tutor/api/types.ts."""

    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    status: str
    model_loaded: bool
    llm_reachable: bool
    model_version: str | None


def create_app(models_dir: Path | None = None) -> FastAPI:
    settings = Settings()
    root = Path(models_dir) if models_dir is not None else settings.MODELS_DIR

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Loaded once per process. A failed verification (ModelLoadError only) is
        # logged and the service starts degraded with no model, so /health can
        # report it and later stages can answer 503. A model that failed any
        # check is never stored. Any other exception still propagates.
        try:
            app.state.model = load_model(root / settings.MODEL_VERSION)
        except ModelLoadError as exc:
            logger.error("model NOT loaded, starting degraded: %s", exc)
            app.state.model = None
        yield

    app = FastAPI(title="Adaptive AI Voice Tutor: tutor service", lifespan=lifespan)

    @app.get("/health", response_model=HealthResponse)
    def health(request: Request) -> HealthResponse:
        model = getattr(request.app.state, "model", None)
        model_loaded = model is not None
        return HealthResponse(
            # 'degraded' = verification failed at startup (see lifespan).
            status="ok" if model_loaded else "degraded",
            model_loaded=model_loaded,
            # Hard-coded until the Ollama stage adds a real reachability probe.
            llm_reachable=False,
            model_version=model.version if model_loaded else None,
        )

    return app


_configure_logging()
app = create_app()

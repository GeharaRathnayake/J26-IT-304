"""Tutor service entry point: verified model load, /health, /topics and POST /tutor/message.

The classifier is a prototype proxy trained on synthetic answers, not a
validated confusion detector.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from app.classifier.model import ModelLoadError, load_model
from app.config import Settings
from app.escalation.engine import EngineConfig, default_episode_id
from app.escalation.episode_log import utc_now
from app.generation.adapters import LLMAdapter, MockAdapter, TemplateFallback
from app.orchestrator import Deps, TurnError, TurnLogger, handle_turn
from app.schemas import TutorRequest, TutorResponse
from app.topics import public_topics

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


def create_app(
    models_dir: Path | None = None,
    *,
    settings: Settings | None = None,
    adapter: LLMAdapter | None = None,
    now: Callable[[], datetime] = utc_now,
    new_episode_id: Callable[[], str] = default_episode_id,
) -> FastAPI:
    """`adapter`, `now` and `new_episode_id` are injection points for tests; `adapter` is used only
    when LLM_PROVIDER is "mock"."""
    settings = settings if settings is not None else Settings()
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
        # Our own template file: a broken one is a build defect, so a TemplateError here is NOT
        # caught and startup fails loudly.
        templates = TemplateFallback()
        provider = settings.LLM_PROVIDER
        app.state.adapter = (adapter or MockAdapter()) if provider == "mock" else None
        turn_logger = TurnLogger(settings.TURN_LOG_PATH) if settings.TURN_LOG_PATH is not None else None
        app.state.deps = (
            None
            if app.state.model is None
            else Deps(
                model=app.state.model,
                cfg=EngineConfig.from_settings(settings),
                templates=templates,
                provider=provider,
                adapter=app.state.adapter,
                llm_timeout_s=settings.LLM_TIMEOUT_S,
                weak_threshold=settings.WEAK_THRESHOLD,
                now=now,
                new_episode_id=new_episode_id,
                turn_logger=turn_logger,
            )
        )
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

    @app.get("/topics")
    def topics() -> list[dict[str, str]]:
        # The service owns the topic list; `general` is accepted but never listed.
        return public_topics()

    @app.post("/tutor/message", response_model=TutorResponse)
    async def tutor_message(body: TutorRequest, request: Request) -> TutorResponse:
        # Order: invalid body -> 422 (FastAPI, before this runs); model not loaded -> 503;
        # otherwise the turn is handled. An unservable turn (impossible echoed state, history that
        # contradicts the state) is a 422 from the orchestrator.
        deps = getattr(request.app.state, "deps", None)
        if deps is None:
            raise HTTPException(
                status_code=503,
                detail="classifier failed verification at startup; model not loaded",
            )
        try:
            return await handle_turn(body, deps)
        except TurnError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return app


_configure_logging()
app = create_app()

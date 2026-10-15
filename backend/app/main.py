"""Tutor service entry point: verified model load, /health, /topics and POST /tutor/message.

The classifier is a prototype proxy trained on synthetic answers, not a
validated confusion detector.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from app.classifier.model import ModelLoadError, load_model
from app.config import Settings
from app.escalation.engine import EngineConfig, default_episode_id
from app.escalation.episode_log import utc_now
from app.generation.adapters import LLMAdapter, MockAdapter, OllamaAdapter, TemplateFallback
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


# The warm-up loads the model into Ollama's memory so the first student question does not pay the cold
# start (measured ~12-18 s cold against ~7-9 s warm). Generous: it runs in the background.
WARMUP_PROMPT = "Reply with the single word: ready."
WARMUP_TIMEOUT_S = 90.0
HEALTH_CHECK_TIMEOUT_S = 1.0


async def _warm_up(adapter: LLMAdapter, model: str) -> None:
    """One throwaway generation. A failure is a WARNING, never a failed startup."""
    started = time.perf_counter()
    try:
        await asyncio.wait_for(adapter.complete(WARMUP_PROMPT, WARMUP_TIMEOUT_S), WARMUP_TIMEOUT_S)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.warning(
            "LLM warm-up failed (%s) after %.1f s; continuing: replies fall back to templates until %s answers",
            type(exc).__name__, time.perf_counter() - started, model,
        )
        return
    logger.info("LLM warm-up done: %s loaded in %.1f s", model, time.perf_counter() - started)


def create_app(
    models_dir: Path | None = None,
    *,
    settings: Settings | None = None,
    adapter: LLMAdapter | None = None,
    ollama_transport: httpx.AsyncBaseTransport | None = None,
    now: Callable[[], datetime] = utc_now,
    new_episode_id: Callable[[], str] = default_episode_id,
) -> FastAPI:
    """`adapter`, `ollama_transport`, `now` and `new_episode_id` are injection points for tests.
    `adapter` replaces the provider's adapter ("mock" or "ollama"); `ollama_transport` (an
    httpx.MockTransport) is what the real OllamaAdapter talks through under "ollama", for generation,
    the /health check and the warm-up alike."""
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
        client: httpx.AsyncClient | None = None
        warm_up: asyncio.Task | None = None
        llm_label = provider
        if provider == "mock":
            app.state.adapter = adapter or MockAdapter()
        elif provider == "ollama":
            llm_label = f"ollama:{settings.LLM_MODEL}"
            # One client for the process lifetime: generation, /health and the warm-up share it.
            client = httpx.AsyncClient(transport=ollama_transport)
            app.state.adapter = adapter or OllamaAdapter(
                client, settings.OLLAMA_URL, settings.LLM_MODEL, settings.LLM_MAX_TOKENS
            )
            logger.info(
                "LLM provider: ollama, model %s at %s (num_predict %d, timeout %.1f s); template fallback on",
                settings.LLM_MODEL, settings.OLLAMA_URL, settings.LLM_MAX_TOKENS, settings.LLM_TIMEOUT_S,
            )
            # In the background: startup is never blocked, and a failure never fails it. Only the real
            # adapter is warmed (an injected test adapter would record the warm-up prompt as a turn).
            if isinstance(app.state.adapter, OllamaAdapter):
                warm_up = asyncio.create_task(_warm_up(app.state.adapter, settings.LLM_MODEL))
        else:
            app.state.adapter = None
        app.state.provider = provider
        app.state.warm_up = warm_up
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
                llm_label=llm_label,
                weak_threshold=settings.WEAK_THRESHOLD,
                now=now,
                new_episode_id=new_episode_id,
                turn_logger=turn_logger,
            )
        )
        try:
            yield
        finally:
            if warm_up is not None and not warm_up.done():
                warm_up.cancel()
                try:
                    await warm_up
                except asyncio.CancelledError:
                    pass
            if client is not None:
                await client.aclose()

    app = FastAPI(title="Adaptive AI Voice Tutor: tutor service", lifespan=lifespan)

    @app.get("/health", response_model=HealthResponse)
    async def health(request: Request) -> HealthResponse:
        model = getattr(request.app.state, "model", None)
        model_loaded = model is not None
        # A real, cheap check on every call (GET /api/tags, ~1 s): true only if Ollama answers AND the
        # model is pulled. Always false under the template or mock provider. The frontend shows its
        # "running with template responses" banner from this flag. It does not affect `status`: the
        # service still answers (with templates) when the LLM is down.
        llm_reachable = False
        adapter = getattr(request.app.state, "adapter", None)
        if getattr(request.app.state, "provider", None) == "ollama" and isinstance(adapter, OllamaAdapter):
            llm_reachable = await adapter.reachable(HEALTH_CHECK_TIMEOUT_S)
        return HealthResponse(
            # 'degraded' = verification failed at startup (see lifespan).
            status="ok" if model_loaded else "degraded",
            model_loaded=model_loaded,
            llm_reachable=llm_reachable,
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

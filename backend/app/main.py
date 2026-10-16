"""Tutor service entry point: verified model load, /health, /topics, /model-info and POST /tutor/message.

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
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, ValidationError

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
    """Mirrors HealthResponse in frontend/src/features/tutor/api/types.ts, plus ONE additive,
    backend-only diagnostic field (`llm_gpu_fraction`). Safe because the frontend's Zod schema is a
    plain z.object that strips unknown keys (07 section 2 rule 5)."""

    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    status: str
    model_loaded: bool
    llm_reachable: bool
    model_version: str | None
    # size_vram / size of the LLM from Ollama's /api/ps: 1.0 fully on GPU, 0.0 fully on CPU, None
    # unknown (probe failed, model not resident, or not the ollama provider). Below 1.0 = slower replies.
    llm_gpu_fraction: float | None


class ModelInfo(BaseModel):
    """Mirrors ModelInfo in frontend/src/features/tutor/api/types.ts. Used only to VALIDATE the block
    once at startup; the endpoint serves the parsed dict itself, so number formatting is untouched."""

    model_config = ConfigDict(extra="forbid", strict=True)

    version: str
    trained_at: str
    dataset: str
    threshold: float
    metrics: dict[str, float]


def _validate_model_info(metadata: dict) -> None:
    """A malformed model_info is an artifact defect: raise ModelLoadError so the start is degraded."""
    try:
        ModelInfo.model_validate(metadata["model_info"])
    except KeyError as exc:
        raise ModelLoadError("metadata.json has no model_info block") from exc
    except ValidationError as exc:
        raise ModelLoadError(f"metadata.json model_info is malformed: {exc}") from exc


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
    # Placement is fixed when the model loads (and kept for keep_alive): observe it, never assume it.
    # A failing probe is None, never an exception, and never fails startup.
    fraction = await adapter.placement(HEALTH_CHECK_TIMEOUT_S)
    meaning = "1.0 = fully on GPU, 0.0 = fully on CPU, None = unknown"
    if fraction is not None and fraction < 1.0:
        logger.warning(
            "LLM placement: %s gpu_fraction=%s (%s); replies will be slower than measured on the GPU",
            model, fraction, meaning,
        )
    else:
        logger.info("LLM placement: %s gpu_fraction=%s (%s)", model, fraction, meaning)


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
            loaded = load_model(root / settings.MODEL_VERSION)
            _validate_model_info(loaded.metadata)
            app.state.model = loaded
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

    # Decision D5 (09): the browser calls this service cross-origin (07 section 8). add_middleware puts
    # CORS outside the routing and exception layers, so 422 and 503 responses carry the header too.
    # Exact origins, no regex; only the one non-simple header the frontend sends (Content-Type on POST).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list(),
        allow_methods=["GET", "POST"],
        # Redundant: Starlette's SAFELISTED_HEADERS already include Content-Type
        # (allow_headers = sorted(SAFELISTED_HEADERS | set(allow_headers))). Kept to document intent.
        allow_headers=["Content-Type"],
        allow_credentials=False,
        max_age=600,
    )

    @app.get("/health", response_model=HealthResponse)
    async def health(request: Request) -> HealthResponse:
        model = getattr(request.app.state, "model", None)
        model_loaded = model is not None
        # A real, cheap check on every call (GET /api/tags, ~1 s): true only if Ollama answers AND the
        # model is pulled. Always false under the template or mock provider. The frontend shows its
        # "running with template responses" banner from this flag. It does not affect `status`: the
        # service still answers (with templates) when the LLM is down.
        llm_reachable = False
        llm_gpu_fraction: float | None = None
        adapter = getattr(request.app.state, "adapter", None)
        if getattr(request.app.state, "provider", None) == "ollama" and isinstance(adapter, OllamaAdapter):
            # Concurrently: /health must not be slower in the worst case than one probe. Neither
            # probe raises, and placement never changes llm_reachable (different endpoints).
            llm_reachable, llm_gpu_fraction = await asyncio.gather(
                adapter.reachable(HEALTH_CHECK_TIMEOUT_S), adapter.placement(HEALTH_CHECK_TIMEOUT_S)
            )
        return HealthResponse(
            # 'degraded' = verification failed at startup (see lifespan).
            status="ok" if model_loaded else "degraded",
            model_loaded=model_loaded,
            llm_reachable=llm_reachable,
            model_version=model.version if model_loaded else None,
            llm_gpu_fraction=llm_gpu_fraction,
        )

    @app.get("/model-info")
    def model_info(request: Request) -> dict:
        # The block parsed (and validated) at load, served unchanged. Never re-read from disk.
        model = getattr(request.app.state, "model", None)
        if model is None:
            raise HTTPException(
                status_code=503,
                detail="classifier failed verification at startup; model not loaded",
            )
        return model.metadata["model_info"]

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

"""
Atlas AI – FastAPI application entry-point.

Bootstraps:
  • OpenTelemetry tracing
  • Database connection pool (skipped in MOCK_MODE)
  • All API routers
  • CORS middleware
  • Prometheus metrics middleware
  • Health-check endpoint

Set MOCK_MODE=true to run with zero external dependencies (no Postgres / Redis).
All endpoints are served from in-memory mock data — perfect for local demos.
"""

from __future__ import annotations

import os
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from app.config import get_settings

_MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() in ("true", "1", "yes")

if not _MOCK_MODE:
    from app.api import agents, incidents, metrics, rca, websocket
    from app.db.database import close_db, init_db

logger = structlog.get_logger(__name__)
settings = get_settings()

# ---------------------------------------------------------------------------
# Prometheus instruments (module-level so they survive across requests)
# ---------------------------------------------------------------------------
REQUEST_COUNT = Counter(
    "atlas_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)
REQUEST_LATENCY = Histogram(
    "atlas_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)


# ---------------------------------------------------------------------------
# OpenTelemetry bootstrap
# ---------------------------------------------------------------------------
def _setup_otel(app: FastAPI) -> None:
    """Configure OpenTelemetry SDK and instrument FastAPI."""
    if not settings.OTEL_ENABLED:
        return

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource(attributes={"service.name": settings.OTEL_SERVICE_NAME})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)
    SQLAlchemyInstrumentor().instrument()
    RedisInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()

    logger.info("OpenTelemetry tracing enabled", endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage startup and shutdown of shared resources."""
    logger.info(
        "Atlas AI starting",
        environment=settings.ENVIRONMENT,
        version=settings.APP_VERSION,
        mock_mode=_MOCK_MODE,
    )

    if not _MOCK_MODE:
        await init_db()
        logger.info("Database connection pool initialised")
    else:
        logger.info("MOCK_MODE enabled — skipping database and Redis init")

    yield  # ── application runs here ──────────────────────────────────────

    logger.info("Atlas AI shutting down – releasing resources")
    if not _MOCK_MODE:
        await close_db()


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------
def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "Multi-agent incident response and root-cause analysis platform "
            "powered by OpenAI and MCP tool servers."
        ),
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    # ── CORS ────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Request instrumentation middleware ──────────────────────────────────
    @app.middleware("http")
    async def _metrics_middleware(request: Request, call_next: object) -> Response:
        start = time.perf_counter()
        # Normalise path so high-cardinality IDs don't explode label sets
        path = request.url.path
        response: Response = await call_next(request)  # type: ignore[operator]
        latency = time.perf_counter() - start
        REQUEST_COUNT.labels(request.method, path, response.status_code).inc()
        REQUEST_LATENCY.labels(request.method, path).observe(latency)
        return response

    # ── Routers ─────────────────────────────────────────────────────────────
    if _MOCK_MODE:
        from app.api.mock_routes import router as mock_router
        app.include_router(mock_router)
    else:
        app.include_router(incidents.router, prefix="/api/v1/incidents", tags=["incidents"])
        app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
        app.include_router(rca.router, prefix="/api/v1/rca", tags=["rca"])
        app.include_router(metrics.router, prefix="/api/v1/metrics", tags=["metrics"])
        app.include_router(websocket.router, prefix="/ws", tags=["websocket"])

        # ── Health endpoints (non-mock) ──────────────────────────────────────
        @app.get("/health", tags=["ops"], include_in_schema=False)
        async def health() -> dict[str, str]:
            return {"status": "ok", "version": settings.APP_VERSION}

        @app.get("/health/ready", tags=["ops"], include_in_schema=False)
        async def readiness() -> dict[str, object]:
            """Deep readiness check – verifies DB + Redis reachability."""
            from app.db.database import check_db_health

            db_ok = await check_db_health()
            return {
                "status": "ready" if db_ok else "degraded",
                "checks": {"database": db_ok},
            }

    @app.get("/metrics/prometheus", tags=["ops"], include_in_schema=False)
    async def prometheus_metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    # ── OTel (after app creation so instrumentor can wrap the app) ───────────
    _setup_otel(app)

    return app


app = create_app()

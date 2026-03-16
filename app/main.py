import time
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import engine
from app.services.cache_service import cache

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──
    logger.info("Starting Voya.ai API", env=settings.app_env)

    # Run DB migrations on startup in dev (in prod use Alembic CLI in CI)
    if settings.app_env == "development":
        from app.db.session import Base
        import app.models.user  # noqa: F401 — ensures models are registered
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created / verified")

    yield

    # ── Shutdown ──
    logger.info("Shutting down Voya.ai API")
    await cache.close()
    await engine.dispose()


app = FastAPI(
    title="Voya.ai API",
    description="AI-powered travel planning backend",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request logging middleware ─────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    logger.info(
        "request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=duration_ms,
    )
    return response


# ── Global error handlers ──────────────────────────────────────────────
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# ── Routes ─────────────────────────────────────────────────────────────
app.include_router(api_router)


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}
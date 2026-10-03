"""
Fair Drop API — application entry point.

Configures the FastAPI application, database lifespan hooks, CORS middleware,
request ID tracing, exception handlers, and mounts API routers.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.config import lru_settings
from app.database import close_db, init_db
from app.security.jwt import InvalidTokenError
from app.security.request_ids import get_request_id

logger = logging.getLogger(__name__)

settings = lru_settings()


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Fair Drop API starting")
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as exc:
        logger.error("Database initialization failed: %s", exc)

    yield

    # Shutdown
    logger.info("Fair Drop API shutting down")
    try:
        await close_db()
        logger.info("Database closed")
    except Exception as exc:
        logger.error("Database close failed: %s", exc)


# ── Application factory ───────────────────────────────────────────────────────

app = FastAPI(
    title="Fair Drop API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ── Middleware ────────────────────────────────────────────────────────────────

@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """
    Ensure every request has a tracking ID in state and in the response header.
    """
    request_id = await get_request_id(request)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Exception handlers ────────────────────────────────────────────────────────

@app.exception_handler(InvalidTokenError)
async def invalid_token_handler(request: Request, exc: InvalidTokenError):
    """
    Catch any unhandled InvalidTokenError and format using standard error envelope.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error": {
                "code": exc.code,
                "message": str(exc),
                "request_id": request_id,
                "details": {},
            }
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Unwrap detail dict to ensure error envelope is always at JSON root.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "HTTP_ERROR",
                "message": str(exc.detail),
                "request_id": request_id,
                "details": {},
            }
        },
    )


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(api_router)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
async def root() -> dict:
    return {"service": "fair-drop", "status": "running", "version": "0.1.0"}


@app.get("/health")
async def health() -> dict:
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

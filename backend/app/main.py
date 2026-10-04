"""
Fair Drop API — application entry point.

Configures the FastAPI application, database lifespan hooks, CORS middleware,
request ID tracing, exception handlers, and mounts API routers.
"""
# API entrypoint - reloaded v2

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
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
        await asyncio.wait_for(init_db(), timeout=10.0)
        logger.info("Database initialized")
    except (asyncio.TimeoutError, asyncio.CancelledError) as te:
        logger.warning("Database init timed out or cancelled during startup: %s", te)
    except Exception as exc:
        logger.error("Database initialization failed: %s", exc)

    try:
        yield
    except (asyncio.CancelledError, GeneratorExit):
        # Gracefully absorb cancellation signals from uvicorn --reload / process shutdown
        pass
    finally:
        # Shutdown
        logger.info("Fair Drop API shutting down")
        try:
            await asyncio.wait_for(close_db(), timeout=5.0)
            logger.info("Database connection pool cleanly closed")
        except (Exception, asyncio.CancelledError) as exc:
            logger.warning("Database close warning during shutdown: %s", exc)


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


from app.middleware.rate_limit import GlobalRateLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(GlobalRateLimitMiddleware)

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


from fastapi.encoders import jsonable_encoder


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Format FastAPI Pydantic schema validation errors to standard error envelope.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    try:
        errors = jsonable_encoder(exc.errors())
    except Exception:
        errors = [str(err) for err in exc.errors()]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Validation error in request payload or parameters",
                "request_id": request_id,
                "details": {"errors": errors},
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
        headers = dict(exc.headers or {})
        return JSONResponse(status_code=exc.status_code, content=exc.detail, headers=headers)

    headers = dict(exc.headers or {})
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
        headers=headers,
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Catch-all unhandled server error handler ensuring standard error envelope
    and sanitizing stack traces in non-development environments.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception("Unhandled server exception for request %s: %s", request_id, exc)

    msg = str(exc) if settings.APP_ENV == "development" else "Internal server error"
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": msg,
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


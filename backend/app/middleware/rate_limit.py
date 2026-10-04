"""
Rate limiting middleware and route-level enforcers.

Provides:
1. Global IP rate limiting middleware (skips health check & root endpoints).
2. Scoped rate limit check helpers with standard 429 error envelope and Retry-After header.
3. IP address extraction with proxy header support.
"""

from __future__ import annotations

import logging
from typing import Callable

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import lru_settings
from app.core.rate_limit_store import get_rate_limit_store
from app.security.request_ids import get_request_id

logger = logging.getLogger(__name__)
settings = lru_settings()

# Routes that are never rate limited
UNLIMITED_PATHS = {
    "/",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
}


def get_client_ip(request: Request) -> str:
    """Extract client IP address, checking X-Forwarded-For first hop if present."""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # Take the first IP before comma (client IP)
        ip = forwarded_for.split(",")[0].strip()
        if ip:
            return ip
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


async def enforce_rate_limit(
    scope: str,
    key_identifier: str,
    limit: int,
    request_id: str,
    window_seconds: int = 60,
) -> None:
    """
    Check rate limit for a specific key and scope.
    Raises HTTPException(429) formatted to standard error envelope if exceeded.
    """
    if not settings.RATE_LIMIT_ENABLED or limit <= 0:
        return

    store = get_rate_limit_store()
    rate_key = f"{scope}:{key_identifier}"
    result = await store.check_and_increment(rate_key, limit=limit, window_seconds=window_seconds)

    if not result.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": {
                    "code": "RATE_LIMITED",
                    "message": "Too many requests. Please retry later.",
                    "request_id": request_id,
                    "details": {
                        "retry_after_seconds": result.retry_after_seconds,
                        "limit_scope": scope,
                    },
                }
            },
            headers={"Retry-After": str(result.retry_after_seconds)},
        )


class GlobalRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Enforces a global per-IP request rate limit across all API endpoints.
    Health checks and root info endpoints are strictly exempted.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        path = request.url.path
        if path in UNLIMITED_PATHS or path.startswith(("/docs", "/redoc", "/static")):
            return await call_next(request)

        client_ip = get_client_ip(request)
        request_id = await get_request_id(request)
        store = get_rate_limit_store()

        rate_key = f"ip_global:{client_ip}"
        result = await store.check_and_increment(
            rate_key,
            limit=settings.RL_GLOBAL_IP_PER_MIN,
            window_seconds=60,
        )

        if not result.allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": {
                        "code": "RATE_LIMITED",
                        "message": "Too many requests. Please retry later.",
                        "request_id": request_id,
                        "details": {
                            "retry_after_seconds": result.retry_after_seconds,
                            "limit_scope": "ip_global",
                        },
                    }
                },
                headers={
                    "Retry-After": str(result.retry_after_seconds),
                    "X-Request-ID": request_id,
                },
            )

        response: Response = await call_next(request)
        return response

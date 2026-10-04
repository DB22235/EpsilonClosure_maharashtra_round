"""
Security headers and request payload hardening middleware.

Enforces:
1. Defensive HTTP security headers (nosniff, DENY, no-referrer).
2. Cache-Control: no-store on sensitive/mutating routes.
3. Maximum request body size guard (413 PAYLOAD_TOO_LARGE).
"""

from __future__ import annotations

import logging
from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import lru_settings
from app.security.request_ids import get_request_id

logger = logging.getLogger(__name__)
settings = lru_settings()

# Path prefixes that must never be cached by browsers or proxies
NO_CACHE_PREFIXES = (
    "/api/v1/auth",
    "/api/v1/campaigns",
    "/api/v1/entitlements",
    "/api/v1/admin",
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Applies security headers and enforces request body size limits.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = await get_request_id(request)

        # 1. Payload Size Guard (Check Content-Length header if present)
        content_length_header = request.headers.get("content-length")
        if content_length_header:
            try:
                content_length = int(content_length_header)
                if content_length > settings.MAX_REQUEST_BODY_BYTES:
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={
                            "error": {
                                "code": "PAYLOAD_TOO_LARGE",
                                "message": f"Request body exceeds maximum allowed size of {settings.MAX_REQUEST_BODY_BYTES} bytes",
                                "request_id": request_id,
                                "details": {
                                    "max_bytes": settings.MAX_REQUEST_BODY_BYTES,
                                    "received_bytes": content_length,
                                },
                            }
                        },
                        headers={"X-Request-ID": request_id},
                    )
            except ValueError:
                pass

        # 2. Process Request
        response: Response = await call_next(request)

        # 3. Apply Standard Defensive Headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"

        # 4. Cache-Control for Sensitive Routes
        path = request.url.path
        if any(path.startswith(prefix) for prefix in NO_CACHE_PREFIXES):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"

        return response

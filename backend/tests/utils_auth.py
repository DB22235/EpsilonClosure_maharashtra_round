"""
Authentication test utilities for generating signed JWTs and request headers.
"""

from __future__ import annotations

import time
import uuid

import jwt


def make_jwt(
    sub: str | uuid.UUID,
    email: str | None,
    secret: str,
    audience: str = "authenticated",
    expires_in: int = 3600,
) -> str:
    """
    Generate an HS256-signed Supabase-compatible JWT for testing.
    Asserts subject identity only; roles are resolved database-side.
    """
    now = int(time.time())
    payload = {
        "sub": str(sub),
        "email": email or f"user_{str(sub)[:8]}@test.local",
        "aud": audience,
        "role": "authenticated",
        "iat": now,
        "exp": now + expires_in,
    }
    key = secret or "fair-drop-default-test-jwt-secret-key"
    return jwt.encode(payload, key, algorithm="HS256")


def auth_headers(token: str, request_id: str | None = None) -> dict[str, str]:
    """
    Format headers containing Bearer token and optional X-Request-ID.
    """
    headers = {"Authorization": f"Bearer {token}"}
    if request_id:
        headers["X-Request-ID"] = request_id
    return headers

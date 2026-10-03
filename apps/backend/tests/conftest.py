"""
Pytest configuration and shared fixtures for Fair Drop backend integration tests.
"""

from __future__ import annotations

import logging
import os
import uuid
from collections.abc import AsyncGenerator
from typing import Any

import httpx
import pytest
from httpx import ASGITransport

from app.config import lru_settings
from app.main import app as fastapi_app
from scripts.seed_admin import seed_admin
from tests.utils_auth import auth_headers, make_jwt

logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

# Default stable UUIDs for test users
TEST_USER_UUID = uuid.UUID("22222222-3333-4444-5555-666666666666")
TEST_ADMIN_UUID = uuid.UUID("11111111-2222-3333-4444-555555555555")


def assert_error(resp: httpx.Response, status_code: int, code: str) -> dict[str, Any]:
    """
    Validate standardized Fair Drop API error envelope contract:
    {"error": {"code": ..., "message": ..., "request_id": ..., "details": ...}}
    """
    assert resp.status_code == status_code, (
        f"Expected HTTP {status_code}, got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    assert "error" in body, f"Response missing root 'error' key: {body}"
    err = body["error"]
    assert err.get("code") == code, f"Expected code '{code}', got '{err.get('code')}'"
    assert "message" in err, "Error envelope missing 'message'"
    assert "request_id" in err, "Error envelope missing 'request_id'"
    assert "details" in err, "Error envelope missing 'details'"
    return err


@pytest.fixture
def assert_err():
    """Fixture providing assert_error helper."""
    return assert_error


@pytest.fixture(scope="session")
def app():
    """Provide the FastAPI application instance."""
    return fastapi_app


@pytest.fixture
async def client(app) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provide an async HTTP test client using ASGITransport."""
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
def request_id_header() -> dict[str, str]:
    """Provide a standard X-Request-ID test header."""
    return {"X-Request-ID": "test-req-123"}


@pytest.fixture
def auth_header_user() -> dict[str, str]:
    """
    Provide authorization headers for a standard USER.
    Prefers TEST_USER_JWT env var, otherwise creates a signed test JWT.
    """
    env_token = os.environ.get("TEST_USER_JWT")
    if env_token:
        return auth_headers(env_token)

    settings = lru_settings()
    token = make_jwt(
        sub=TEST_USER_UUID,
        email="test_user@fairdrop.local",
        secret=settings.SUPABASE_JWT_SECRET,
        audience=settings.SUPABASE_JWT_AUDIENCE,
    )
    return auth_headers(token)


@pytest.fixture
async def auth_header_admin() -> dict[str, str]:
    """
    Provide authorization headers for an ADMIN.
    Ensures the profile role is set to ADMIN in the database.
    """
    env_token = os.environ.get("TEST_ADMIN_JWT")
    if env_token:
        # If external token given, ensure profile is admin if possible
        return auth_headers(env_token)

    settings = lru_settings()
    token = make_jwt(
        sub=TEST_ADMIN_UUID,
        email="test_admin@fairdrop.local",
        secret=settings.SUPABASE_JWT_SECRET,
        audience=settings.SUPABASE_JWT_AUDIENCE,
    )

    # Ensure profile role is ADMIN in PostgreSQL
    try:
        await seed_admin(TEST_ADMIN_UUID)
    except Exception as exc:
        pytest.skip(f"Database unavailable for admin seeding: {exc}")

    return auth_headers(token)

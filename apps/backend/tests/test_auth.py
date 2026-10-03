"""
Integration tests for authentication, JIT provisioning, RBAC, and error envelopes.
"""

from __future__ import annotations

import httpx
import pytest

from tests.conftest import assert_error

pytestmark = pytest.mark.asyncio


async def test_auth_me_missing_token(client: httpx.AsyncClient) -> None:
    """GET /api/v1/auth/me without token returns 401 AUTH_REQUIRED."""
    response = await client.get("/api/v1/auth/me")
    assert_error(response, 401, "AUTH_REQUIRED")


async def test_auth_me_garbage_token(client: httpx.AsyncClient) -> None:
    """GET /api/v1/auth/me with garbage token returns 401 INVALID_TOKEN or TOKEN_DECODE_FAILED."""
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-valid-token-string"},
    )
    assert response.status_code == 401
    body = response.json()
    assert "error" in body
    assert body["error"]["code"] in ("INVALID_TOKEN", "TOKEN_DECODE_FAILED")


async def test_auth_me_valid_user(
    client: httpx.AsyncClient,
    auth_header_user: dict[str, str],
) -> None:
    """
    GET /api/v1/auth/me with valid user JWT returns 200 with profile,
    participant, and server_time; profile.role is USER.
    """
    response = await client.get("/api/v1/auth/me", headers=auth_header_user)
    assert response.status_code == 200
    data = response.json()

    assert "profile" in data
    assert "participant" in data
    assert "server_time" in data

    profile = data["profile"]
    assert profile["role"] == "USER"
    assert "id" in profile
    assert profile["email_verified"] is True

    participant = data["participant"]
    assert "id" in participant
    assert participant["account_id"] == profile["id"]
    assert participant["verification_status"] == "PENDING"


async def test_auth_me_jit_idempotent(
    client: httpx.AsyncClient,
    auth_header_user: dict[str, str],
) -> None:
    """Second GET /api/v1/auth/me with same JWT returns identical profile.id and participant.id."""
    res1 = await client.get("/api/v1/auth/me", headers=auth_header_user)
    assert res1.status_code == 200
    data1 = res1.json()

    res2 = await client.get("/api/v1/auth/me", headers=auth_header_user)
    assert res2.status_code == 200
    data2 = res2.json()

    assert data1["profile"]["id"] == data2["profile"]["id"]
    assert data1["participant"]["id"] == data2["participant"]["id"]


async def test_auth_me_admin_user_forbidden(
    client: httpx.AsyncClient,
    auth_header_user: dict[str, str],
) -> None:
    """GET /api/v1/auth/me/admin with regular user JWT returns 403 FORBIDDEN."""
    response = await client.get("/api/v1/auth/me/admin", headers=auth_header_user)
    assert_error(response, 403, "FORBIDDEN")


async def test_auth_me_admin_success(
    client: httpx.AsyncClient,
    auth_header_admin: dict[str, str],
) -> None:
    """GET /api/v1/auth/me/admin with admin JWT (profiles.role=ADMIN) returns 200."""
    response = await client.get("/api/v1/auth/me/admin", headers=auth_header_admin)
    assert response.status_code == 200
    data = response.json()
    assert data.get("role") == "ADMIN"
    assert "id" in data


async def test_error_envelope_request_id(client: httpx.AsyncClient) -> None:
    """Error response includes request_id from X-Request-ID when provided."""
    custom_trace_id = "test-custom-trace-err-444"
    response = await client.get(
        "/api/v1/auth/me",
        headers={"X-Request-ID": custom_trace_id},
    )
    assert response.status_code == 401
    body = response.json()
    assert "error" in body
    assert body["error"]["request_id"] == custom_trace_id


async def test_invalid_auth_scheme(client: httpx.AsyncClient) -> None:
    """Authorization scheme must be Bearer; malformed auth fails safely with 401 AUTH_REQUIRED."""
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Basic dXNlcjpwYXNzd29yZA=="},
    )
    assert_error(response, 401, "AUTH_REQUIRED")

"""
Tests for Rate Limiting, Security Headers, Input Hardening, and Idempotent Abuse Resistance.
"""

from __future__ import annotations

import uuid
import httpx
import pytest

from app.config import lru_settings
from app.core.rate_limit_store import get_rate_limit_store
from tests.test_registration import _create_open_campaign

pytestmark = pytest.mark.asyncio
settings = lru_settings()


@pytest.fixture(autouse=True)
async def reset_rate_limiter():
    """Reset the in-memory rate limiter store before and after each test."""
    store = get_rate_limit_store()
    await store.reset()
    yield
    await store.reset()


async def test_security_headers_present(client: httpx.AsyncClient) -> None:
    """Ensure defensive security headers are returned on API responses."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"
    assert resp.headers.get("referrer-policy") == "no-referrer"

    # Test cache-control on sensitive endpoints
    resp_api = await client.get("/api/v1/campaigns")
    assert resp_api.status_code == 200
    assert "no-store" in resp_api.headers.get("cache-control", "")


async def test_payload_too_large_rejected(client: httpx.AsyncClient) -> None:
    """Request body exceeding MAX_REQUEST_BODY_BYTES must be rejected with 413 PAYLOAD_TOO_LARGE."""
    oversized_body = "x" * 70000  # > 64KB (65536 bytes)
    resp = await client.post(
        f"/api/v1/campaigns/{uuid.uuid4()}/join",
        content=oversized_body,
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 413
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "PAYLOAD_TOO_LARGE"
    assert "max_bytes" in data["error"]["details"]


async def test_missing_idempotency_key_rejected(
    client: httpx.AsyncClient,
    auth_header_user: dict[str, str],
) -> None:
    """Mutating endpoints without Idempotency-Key must return 400 with IDEMPOTENCY_KEY_REQUIRED."""
    camp_id = uuid.uuid4()
    resp = await client.post(
        f"/api/v1/campaigns/{camp_id}/register",
        json={"admission_token": "valid_token_example", "nonce": "1234567890123456"},
        headers=auth_header_user,  # Omits Idempotency-Key
    )
    assert resp.status_code == 400
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"


async def test_health_never_rate_limited(client: httpx.AsyncClient) -> None:
    """Health check endpoints must never be throttled even under high request volume."""
    for _ in range(30):
        resp = await client.get("/health")
        assert resp.status_code == 200

    resp_root = await client.get("/")
    assert resp_root.status_code == 200


async def test_route_rate_limiting_triggers_429(
    client: httpx.AsyncClient,
    auth_header_user: dict[str, str],
    auth_header_admin: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bursting an endpoint beyond its limit must return 429 RATE_LIMITED with Retry-After header."""
    monkeypatch.setattr(settings, "RL_JOIN_PER_MIN", 3)
    camp_id = await _create_open_campaign(client, auth_header_admin)

    store = get_rate_limit_store()
    await store.reset()

    last_resp = None
    for _ in range(5):
        last_resp = await client.post(
            f"/api/v1/campaigns/{camp_id}/join",
            headers=auth_header_user,
        )
        if last_resp.status_code == 429:
            break

    assert last_resp is not None
    assert last_resp.status_code == 429
    data = last_resp.json()
    assert "error" in data
    assert data["error"]["code"] == "RATE_LIMITED"
    assert "retry_after_seconds" in data["error"]["details"]
    assert "Retry-After" in last_resp.headers


async def test_idempotent_replay_bypasses_rate_limit(
    client: httpx.AsyncClient,
    auth_header_user: dict[str, str],
    auth_header_admin: dict[str, str],
) -> None:
    """Legitimate idempotent retries with matching payload must succeed even if rate limiter is full."""
    camp_id = await _create_open_campaign(client, auth_header_admin)

    # Obtain admission permit
    join_resp = await client.post(
        f"/api/v1/campaigns/{camp_id}/join",
        headers=auth_header_user,
    )
    assert join_resp.status_code == 201
    permit_data = join_resp.json()

    idemp_key = f"key-{uuid.uuid4()}"
    reg_payload = {
        "admission_token": permit_data["admission_token"],
        "nonce": permit_data["nonce"],
        "client_meta": {"ip": "127.0.0.1"},
    }
    headers = {**auth_header_user, "Idempotency-Key": idemp_key}

    # First registration
    first_resp = await client.post(
        f"/api/v1/campaigns/{camp_id}/register",
        json=reg_payload,
        headers=headers,
    )
    assert first_resp.status_code == 201

    # Replaying with same key and body returns cached 200 repeatedly without 429
    for _ in range(3):
        replay_resp = await client.post(
            f"/api/v1/campaigns/{camp_id}/register",
            json=reg_payload,
            headers=headers,
        )
        assert replay_resp.status_code == 200
        assert replay_resp.json()["registration_id"] == first_resp.json()["registration_id"]

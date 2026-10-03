"""
Integration tests for service health, root endpoint, and X-Request-ID middleware.
"""

from __future__ import annotations

import httpx
import pytest

pytestmark = pytest.mark.asyncio


async def test_root_endpoint(client: httpx.AsyncClient) -> None:
    """GET / returns 200 and service=fair-drop."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data.get("service") == "fair-drop"
    assert data.get("status") == "running"
    assert "version" in data


async def test_health_endpoint(client: httpx.AsyncClient) -> None:
    """GET /health returns 200, status=healthy, and timestamp."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "healthy"
    assert "timestamp" in data


async def test_request_id_echoed(client: httpx.AsyncClient) -> None:
    """X-Request-ID sent by client is echoed in the response headers."""
    custom_req_id = "test-custom-trace-987"
    response = await client.get("/health", headers={"X-Request-ID": custom_req_id})
    assert response.status_code == 200
    # Case-insensitive header lookup in httpx
    assert response.headers.get("x-request-id") == custom_req_id


async def test_request_id_auto_generated(client: httpx.AsyncClient) -> None:
    """If client omits X-Request-ID, server returns an auto-generated x-request-id header."""
    response = await client.get("/health")
    assert response.status_code == 200
    req_id = response.headers.get("x-request-id")
    assert req_id is not None
    assert req_id.startswith("req_")

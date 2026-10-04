"""
Operational smoke test verifying API Rate Limiting, 429 Envelope, and Retry-After headers.

Usage:
    python -m scripts.test_rate_limits
    python -m scripts.test_rate_limits --in-process
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
import httpx

from app.config import lru_settings
from app.core.rate_limit_store import get_rate_limit_store
from app.main import app
from tests.utils_auth import auth_headers, make_jwt

settings = lru_settings()


async def run_tests(client: httpx.AsyncClient) -> bool:
    print("=" * 65)
    print("🚦 FAIR DROP SMOKE TEST: Rate Limiting & Abuse Hardening")
    print("=" * 65)

    passed = 0
    total = 0

    def assert_check(name: str, condition: bool, details: str = ""):
        nonlocal passed, total
        total += 1
        if condition:
            passed += 1
            print(f"  ✅ [PASS] {name}")
        else:
            print(f"  ❌ [FAIL] {name} — {details}")

    # Generate test tokens
    test_sub = uuid.uuid4()
    participant_token = make_jwt(
        sub=test_sub,
        email="ratelimit_tester@fairdrop.local",
        secret=settings.SUPABASE_JWT_SECRET or "fair-drop-default-test-jwt-secret-key",
        audience=settings.SUPABASE_JWT_AUDIENCE,
    )
    headers = {
        **auth_headers(participant_token),
        "Content-Type": "application/json",
    }

    # Reset store for clean test baseline
    store = get_rate_limit_store()
    await store.reset()

    # 1. Health check is available
    res_health = await client.get("/health")
    assert_check("Health endpoint returns 200", res_health.status_code == 200)

    # 2. Warm up test identity with one request first
    warm_res = await client.get("/api/v1/auth/me", headers=headers)
    assert_check("Initial authenticated request succeeds (200)", warm_res.status_code == 200)

    # 3. Burst requests concurrently against /api/v1/auth/me (limit 120/min)
    print(f"\n[1] Firing burst of 130 concurrent requests on /api/v1/auth/me...")
    tasks = [client.get("/api/v1/auth/me", headers=headers) for _ in range(130)]
    responses = await asyncio.gather(*tasks)

    hit_429 = any(r.status_code == 429 for r in responses)
    resp_429 = next((r for r in responses if r.status_code == 429), None)

    assert_check("Exceeding limit triggers HTTP 429", hit_429)

    retry_header_val = resp_429.headers.get("retry-after") if resp_429 else None
    assert_check(
        "429 contains Retry-After header",
        retry_header_val is not None and int(retry_header_val) > 0,
        f"Got Retry-After: {retry_header_val}",
    )

    rate_limit_envelope = resp_429.json() if resp_429 else {}
    assert_check(
        "429 uses standard error envelope with RATE_LIMITED code",
        rate_limit_envelope.get("error", {}).get("code") == "RATE_LIMITED"
        and "retry_after_seconds" in rate_limit_envelope.get("error", {}).get("details", {}),
    )

    # 4. Health check remains 200 even after rate limit triggered on API
    res_health_after = await client.get("/health")
    assert_check("Health check remains 200 during/after 429 throttle", res_health_after.status_code == 200)

    # 5. Root info remains 200
    res_root = await client.get("/")
    assert_check("Root endpoint remains 200", res_root.status_code == 200)

    # 6. Single path recovers after limiter reset
    await store.reset()
    res_recovery = await client.get("/api/v1/auth/me", headers=headers)
    assert_check("Legitimate single-path flow succeeds after window reset", res_recovery.status_code == 200)

    # Summary
    print("\n" + "=" * 65)
    print(f"RESULTS: {passed}/{total} checks passed")
    print("=" * 65)
    return passed == total


async def main():
    parser = argparse.ArgumentParser(description="Test rate limits")
    parser.add_argument("--in-process", action="store_true", default=True, help="Run in-process using httpx.ASGITransport")
    args = parser.parse_args()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        success = await run_tests(client)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

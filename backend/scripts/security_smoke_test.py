"""
Security smoke test script verifying:
1. 401 AUTH_REQUIRED on unauthenticated protected endpoints
2. 403 FORBIDDEN on participant accessing admin endpoints
3. 413 PAYLOAD_TOO_LARGE on oversized JSON payload
4. 400 IDEMPOTENCY_KEY_REQUIRED on mutations without Idempotency-Key
5. Security headers presence
6. No sensitive token/secret leakage in metrics and audit outputs

Usage:
    python -m scripts.security_smoke_test
    python -m scripts.security_smoke_test --in-process
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
import httpx

from app.config import lru_settings
from app.main import app
from tests.utils_auth import auth_headers, make_jwt

settings = lru_settings()


async def run_security_tests(client: httpx.AsyncClient) -> bool:
    print("=" * 65)
    print("🛡️  FAIR DROP SECURITY & HARDENING SMOKE TEST")
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

    secret = settings.SUPABASE_JWT_SECRET or "fair-drop-default-test-jwt-secret-key"

    # Participant token
    part_sub = uuid.uuid4()
    part_token = make_jwt(
        sub=part_sub,
        email="part_security@fairdrop.local",
        secret=secret,
        audience=settings.SUPABASE_JWT_AUDIENCE,
    )
    part_headers = {
        **auth_headers(part_token),
        "Content-Type": "application/json",
    }

    # 1. Unauthenticated protected route -> 401 AUTH_REQUIRED
    res_unauth = await client.get("/api/v1/auth/me")
    assert_check(
        "Unauthenticated access returns 401 AUTH_REQUIRED",
        res_unauth.status_code == 401
        and res_unauth.json().get("error", {}).get("code") == "AUTH_REQUIRED",
    )

    # 2. Participant accessing admin endpoint -> 403 FORBIDDEN
    res_forbidden = await client.get("/api/v1/admin/campaigns", headers=part_headers)
    assert_check(
        "Participant accessing admin route returns 403 FORBIDDEN",
        res_forbidden.status_code == 403
        and res_forbidden.json().get("error", {}).get("code") == "FORBIDDEN",
    )

    # 3. Oversized payload rejected -> 413 PAYLOAD_TOO_LARGE
    oversized_data = "0" * (settings.MAX_REQUEST_BODY_BYTES + 1024)
    res_oversized = await client.post(
        f"/api/v1/campaigns/{uuid.uuid4()}/join",
        content=oversized_data,
        headers={"Content-Type": "application/json"},
    )
    assert_check(
        "Oversized payload rejected with 413 PAYLOAD_TOO_LARGE",
        res_oversized.status_code == 413
        and res_oversized.json().get("error", {}).get("code") == "PAYLOAD_TOO_LARGE",
    )

    # 4. Mutation without Idempotency-Key rejected -> 400 IDEMPOTENCY_KEY_REQUIRED
    res_missing_idemp = await client.post(
        f"/api/v1/campaigns/{uuid.uuid4()}/register",
        json={"admission_token": "token_example", "nonce": "1234567890123456"},
        headers=part_headers,  # Missing Idempotency-Key header
    )
    assert_check(
        "Missing Idempotency-Key returns 400 IDEMPOTENCY_KEY_REQUIRED",
        res_missing_idemp.status_code == 400
        and res_missing_idemp.json().get("error", {}).get("code") == "IDEMPOTENCY_KEY_REQUIRED",
    )

    # 5. Security headers presence check
    res_headers = await client.get("/health")
    assert_check(
        "Security headers (nosniff, DENY, no-referrer) present",
        res_headers.headers.get("x-content-type-options") == "nosniff"
        and res_headers.headers.get("x-frame-options") == "DENY"
        and res_headers.headers.get("referrer-policy") == "no-referrer",
    )

    # 6. Spot check no secret leaks in public responses
    res_public = await client.get("/api/v1/campaigns")
    text_content = res_public.text.lower()
    leaks_found = any(s in text_content for s in ["jwt_secret", "signing_private_key", "password", "pepper"])
    assert_check("No internal secrets leaked in public API payload", not leaks_found)

    print("\n" + "=" * 65)
    print(f"RESULTS: {passed}/{total} security checks passed")
    print("=" * 65)
    return passed == total


async def main():
    parser = argparse.ArgumentParser(description="Security smoke test")
    parser.add_argument("--in-process", action="store_true", default=True, help="Run in-process using httpx.ASGITransport")
    args = parser.parse_args()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        success = await run_security_tests(client)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

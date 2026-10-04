"""
Integration tests for Seat Hold, Booking Redemption, and Hold Release (Step 8).
"""

from __future__ import annotations

import uuid

import httpx
import pytest

from tests.conftest import assert_error
from tests.test_lottery import _create_open_campaign_with_registration

pytestmark = pytest.mark.asyncio


async def _setup_drawn_campaign_with_winner(
    client: httpx.AsyncClient,
    auth_header_admin: dict[str, str],
    auth_header_user: dict[str, str],
) -> tuple[str, str]:
    """Helper to create campaign, register user, freeze, draw lottery, and return (camp_id, entitlement_id)."""
    camp_id = await _create_open_campaign_with_registration(client, auth_header_admin, auth_header_user)

    # Admin freezes roster
    res_freeze = await client.post(
        f"/api/v1/admin/campaigns/{camp_id}/freeze",
        headers=auth_header_admin,
    )
    assert res_freeze.status_code == 200

    # Admin executes draw
    res_draw = await client.post(
        f"/api/v1/admin/campaigns/{camp_id}/draw",
        headers=auth_header_admin,
        json={"randomness_seed": "0123456789abcdef0123456789abcdef"},
    )
    assert res_draw.status_code == 200

    # User fetches result
    res_result = await client.get(
        f"/api/v1/campaigns/{camp_id}/result",
        headers=auth_header_user,
    )
    assert res_result.status_code == 200
    res_data = res_result.json()
    assert res_data["status"] == "WON"
    entitlement_id = res_data["entitlement_id"]
    assert entitlement_id is not None

    return camp_id, entitlement_id


async def test_hold_missing_idempotency_key(
    client: httpx.AsyncClient,
    auth_header_admin: dict[str, str],
    auth_header_user: dict[str, str],
) -> None:
    """Holding seat without Idempotency-Key header returns 400."""
    camp_id, entitlement_id = await _setup_drawn_campaign_with_winner(
        client, auth_header_admin, auth_header_user
    )

    res = await client.post(
        f"/api/v1/entitlements/{camp_id}/hold",
        headers=auth_header_user,
        json={"entitlement_token": entitlement_id},
    )
    assert_error(res, 400, "IDEMPOTENCY_KEY_REQUIRED")


async def test_hold_invalid_token(
    client: httpx.AsyncClient,
    auth_header_admin: dict[str, str],
    auth_header_user: dict[str, str],
) -> None:
    """Holding seat with non-existent entitlement token returns 404."""
    camp_id, _ = await _setup_drawn_campaign_with_winner(
        client, auth_header_admin, auth_header_user
    )

    fake_token = str(uuid.uuid4())
    res = await client.post(
        f"/api/v1/entitlements/{camp_id}/hold",
        headers={**auth_header_user, "Idempotency-Key": f"hold-test-{uuid.uuid4().hex}"},
        json={"entitlement_token": fake_token},
    )
    assert_error(res, 404, "ENTITLEMENT_NOT_FOUND")


async def test_hold_and_redeem_workflow(
    client: httpx.AsyncClient,
    auth_header_admin: dict[str, str],
    auth_header_user: dict[str, str],
) -> None:
    """Full journey: hold seat, idempotent replay, redeem booking, idempotent replay, and replay attack prevention."""
    camp_id, entitlement_id = await _setup_drawn_campaign_with_winner(
        client, auth_header_admin, auth_header_user
    )

    hold_key = f"hold-key-{uuid.uuid4().hex}"

    # 1. Hold seat
    res_hold = await client.post(
        f"/api/v1/entitlements/{camp_id}/hold",
        headers={**auth_header_user, "Idempotency-Key": hold_key},
        json={"entitlement_token": entitlement_id},
    )
    assert res_hold.status_code == 200
    hold_data = res_hold.json()
    assert hold_data["seat_id"] is not None
    assert "hold_expires_at" in hold_data
    seat_id = hold_data["seat_id"]

    # 2. Idempotent replay of hold
    res_hold_dup = await client.post(
        f"/api/v1/entitlements/{camp_id}/hold",
        headers={**auth_header_user, "Idempotency-Key": hold_key},
        json={"entitlement_token": entitlement_id},
    )
    assert res_hold_dup.status_code == 200
    assert res_hold_dup.json()["seat_id"] == seat_id

    # 3. Redeem booking
    redeem_key = f"redeem-key-{uuid.uuid4().hex}"
    res_redeem = await client.post(
        f"/api/v1/entitlements/{camp_id}/redeem",
        headers={**auth_header_user, "Idempotency-Key": redeem_key},
        json={"entitlement_token": entitlement_id, "seat_id": seat_id},
    )
    assert res_redeem.status_code == 201
    redeem_data = res_redeem.json()
    assert redeem_data["booking_id"] is not None
    assert redeem_data["receipt_id"] is not None
    assert redeem_data["seat_id"] == seat_id

    # 4. Idempotent replay of redeem
    res_redeem_dup = await client.post(
        f"/api/v1/entitlements/{camp_id}/redeem",
        headers={**auth_header_user, "Idempotency-Key": redeem_key},
        json={"entitlement_token": entitlement_id, "seat_id": seat_id},
    )
    assert res_redeem_dup.status_code in (200, 201)
    assert res_redeem_dup.json()["receipt_id"] == redeem_data["receipt_id"]

    # 5. Replay attack with new idempotency key on consumed entitlement -> 409
    res_replayed = await client.post(
        f"/api/v1/entitlements/{camp_id}/redeem",
        headers={**auth_header_user, "Idempotency-Key": f"redeem-new-{uuid.uuid4().hex}"},
        json={"entitlement_token": entitlement_id, "seat_id": seat_id},
    )
    assert_error(res_replayed, 409, "ENTITLEMENT_REPLAYED")


async def test_hold_release_workflow(
    client: httpx.AsyncClient,
    auth_header_admin: dict[str, str],
    auth_header_user: dict[str, str],
) -> None:
    """Holding a seat and subsequently releasing it makes it available again."""
    camp_id, entitlement_id = await _setup_drawn_campaign_with_winner(
        client, auth_header_admin, auth_header_user
    )

    hold_key = f"hold-rel-{uuid.uuid4().hex}"

    # 1. Hold seat
    res_hold = await client.post(
        f"/api/v1/entitlements/{camp_id}/hold",
        headers={**auth_header_user, "Idempotency-Key": hold_key},
        json={"entitlement_token": entitlement_id},
    )
    assert res_hold.status_code == 200
    seat_id = res_hold.json()["seat_id"]

    # 2. Release hold
    res_release = await client.post(
        f"/api/v1/entitlements/{camp_id}/release",
        headers=auth_header_user,
        json={"entitlement_token": entitlement_id, "seat_id": seat_id},
    )
    assert res_release.status_code == 200
    assert res_release.json()["status"] == "RELEASED"


async def test_redeem_without_hold_fails(
    client: httpx.AsyncClient,
    auth_header_admin: dict[str, str],
    auth_header_user: dict[str, str],
) -> None:
    """Attempting to redeem a seat that was never held returns 409 SEAT_NOT_HELD."""
    camp_id, entitlement_id = await _setup_drawn_campaign_with_winner(
        client, auth_header_admin, auth_header_user
    )

    unheld_seat_id = str(uuid.uuid4())
    res = await client.post(
        f"/api/v1/entitlements/{camp_id}/redeem",
        headers={**auth_header_user, "Idempotency-Key": f"redeem-unheld-{uuid.uuid4().hex}"},
        json={"entitlement_token": entitlement_id, "seat_id": unheld_seat_id},
    )
    assert_error(res, 409, "SEAT_NOT_HELD")


async def test_hold_when_redemption_paused(
    client: httpx.AsyncClient,
    auth_header_admin: dict[str, str],
    auth_header_user: dict[str, str],
) -> None:
    """Holding a seat when operator has paused REDEMPTION scope returns 409 CAMPAIGN_PAUSED."""
    camp_id, entitlement_id = await _setup_drawn_campaign_with_winner(
        client, auth_header_admin, auth_header_user
    )

    # Admin pauses redemption
    res_pause = await client.post(
        f"/api/v1/admin/campaigns/{camp_id}/pause",
        headers=auth_header_admin,
        json={"scope": "REDEMPTION", "reason": "Operational inventory audit"},
    )
    assert res_pause.status_code == 200

    # User attempts to hold seat
    res_hold = await client.post(
        f"/api/v1/entitlements/{camp_id}/hold",
        headers={**auth_header_user, "Idempotency-Key": f"hold-paused-{uuid.uuid4().hex}"},
        json={"entitlement_token": entitlement_id},
    )
    assert_error(res_hold, 409, "CAMPAIGN_PAUSED")


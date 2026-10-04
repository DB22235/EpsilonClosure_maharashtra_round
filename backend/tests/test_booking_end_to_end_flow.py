import pytest
import uuid
import httpx
from datetime import datetime, timedelta, timezone

from tests.test_entitlements import _setup_drawn_campaign_with_winner

pytestmark = pytest.mark.asyncio

async def test_full_booking_lifecycle_end_to_end(
    client: httpx.AsyncClient,
    auth_header_admin: dict[str, str],
    auth_header_user: dict[str, str],
):
    # 1. Setup campaign with winner
    camp_id, entitlement_id = await _setup_drawn_campaign_with_winner(
        client, auth_header_admin, auth_header_user
    )

    # 2. Test GET /campaigns/{id}/seats to fetch real PostgreSQL seats
    seats_res = await client.get(f"/api/v1/campaigns/{camp_id}/seats")
    assert seats_res.status_code == 200
    seat_data = seats_res.json()
    assert seat_data["total_seats"] > 0
    assert seat_data["available_seats"] > 0
    first_seat = seat_data["seats"][0]
    target_seat_id = first_seat["id"]
    assert first_seat["status"] == "AVAILABLE"

    # 3. Hold target seat
    idemp_hold = f"idemp_hold_{uuid.uuid4().hex}"
    hold_res = await client.post(
        f"/api/v1/entitlements/{camp_id}/hold",
        headers={**auth_header_user, "Idempotency-Key": idemp_hold},
        json={
            "entitlement_token": entitlement_id,
            "seat_id": target_seat_id,
            "hold_duration_seconds": 900,
        },
    )
    assert hold_res.status_code == 200, f"Hold failed: {hold_res.text}"
    hold_body = hold_res.json()
    assert hold_body["seat_id"] == target_seat_id
    assert "successfully held" in hold_body["message"].lower()

    # 4. Check seat map reflects held state
    seats_res2 = await client.get(f"/api/v1/campaigns/{camp_id}/seats")
    seat_data2 = seats_res2.json()
    assert seat_data2["held_seats"] == 1
    held_seat = next(s for s in seat_data2["seats"] if s["id"] == target_seat_id)
    assert held_seat["status"] == "HELD"

    # 5. Redeem entitlement and confirm booking
    idemp_redeem = f"idemp_redeem_{uuid.uuid4().hex}"
    redeem_res = await client.post(
        f"/api/v1/entitlements/{camp_id}/redeem",
        headers={**auth_header_user, "Idempotency-Key": idemp_redeem},
        json={
            "entitlement_token": entitlement_id,
            "seat_id": target_seat_id,
        },
    )
    assert redeem_res.status_code == 201, f"Redeem failed: {redeem_res.text}"
    redeem_body = redeem_res.json()
    assert redeem_body["seat_id"] == target_seat_id
    assert redeem_body["booking_id"] is not None
    assert "receipt_id" in redeem_body and bool(redeem_body["receipt_id"])

    # 6. Idempotent replay: Replaying same redeem returns cached 201 with identical receipt
    replay_res = await client.post(
        f"/api/v1/entitlements/{camp_id}/redeem",
        headers={**auth_header_user, "Idempotency-Key": idemp_redeem},
        json={
            "entitlement_token": entitlement_id,
            "seat_id": target_seat_id,
        },
    )
    assert replay_res.status_code == 201
    assert replay_res.json()["receipt_id"] == redeem_body["receipt_id"]

    # 7. Seat map reflects that the seat is now CONFIRMED
    seats_res3 = await client.get(f"/api/v1/campaigns/{camp_id}/seats")
    seat_data3 = seats_res3.json()
    assert seat_data3["confirmed_seats"] == 1
    assert seat_data3["held_seats"] == 0
    confirmed_seat = next(s for s in seat_data3["seats"] if s["id"] == target_seat_id)
    assert confirmed_seat["status"] == "CONFIRMED"

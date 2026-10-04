"""
Integration tests for Roster Freeze, Lottery Draw, and Participant Results.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from tests.conftest import assert_error
from tests.test_campaigns import _valid_campaign_payload

pytestmark = pytest.mark.asyncio


async def _create_open_campaign_with_registration(
    client: httpx.AsyncClient,
    auth_header_admin: dict[str, str],
    auth_header_user: dict[str, str],
) -> str:
    """Helper to create OPEN campaign and register a test user."""
    res_create = await client.post(
        "/api/v1/admin/campaigns",
        json=_valid_campaign_payload(),
        headers=auth_header_admin,
    )
    assert res_create.status_code == 201
    camp_id = res_create.json()["id"]

    res_prep = await client.post(
        f"/api/v1/admin/campaigns/{camp_id}/prepare",
        headers=auth_header_admin,
    )
    assert res_prep.status_code == 200

    res_open = await client.post(
        f"/api/v1/admin/campaigns/{camp_id}/publish",
        headers=auth_header_admin,
    )
    assert res_open.status_code == 200

    # User joins and registers
    res_join = await client.post(
        f"/api/v1/campaigns/{camp_id}/join",
        headers=auth_header_user,
    )
    assert res_join.status_code == 201
    join_data = res_join.json()

    res_reg = await client.post(
        f"/api/v1/campaigns/{camp_id}/register",
        headers={**auth_header_user, "Idempotency-Key": f"lottery-test-{uuid.uuid4().hex}"},
        json={"admission_token": join_data["admission_token"], "nonce": join_data["nonce"]},
    )
    assert res_reg.status_code in (200, 201)

    return camp_id


async def test_freeze_roster_unauthorized(client: httpx.AsyncClient, auth_header_user: dict[str, str]) -> None:
    """Non-admin user cannot freeze roster -> 403 FORBIDDEN."""
    fake_id = str(uuid.uuid4())
    res = await client.post(f"/api/v1/admin/campaigns/{fake_id}/freeze", headers=auth_header_user)
    assert_error(res, 403, "FORBIDDEN")


async def test_freeze_roster_success(
    client: httpx.AsyncClient,
    auth_header_admin: dict[str, str],
    auth_header_user: dict[str, str],
) -> None:
    """Admin freezes open campaign -> 200 OK with FROZEN status and roster_count >= 1."""
    camp_id = await _create_open_campaign_with_registration(client, auth_header_admin, auth_header_user)

    res_freeze = await client.post(
        f"/api/v1/admin/campaigns/{camp_id}/freeze",
        headers=auth_header_admin,
    )
    assert res_freeze.status_code == 200
    data = res_freeze.json()
    assert data["campaign_id"] == camp_id
    assert data["status"] == "FROZEN"
    assert data["roster_count"] >= 1


async def test_draw_unfrozen_campaign_conflict(
    client: httpx.AsyncClient,
    auth_header_admin: dict[str, str],
) -> None:
    """Admin cannot draw an unfrozen campaign -> 409 INVALID_STATE_TRANSITION."""
    res_create = await client.post(
        "/api/v1/admin/campaigns",
        json=_valid_campaign_payload(),
        headers=auth_header_admin,
    )
    camp_id = res_create.json()["id"]

    res_draw = await client.post(
        f"/api/v1/admin/campaigns/{camp_id}/draw",
        headers=auth_header_admin,
        json={},
    )
    assert_error(res_draw, 409, "INVALID_STATE_TRANSITION")


async def test_lottery_draw_and_result_flow(
    client: httpx.AsyncClient,
    auth_header_admin: dict[str, str],
    auth_header_user: dict[str, str],
) -> None:
    """Full lifecycle: Register -> Result before draw -> Freeze -> Draw -> Result after draw -> Double Draw 409."""
    camp_id = await _create_open_campaign_with_registration(client, auth_header_admin, auth_header_user)

    # 1. Result before draw
    res_result_pre = await client.get(
        f"/api/v1/campaigns/{camp_id}/result",
        headers=auth_header_user,
    )
    assert res_result_pre.status_code == 200
    data_pre = res_result_pre.json()
    assert data_pre["status"] == "PENDING_DRAW"
    assert data_pre["is_winner"] is False

    # 2. Freeze roster
    res_freeze = await client.post(
        f"/api/v1/admin/campaigns/{camp_id}/freeze",
        headers=auth_header_admin,
    )
    assert res_freeze.status_code == 200

    # 3. Draw lottery
    test_seed = "0123456789abcdef0123456789abcdef"
    res_draw = await client.post(
        f"/api/v1/admin/campaigns/{camp_id}/draw",
        headers=auth_header_admin,
        json={"randomness_seed": test_seed},
    )
    assert res_draw.status_code == 200
    draw_data = res_draw.json()
    assert draw_data["seed"] == test_seed
    assert "seed_hash" in draw_data
    assert draw_data["total_eligible"] >= 1
    assert draw_data["total_winners"] >= 1

    # 4. Result after draw -> WON
    res_result_post = await client.get(
        f"/api/v1/campaigns/{camp_id}/result",
        headers=auth_header_user,
    )
    assert res_result_post.status_code == 200
    data_post = res_result_post.json()
    assert data_post["status"] == "WON"
    assert data_post["is_winner"] is True
    assert data_post["rank"] == 1
    assert data_post["entitlement_id"] is not None
    assert data_post["entitlement_status"] == "SELECTED"

    # 5. Double Draw conflict -> 409
    res_draw2 = await client.post(
        f"/api/v1/admin/campaigns/{camp_id}/draw",
        headers=auth_header_admin,
        json={},
    )
    assert res_draw2.status_code == 409

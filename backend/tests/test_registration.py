"""
Integration tests for Campaign Join, Admission Permits, and Idempotent Registration.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from tests.conftest import assert_error
from tests.test_campaigns import _valid_campaign_payload

pytestmark = pytest.mark.asyncio


async def _create_open_campaign(
    client: httpx.AsyncClient,
    auth_header_admin: dict[str, str],
) -> str:
    """Helper to create and transition a campaign from DRAFT -> PREPARING -> OPEN."""
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
    return camp_id


async def test_join_unauthenticated(client: httpx.AsyncClient) -> None:
    """POST /campaigns/{id}/join without auth returns 401 AUTH_REQUIRED."""
    camp_id = str(uuid.uuid4())
    res = await client.post(f"/api/v1/campaigns/{camp_id}/join")
    assert_error(res, 401, "AUTH_REQUIRED")


async def test_join_nonexistent_campaign(
    client: httpx.AsyncClient,
    auth_header_user: dict[str, str],
) -> None:
    """POST /campaigns/{id}/join with nonexistent campaign returns 404 CAMPAIGN_NOT_FOUND."""
    fake_id = str(uuid.uuid4())
    res = await client.post(f"/api/v1/campaigns/{fake_id}/join", headers=auth_header_user)
    assert_error(res, 404, "CAMPAIGN_NOT_FOUND")


async def test_join_draft_campaign(
    client: httpx.AsyncClient,
    auth_header_admin: dict[str, str],
    auth_header_user: dict[str, str],
) -> None:
    """POST /campaigns/{id}/join on DRAFT campaign returns 409 REGISTRATION_NOT_STARTED."""
    res_create = await client.post(
        "/api/v1/admin/campaigns",
        json=_valid_campaign_payload(),
        headers=auth_header_admin,
    )
    draft_id = res_create.json()["id"]

    res = await client.post(f"/api/v1/campaigns/{draft_id}/join", headers=auth_header_user)
    assert_error(res, 409, "REGISTRATION_NOT_STARTED")


async def test_join_open_campaign_success(
    client: httpx.AsyncClient,
    auth_header_admin: dict[str, str],
    auth_header_user: dict[str, str],
) -> None:
    """POST /campaigns/{id}/join on OPEN campaign returns 201 with signed permit."""
    camp_id = await _create_open_campaign(client, auth_header_admin)

    res = await client.post(f"/api/v1/campaigns/{camp_id}/join", headers=auth_header_user)
    assert res.status_code == 201
    data = res.json()

    assert "permit_id" in data
    assert "admission_token" in data
    assert "nonce" in data
    assert len(data["nonce"]) == 32
    assert data["campaign_id"] == camp_id


async def test_register_missing_idempotency_key(
    client: httpx.AsyncClient,
    auth_header_admin: dict[str, str],
    auth_header_user: dict[str, str],
) -> None:
    """POST /campaigns/{id}/register without Idempotency-Key header returns 400 IDEMPOTENCY_KEY_REQUIRED."""
    camp_id = await _create_open_campaign(client, auth_header_admin)

    res = await client.post(
        f"/api/v1/campaigns/{camp_id}/register",
        json={"admission_token": "token", "nonce": "dummy_nonce_min_length_16"},
        headers=auth_header_user,
    )
    assert_error(res, 400, "IDEMPOTENCY_KEY_REQUIRED")


async def test_register_forged_permit(
    client: httpx.AsyncClient,
    auth_header_admin: dict[str, str],
    auth_header_user: dict[str, str],
) -> None:
    """POST /campaigns/{id}/register with forged permit token returns 403 ADMISSION_REQUIRED."""
    camp_id = await _create_open_campaign(client, auth_header_admin)

    headers = {**auth_header_user, "Idempotency-Key": f"key-{uuid.uuid4().hex}"}
    res = await client.post(
        f"/api/v1/campaigns/{camp_id}/register",
        json={"admission_token": "tampered.jwt.signature", "nonce": "tampered_nonce_123"},
        headers=headers,
    )
    assert_error(res, 403, "ADMISSION_REQUIRED")


async def test_register_end_to_end_flow(
    client: httpx.AsyncClient,
    auth_header_admin: dict[str, str],
    auth_header_user: dict[str, str],
) -> None:
    """Full lifecycle: Join -> Register -> Idempotent Replay -> Conflict -> Duplicate -> Status Recovery."""
    camp_id = await _create_open_campaign(client, auth_header_admin)

    # 1. Join campaign
    res_join = await client.post(f"/api/v1/campaigns/{camp_id}/join", headers=auth_header_user)
    assert res_join.status_code == 201
    join_data = res_join.json()
    token = join_data["admission_token"]
    nonce = join_data["nonce"]

    # 2. Register with Idempotency-Key K1
    k1 = f"k1-{uuid.uuid4().hex}"
    headers_k1 = {**auth_header_user, "Idempotency-Key": k1}
    body_k1 = {"admission_token": token, "nonce": nonce}

    res_reg = await client.post(
        f"/api/v1/campaigns/{camp_id}/register",
        json=body_k1,
        headers=headers_k1,
    )
    assert res_reg.status_code == 201
    reg_data = res_reg.json()
    assert reg_data["status"] == "REGISTERED"
    assert reg_data["campaign_id"] == camp_id
    assert reg_data["risk_level"] == "LOW"
    reg_id = reg_data["registration_id"]

    # 3. Idempotent replay: same key + same body returns 200 identical response
    res_replay = await client.post(
        f"/api/v1/campaigns/{camp_id}/register",
        json=body_k1,
        headers=headers_k1,
    )
    assert res_replay.status_code == 200
    replay_data = res_replay.json()
    assert replay_data["registration_id"] == reg_id
    assert replay_data["status"] == "REGISTERED"

    # 4. Idempotency conflict: same key + altered body returns 409 IDEMPOTENCY_CONFLICT
    res_conflict = await client.post(
        f"/api/v1/campaigns/{camp_id}/register",
        json={"admission_token": token, "nonce": "altered-nonce-val"},
        headers=headers_k1,
    )
    assert_error(res_conflict, 409, "IDEMPOTENCY_CONFLICT")

    # 5. Duplicate Entry: second join for same participant -> fresh permit -> 409 DUPLICATE_ENTRY
    res_join2 = await client.post(f"/api/v1/campaigns/{camp_id}/join", headers=auth_header_user)
    assert res_join2.status_code == 201
    token2 = res_join2.json()["admission_token"]
    nonce2 = res_join2.json()["nonce"]

    k2 = f"k2-{uuid.uuid4().hex}"
    headers_k2 = {**auth_header_user, "Idempotency-Key": k2}
    res_dup = await client.post(
        f"/api/v1/campaigns/{camp_id}/register",
        json={"admission_token": token2, "nonce": nonce2},
        headers=headers_k2,
    )
    assert_error(res_dup, 409, "DUPLICATE_ENTRY")

    # 6. Status recovery slice shows is_registered=True
    res_status = await client.get(f"/api/v1/campaigns/{camp_id}/status", headers=auth_header_user)
    assert res_status.status_code == 200
    status_data = res_status.json()
    assert status_data["participant_state"] == "REGISTERED"
    assert status_data["registration"]["is_registered"] is True
    assert status_data["registration"]["registration_id"] == reg_id
    assert status_data["registration_slice"]["is_registered"] is True

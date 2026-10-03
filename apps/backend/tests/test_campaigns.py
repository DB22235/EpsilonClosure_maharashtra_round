"""
Integration tests for campaign lifecycle, state machine, access control, and status recovery.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from tests.conftest import assert_error

pytestmark = pytest.mark.asyncio


def _valid_campaign_payload(
    name: str = "Test Campaign",
    capacity: int = 20,
    reg_start_delta_seconds: int = -60,
) -> dict:
    """Generate a valid CampaignCreateRequest payload with correct chronological order."""
    now = datetime.now(timezone.utc)
    reg_start = now + timedelta(seconds=reg_start_delta_seconds)
    reg_end = now + timedelta(hours=1)
    redemption = now + timedelta(hours=2)

    return {
        "name": f"{name} {uuid.uuid4().hex[:6]}",
        "description": "Integration test campaign",
        "venue": "Cyber Dome",
        "event_start": (now + timedelta(days=7)).isoformat(),
        "capacity": capacity,
        "registration_start": reg_start.isoformat(),
        "registration_end": reg_end.isoformat(),
        "redemption_deadline": redemption.isoformat(),
        "max_tickets_per_participant": 1,
        "allocation_method": "UNIFORM_LOTTERY",
        "standby_policy": "FIXED_ORDER",
        "policy_version": "v1.0",
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4A: Access Control
# ─────────────────────────────────────────────────────────────────────────────

async def test_admin_campaigns_unauthenticated(client: httpx.AsyncClient) -> None:
    """POST /api/v1/admin/campaigns without auth returns 401 AUTH_REQUIRED."""
    response = await client.post("/api/v1/admin/campaigns", json=_valid_campaign_payload())
    assert_error(response, 401, "AUTH_REQUIRED")


async def test_admin_campaigns_forbidden_for_user(
    client: httpx.AsyncClient,
    auth_header_user: dict[str, str],
) -> None:
    """POST /api/v1/admin/campaigns with user auth returns 403 FORBIDDEN."""
    response = await client.post(
        "/api/v1/admin/campaigns",
        json=_valid_campaign_payload(),
        headers=auth_header_user,
    )
    assert_error(response, 403, "FORBIDDEN")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4B: Create + Public Visibility
# ─────────────────────────────────────────────────────────────────────────────

async def test_admin_create_and_visibility(
    client: httpx.AsyncClient,
    auth_header_admin: dict[str, str],
) -> None:
    """
    3. Admin creates campaign with valid payload => 201 status=DRAFT
    4. GET /api/v1/campaigns (public) does not include DRAFT campaign
    5. GET /api/v1/campaigns/{id} public for DRAFT => 404
    6. GET /api/v1/admin/campaigns/{id} => 200 and includes seat_counts/registration_counts
    """
    payload = _valid_campaign_payload(name="Draft Visibility Test", capacity=10)

    # 3. Create campaign
    res_create = await client.post(
        "/api/v1/admin/campaigns",
        json=payload,
        headers=auth_header_admin,
    )
    assert res_create.status_code == 201
    created_camp = res_create.json()
    camp_id = created_camp["id"]
    assert created_camp["status"] == "DRAFT"
    assert created_camp["capacity"] == 10

    # 4. Public list should NOT include DRAFT campaign
    res_pub_list = await client.get("/api/v1/campaigns")
    assert res_pub_list.status_code == 200
    pub_ids = [c["id"] for c in res_pub_list.json()["data"]]
    assert camp_id not in pub_ids

    # 5. Public get by ID for DRAFT returns 404
    res_pub_get = await client.get(f"/api/v1/campaigns/{camp_id}")
    assert_error(res_pub_get, 404, "CAMPAIGN_NOT_FOUND")

    # 6. Admin get by ID includes seat_counts and registration_counts
    res_admin_get = await client.get(
        f"/api/v1/admin/campaigns/{camp_id}",
        headers=auth_header_admin,
    )
    assert res_admin_get.status_code == 200
    admin_camp = res_admin_get.json()
    assert admin_camp["id"] == camp_id
    assert "seat_counts" in admin_camp
    assert "registration_counts" in admin_camp
    assert admin_camp["seat_counts"]["total"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4C: Validation
# ─────────────────────────────────────────────────────────────────────────────

async def test_create_campaign_invalid_chronology(
    client: httpx.AsyncClient,
    auth_header_admin: dict[str, str],
) -> None:
    """Create campaign with registration_end <= registration_start returns 422."""
    now = datetime.now(timezone.utc)
    payload = _valid_campaign_payload()
    # Invert dates: registration_end before registration_start
    payload["registration_start"] = (now + timedelta(hours=2)).isoformat()
    payload["registration_end"] = (now + timedelta(hours=1)).isoformat()

    response = await client.post(
        "/api/v1/admin/campaigns",
        json=payload,
        headers=auth_header_admin,
    )
    assert response.status_code == 422


async def test_create_campaign_invalid_capacity(
    client: httpx.AsyncClient,
    auth_header_admin: dict[str, str],
) -> None:
    """Create campaign with capacity <= 0 returns 422."""
    payload = _valid_campaign_payload()
    payload["capacity"] = 0

    response = await client.post(
        "/api/v1/admin/campaigns",
        json=payload,
        headers=auth_header_admin,
    )
    assert response.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4D & 4E & 4F & 4G & 4H & 4I: Full State Machine Lifecycle
# ─────────────────────────────────────────────────────────────────────────────

async def test_campaign_full_lifecycle(
    client: httpx.AsyncClient,
    auth_header_admin: dict[str, str],
    auth_header_user: dict[str, str],
) -> None:
    """
    Executes the full happy path state progression, invalid transitions,
    edit rules, operational pause/resume, status recovery, and audit checks.
    """
    # 1. Create initial DRAFT campaign
    payload = _valid_campaign_payload(name="Lifecycle Campaign", capacity=5)
    res_create = await client.post(
        "/api/v1/admin/campaigns",
        json=payload,
        headers=auth_header_admin,
    )
    assert res_create.status_code == 201
    camp_id = res_create.json()["id"]

    # 9. PATCH draft campaign name => 200
    res_patch = await client.patch(
        f"/api/v1/admin/campaigns/{camp_id}",
        json={"name": "Patched Draft Name"},
        headers=auth_header_admin,
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["name"] == "Patched Draft Name"

    # 11. POST /prepare => PREPARING and seats generated
    res_prep = await client.post(
        f"/api/v1/admin/campaigns/{camp_id}/prepare",
        headers=auth_header_admin,
    )
    assert res_prep.status_code == 200
    prep_data = res_prep.json()
    assert prep_data["new_status"] == "PREPARING"
    assert prep_data["previous_status"] == "DRAFT"

    # Verify admin detail reflects PREPARING, policy_hash, and seats
    res_admin_prep = await client.get(
        f"/api/v1/admin/campaigns/{camp_id}",
        headers=auth_header_admin,
    )
    assert res_admin_prep.status_code == 200
    prep_admin_data = res_admin_prep.json()
    assert prep_admin_data["status"] == "PREPARING"
    assert prep_admin_data["policy_hash"] is not None
    assert prep_admin_data["seat_counts"]["total"] == 5
    assert prep_admin_data["seat_counts"]["available"] == 5

    # 12. POST /prepare again => 409 INVALID_STATE_TRANSITION
    res_prep_dup = await client.post(
        f"/api/v1/admin/campaigns/{camp_id}/prepare",
        headers=auth_header_admin,
    )
    assert_error(res_prep_dup, 409, "INVALID_STATE_TRANSITION")

    # 13. POST /publish => OPEN and published_at/policy_hash set
    res_pub = await client.post(
        f"/api/v1/admin/campaigns/{camp_id}/publish",
        headers=auth_header_admin,
    )
    assert res_pub.status_code == 200
    pub_data = res_pub.json()
    assert pub_data["new_status"] == "OPEN"
    assert pub_data["previous_status"] == "PREPARING"

    # Verify published_at is set in admin detail
    res_admin_pub = await client.get(
        f"/api/v1/admin/campaigns/{camp_id}",
        headers=auth_header_admin,
    )
    assert res_admin_pub.status_code == 200
    assert res_admin_pub.json()["published_at"] is not None

    # 10. After OPEN, PATCH should return 409 CAMPAIGN_NOT_EDITABLE
    res_patch_open = await client.patch(
        f"/api/v1/admin/campaigns/{camp_id}",
        json={"name": "Illegal Edit"},
        headers=auth_header_admin,
    )
    assert_error(res_patch_open, 409, "CAMPAIGN_NOT_EDITABLE")

    # 14. Public list includes campaign
    res_list = await client.get("/api/v1/campaigns")
    assert res_list.status_code == 200
    active_ids = [c["id"] for c in res_list.json()["data"]]
    assert camp_id in active_ids

    # 15. Public get by id returns 200
    res_pub_detail = await client.get(f"/api/v1/campaigns/{camp_id}")
    assert res_pub_detail.status_code == 200
    assert res_pub_detail.json()["id"] == camp_id

    # 20. Invalid transition: freeze on OPEN => 409 INVALID_STATE_TRANSITION
    res_bad_freeze = await client.post(
        f"/api/v1/admin/campaigns/{camp_id}/freeze",
        headers=auth_header_admin,
    )
    assert_error(res_bad_freeze, 409, "INVALID_STATE_TRANSITION")

    # 21. Pause REGISTRATION => registration_paused true
    res_pause_reg = await client.post(
        f"/api/v1/admin/campaigns/{camp_id}/pause",
        json={"scope": "REGISTRATION", "reason": "High load"},
        headers=auth_header_admin,
    )
    assert res_pause_reg.status_code == 200
    assert res_pause_reg.json()["registration_paused"] is True
    assert res_pause_reg.json()["status"] == "OPEN"

    # 22. Resume REGISTRATION => registration_paused false
    res_resume_reg = await client.post(
        f"/api/v1/admin/campaigns/{camp_id}/resume",
        json={"scope": "REGISTRATION"},
        headers=auth_header_admin,
    )
    assert res_resume_reg.status_code == 200
    assert res_resume_reg.json()["registration_paused"] is False

    # 23. Pause ADMISSION and REDEMPTION both toggle correctly
    res_pause_adm = await client.post(
        f"/api/v1/admin/campaigns/{camp_id}/pause",
        json={"scope": "ADMISSION", "reason": "Gate check"},
        headers=auth_header_admin,
    )
    assert res_pause_adm.json()["admission_paused"] is True
    await client.post(
        f"/api/v1/admin/campaigns/{camp_id}/resume",
        json={"scope": "ADMISSION"},
        headers=auth_header_admin,
    )

    res_pause_red = await client.post(
        f"/api/v1/admin/campaigns/{camp_id}/pause",
        json={"scope": "REDEMPTION", "reason": "Payment pause"},
        headers=auth_header_admin,
    )
    assert res_pause_red.json()["redemption_paused"] is True
    await client.post(
        f"/api/v1/admin/campaigns/{camp_id}/resume",
        json={"scope": "REDEMPTION"},
        headers=auth_header_admin,
    )

    # 24. GET /campaigns/{id}/status without auth => 401
    res_status_unauth = await client.get(f"/api/v1/campaigns/{camp_id}/status")
    assert_error(res_status_unauth, 401, "AUTH_REQUIRED")

    # 25. GET /campaigns/{id}/status with user auth => 200
    res_status_user = await client.get(
        f"/api/v1/campaigns/{camp_id}/status",
        headers=auth_header_user,
    )
    assert res_status_user.status_code == 200
    status_body = res_status_user.json()
    assert status_body["participant_state"] == "NOT_REGISTERED"
    assert status_body["registration"] is None
    assert "server_time" in status_body["campaign"]

    # 16. POST /close => CLOSED
    res_close = await client.post(
        f"/api/v1/admin/campaigns/{camp_id}/close",
        headers=auth_header_admin,
    )
    assert res_close.status_code == 200
    assert res_close.json()["new_status"] == "CLOSED"

    # 17. POST /freeze => FROZEN
    res_freeze = await client.post(
        f"/api/v1/admin/campaigns/{camp_id}/freeze",
        headers=auth_header_admin,
    )
    assert res_freeze.status_code == 200
    assert res_freeze.json()["new_status"] == "FROZEN"

    # 19. Invalid transition: close on FROZEN => 409 INVALID_STATE_TRANSITION
    res_bad_close = await client.post(
        f"/api/v1/admin/campaigns/{camp_id}/close",
        headers=auth_header_admin,
    )
    assert_error(res_bad_close, 409, "INVALID_STATE_TRANSITION")

    # 18. POST /draw => DRAWING
    res_draw = await client.post(
        f"/api/v1/admin/campaigns/{camp_id}/draw",
        headers=auth_header_admin,
    )
    assert res_draw.status_code == 200
    assert res_draw.json()["new_status"] == "DRAWING"

    # 26. Audit trail smoke check: verify transition responses returned previous/new status
    assert res_draw.json()["previous_status"] == "FROZEN"
    assert res_draw.json()["new_status"] == "DRAWING"

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

    # 20. Invalid transition: publish on OPEN => 409 INVALID_STATE_TRANSITION
    res_bad_publish = await client.post(
        f"/api/v1/admin/campaigns/{camp_id}/publish",
        headers=auth_header_admin,
    )
    assert_error(res_bad_publish, 409, "INVALID_STATE_TRANSITION")

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
    assert res_freeze.json().get("status") == "FROZEN" or res_freeze.json().get("new_status") == "FROZEN"

    # 19. Invalid transition: close on FROZEN => 409 INVALID_STATE_TRANSITION
    res_bad_close = await client.post(
        f"/api/v1/admin/campaigns/{camp_id}/close",
        headers=auth_header_admin,
    )
    assert_error(res_bad_close, 409, "INVALID_STATE_TRANSITION")

    # 18. POST /draw => executes lottery draw
    res_draw = await client.post(
        f"/api/v1/admin/campaigns/{camp_id}/draw",
        headers=auth_header_admin,
    )
    assert res_draw.status_code == 200
    draw_data = res_draw.json()
    assert "run_id" in draw_data
    assert draw_data["campaign_id"] == camp_id
    assert "seed_hash" in draw_data


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4J: Admin Pagination & Circuit Breaker Idempotency
# ─────────────────────────────────────────────────────────────────────────────

async def test_admin_list_campaigns_pagination(
    client: httpx.AsyncClient,
    auth_header_admin: dict[str, str],
) -> None:
    """Admin campaign list supports page and page_size query parameters."""
    # Create two distinct test campaigns
    p1 = _valid_campaign_payload(name="Pagination Camp 1")
    p2 = _valid_campaign_payload(name="Pagination Camp 2")

    r1 = await client.post("/api/v1/admin/campaigns", json=p1, headers=auth_header_admin)
    r2 = await client.post("/api/v1/admin/campaigns", json=p2, headers=auth_header_admin)
    assert r1.status_code == 201
    assert r2.status_code == 201

    # Fetch with page_size=1
    res_p1 = await client.get("/api/v1/admin/campaigns?page=1&page_size=1", headers=auth_header_admin)
    assert res_p1.status_code == 200
    data_p1 = res_p1.json()
    assert len(data_p1) == 1

    # Fetch page 2
    res_p2 = await client.get("/api/v1/admin/campaigns?page=2&page_size=1", headers=auth_header_admin)
    assert res_p2.status_code == 200
    data_p2 = res_p2.json()
    assert len(data_p2) == 1
    assert data_p1[0]["id"] != data_p2[0]["id"]


async def test_admin_campaign_emergency_pause_idempotency(
    client: httpx.AsyncClient,
    auth_header_admin: dict[str, str],
) -> None:
    """Toggling emergency pauses multiple times operates idempotently and safely."""
    payload = _valid_campaign_payload(name="Pause Idempotency")
    res_create = await client.post("/api/v1/admin/campaigns", json=payload, headers=auth_header_admin)
    camp_id = res_create.json()["id"]

    # 1. Pause ADMISSION first time
    res_p1 = await client.post(
        f"/api/v1/admin/campaigns/{camp_id}/pause",
        json={"scope": "ADMISSION", "reason": "Initial manual pause"},
        headers=auth_header_admin,
    )
    assert res_p1.status_code == 200
    assert res_p1.json()["admission_paused"] is True

    # 2. Pause ADMISSION second time (already paused) -> succeeds safely
    res_p2 = await client.post(
        f"/api/v1/admin/campaigns/{camp_id}/pause",
        json={"scope": "ADMISSION", "reason": "Repeated pause call"},
        headers=auth_header_admin,
    )
    assert res_p2.status_code == 200
    assert res_p2.json()["admission_paused"] is True

    # 3. Resume ADMISSION first time
    res_r1 = await client.post(
        f"/api/v1/admin/campaigns/{camp_id}/resume",
        json={"scope": "ADMISSION"},
        headers=auth_header_admin,
    )
    assert res_r1.status_code == 200
    assert res_r1.json()["admission_paused"] is False

    # 4. Resume ADMISSION second time (already resumed) -> succeeds safely
    res_r2 = await client.post(
        f"/api/v1/admin/campaigns/{camp_id}/resume",
        json={"scope": "ADMISSION"},
        headers=auth_header_admin,
    )
    assert res_r2.status_code == 200
    assert res_r2.json()["admission_paused"] is False


async def test_audit_query_pagination_and_filter(
    client: httpx.AsyncClient,
    auth_header_admin: dict[str, str],
) -> None:
    """GET /campaigns/{id}/audit correctly enforces limit, offset, and event_type filtering."""
    payload = _valid_campaign_payload(name="Audit Filter Camp", capacity=3)
    res_create = await client.post("/api/v1/admin/campaigns", json=payload, headers=auth_header_admin)
    camp_id = res_create.json()["id"]

    # Execute prepare to generate audit entries
    await client.post(f"/api/v1/admin/campaigns/{camp_id}/prepare", headers=auth_header_admin)

    # Query with limit=1, offset=0
    res_audit_lim = await client.get(
        f"/api/v1/campaigns/{camp_id}/audit?limit=1&offset=0",
        headers=auth_header_admin,
    )
    assert res_audit_lim.status_code == 200
    audit_data = res_audit_lim.json()
    assert "data" in audit_data
    assert len(audit_data["data"]) <= 1
    assert audit_data["limit"] == 1
    assert audit_data["offset"] == 0

    # Query with non-existent event_type filter -> returns empty data
    res_audit_filt = await client.get(
        f"/api/v1/campaigns/{camp_id}/audit?event_type=NONEXISTENT_DUMMY_EVENT",
        headers=auth_header_admin,
    )
    assert res_audit_filt.status_code == 200
    assert len(res_audit_filt.json()["data"]) == 0


async def test_campaign_direct_draft_to_open_publish(
    client: httpx.AsyncClient,
    auth_header_admin: dict[str, str],
) -> None:
    """Directly publishing a DRAFT campaign automatically prepares seats and transitions to OPEN (200)."""
    payload = _valid_campaign_payload(name="Direct Publish Camp", capacity=15)
    res_create = await client.post("/api/v1/admin/campaigns", json=payload, headers=auth_header_admin)
    assert res_create.status_code == 201
    camp = res_create.json()
    camp_id = camp["id"]
    assert camp["status"] == "DRAFT"

    # Direct publish without manual prepare step
    res_pub = await client.post(f"/api/v1/admin/campaigns/{camp_id}/publish", headers=auth_header_admin)
    assert res_pub.status_code == 200
    pub_data = res_pub.json()
    assert pub_data["new_status"] == "OPEN"

    # Verify admin detail has generated 15 available seats
    res_detail = await client.get(f"/api/v1/admin/campaigns/{camp_id}", headers=auth_header_admin)
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["status"] == "OPEN"
    assert detail["seat_counts"]["total"] == 15
    assert detail["seat_counts"]["available"] == 15

    # Verify public event view is accessible
    res_public = await client.get(f"/api/v1/campaigns/{camp_id}")
    assert res_public.status_code == 200
    assert res_public.json()["status"] == "OPEN"


async def test_campaign_publish_advances_future_registration_start(
    client: httpx.AsyncClient,
    auth_header_admin: dict[str, str],
) -> None:
    """Publishing a campaign scheduled in the future auto-advances registration_start to now rather than erroring."""
    now = datetime.now(timezone.utc)
    future_start = now + timedelta(hours=3)
    future_end = now + timedelta(days=2)
    future_deadline = now + timedelta(days=3)

    payload = {
        "name": f"Future Camp {uuid.uuid4().hex[:6]}",
        "description": "Campaign configured with future start time",
        "capacity": 10,
        "registration_start": future_start.isoformat(),
        "registration_end": future_end.isoformat(),
        "redemption_deadline": future_deadline.isoformat(),
        "max_tickets_per_participant": 1,
        "allocation_method": "UNIFORM_LOTTERY",
        "standby_policy": "FIXED_ORDER",
        "policy_version": "v1.0",
    }
    res_create = await client.post("/api/v1/admin/campaigns", json=payload, headers=auth_header_admin)
    assert res_create.status_code == 201
    camp_id = res_create.json()["id"]

    # Publish must succeed (no 409 REGISTRATION_NOT_STARTED) and transition to OPEN
    res_pub = await client.post(f"/api/v1/admin/campaigns/{camp_id}/publish", headers=auth_header_admin)
    assert res_pub.status_code == 200
    assert res_pub.json()["new_status"] == "OPEN"

    # Detail shows registration_start <= now
    res_detail = await client.get(f"/api/v1/admin/campaigns/{camp_id}", headers=auth_header_admin)
    assert res_detail.status_code == 200
    reg_start_parsed = datetime.fromisoformat(res_detail.json()["registration_start"])
    assert reg_start_parsed <= datetime.now(timezone.utc)



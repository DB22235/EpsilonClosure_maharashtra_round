"""
Integration tests for Background Workers, Standby Promotions, Metrics & Audit APIs (Steps 9 & 10).
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy import select, update

from app.database import async_session_factory
from app.models.entitlement import Entitlement
from app.models.inventory import Seat
from app.models.lottery import LotteryEntry, LotteryRun
from app.models.participant import Participant, Profile
from app.models.registration import Registration
from app.services.standby_service import promote_next_standby
from app.workers.entitlement_expiry_worker import expire_stale_entitlements
from app.workers.hold_expiry_worker import expire_stale_seat_holds
from tests.conftest import assert_error
from tests.test_entitlements import _setup_drawn_campaign_with_winner

pytestmark = pytest.mark.asyncio


async def test_hold_expiry_worker(
    client: httpx.AsyncClient,
    auth_header_admin: dict[str, str],
    auth_header_user: dict[str, str],
) -> None:
    """Worker automatically frees expired seat holds and resets linked entitlement state."""
    camp_id, entitlement_id = await _setup_drawn_campaign_with_winner(
        client, auth_header_admin, auth_header_user
    )

    # 1. Acquire seat hold
    res_hold = await client.post(
        f"/api/v1/entitlements/{camp_id}/hold",
        headers={**auth_header_user, "Idempotency-Key": f"hold-exp-{uuid.uuid4().hex}"},
        json={"entitlement_token": entitlement_id},
    )
    assert res_hold.status_code == 200
    seat_id = res_hold.json()["seat_id"]

    # 2. Artificially expire the hold timestamp in DB
    past_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    async with async_session_factory() as db:
        await db.execute(
            update(Seat)
            .where(Seat.id == uuid.UUID(seat_id))
            .values(hold_expires_at=past_time)
        )
        await db.commit()

    # 3. Run hold expiry worker
    async with async_session_factory() as db:
        stats = await expire_stale_seat_holds(db)
        await db.commit()

    assert stats["seats_freed"] >= 1

    # 4. Verify seat is back to AVAILABLE
    async with async_session_factory() as db:
        seat_row = (await db.execute(select(Seat).where(Seat.id == uuid.UUID(seat_id)))).scalar_one()
        assert seat_row.status == "AVAILABLE"
        assert seat_row.held_by_entitlement_id is None
        assert seat_row.hold_expires_at is None


async def test_entitlement_expiry_worker(
    client: httpx.AsyncClient,
    auth_header_admin: dict[str, str],
    auth_header_user: dict[str, str],
) -> None:
    """Worker transitions past-deadline entitlements to EXPIRED."""
    camp_id, entitlement_id = await _setup_drawn_campaign_with_winner(
        client, auth_header_admin, auth_header_user
    )

    # 1. Artificially backdate entitlement expiration
    past_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    async with async_session_factory() as db:
        await db.execute(
            update(Entitlement)
            .where(Entitlement.id == uuid.UUID(entitlement_id))
            .values(expires_at=past_time)
        )
        await db.commit()

    # 2. Run entitlement expiry worker
    async with async_session_factory() as db:
        stats = await expire_stale_entitlements(db)
        await db.commit()

    assert stats["entitlements_expired"] >= 1

    # 3. Verify entitlement is EXPIRED
    async with async_session_factory() as db:
        ent_row = (await db.execute(select(Entitlement).where(Entitlement.id == uuid.UUID(entitlement_id)))).scalar_one()
        assert ent_row.status == "EXPIRED"

    # 4. Attempting to hold with expired entitlement fails with 410 ENTITLEMENT_EXPIRED
    res_hold_exp = await client.post(
        f"/api/v1/entitlements/{camp_id}/hold",
        headers={**auth_header_user, "Idempotency-Key": f"hold-after-exp-{uuid.uuid4().hex}"},
        json={"entitlement_token": entitlement_id},
    )
    assert_error(res_hold_exp, 410, "ENTITLEMENT_EXPIRED")


async def test_standby_process_next_admin_endpoint(
    client: httpx.AsyncClient,
    auth_header_admin: dict[str, str],
    auth_header_user: dict[str, str],
) -> None:
    """Admin standby process-next endpoint promotes queue participants when capacity exists."""
    camp_id, _ = await _setup_drawn_campaign_with_winner(
        client, auth_header_admin, auth_header_user
    )

    # Manually insert a mock standby entry with valid participant and registration to test promotion
    c_uuid = uuid.UUID(camp_id)
    async with async_session_factory() as db:
        stmt_run = select(LotteryRun).where(LotteryRun.campaign_id == c_uuid)
        run = (await db.execute(stmt_run)).scalar_one()

        prof_id = uuid.uuid4()
        prof = Profile(
            id=prof_id,
            display_name="Standby User",
            role="USER",
            email_verified=True,
        )
        db.add(prof)
        await db.flush()

        part = Participant(
            id=uuid.uuid4(),
            account_id=prof_id,
            email_hash=hashlib.sha256(f"{prof_id}@test.com".encode()).hexdigest(),
            verification_status="VERIFIED",
            risk_level="LOW",
        )
        db.add(part)
        await db.flush()

        reg = Registration(
            id=uuid.uuid4(),
            campaign_id=c_uuid,
            participant_id=part.id,
            idempotency_key=f"standby-reg-{uuid.uuid4().hex}",
            request_hash="mock_hash",
            status="ACCEPTED",
            eligible=True,
        )
        db.add(reg)
        await db.flush()

        entry = LotteryEntry(
            id=uuid.uuid4(),
            lottery_run_id=run.id,
            participant_id=part.id,
            registration_id=reg.id,
            position=99,
            selected=False,
            standby_position=1,
        )
        db.add(entry)
        await db.commit()

    # 1. Call admin endpoint to process next standby
    res_promo = await client.post(
        f"/api/v1/admin/campaigns/{camp_id}/standby/process-next",
        headers=auth_header_admin,
    )
    assert res_promo.status_code == 200
    promo_data = res_promo.json()
    assert promo_data["promoted"] is True
    assert promo_data["standby_position"] == 1

    # 2. Re-invoking endpoint when no further capacity/standby exists handles gracefully
    res_promo_repeat = await client.post(
        f"/api/v1/admin/campaigns/{camp_id}/standby/process-next",
        headers=auth_header_admin,
    )
    assert res_promo_repeat.status_code == 200
    assert res_promo_repeat.json()["promoted"] is False


async def test_campaign_metrics_and_fairness_evidence(
    client: httpx.AsyncClient,
    auth_header_admin: dict[str, str],
    auth_header_user: dict[str, str],
) -> None:
    """GET /metrics and /fairness return coherent counts and cryptographic proof."""
    camp_id, _ = await _setup_drawn_campaign_with_winner(
        client, auth_header_admin, auth_header_user
    )

    # 1. Authenticated metrics endpoint
    res_metrics = await client.get(
        f"/api/v1/campaigns/{camp_id}/metrics",
        headers=auth_header_user,
    )
    assert res_metrics.status_code == 200
    m = res_metrics.json()
    assert m["campaign_id"] == camp_id
    assert m["oversell_count"] == 0
    assert m["duplicate_allocation_count"] == 0
    assert m["winners_count"] >= 1

    # 2. Public fairness endpoint (redacted seed)
    res_fair_pub = await client.get(f"/api/v1/campaigns/{camp_id}/fairness")
    assert res_fair_pub.status_code == 200
    f_pub = res_fair_pub.json()
    assert f_pub["randomness_seed"] is None
    assert f_pub["roster_hash"] is not None
    assert f_pub["evidence_hash"] is not None
    assert "selection probability is independent of request rate" in f_pub["statement"]

    # 3. Admin fairness endpoint (revealed seed)
    res_fair_admin = await client.get(
        f"/api/v1/admin/campaigns/{camp_id}/fairness-evidence",
        headers=auth_header_admin,
    )
    assert res_fair_admin.status_code == 200
    f_admin = res_fair_admin.json()
    assert f_admin["randomness_seed"] is not None


async def test_audit_log_rbac_and_filtering(
    client: httpx.AsyncClient,
    auth_header_admin: dict[str, str],
    auth_header_user: dict[str, str],
) -> None:
    """User audit queries only return own actions; admin queries receive the full stream."""
    camp_id, _ = await _setup_drawn_campaign_with_winner(
        client, auth_header_admin, auth_header_user
    )

    # 1. Participant query
    res_user_audit = await client.get(
        f"/api/v1/campaigns/{camp_id}/audit",
        headers=auth_header_user,
    )
    assert res_user_audit.status_code == 200
    user_data = res_user_audit.json()
    assert "data" in user_data
    assert user_data["total"] >= 1

    # 2. Admin query
    res_admin_audit = await client.get(
        f"/api/v1/campaigns/{camp_id}/audit",
        headers=auth_header_admin,
    )
    assert res_admin_audit.status_code == 200
    admin_data = res_admin_audit.json()
    assert admin_data["total"] >= user_data["total"]

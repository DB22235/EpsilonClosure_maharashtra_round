"""
Standby promotion service orchestrating deterministic queue advancement upon released inventory.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import lru_settings
from app.models.audit import AuditEvent, MetricEvent, StandbyPromotion
from app.models.entitlement import Entitlement
from app.models.inventory import Booking, Seat
from app.models.lottery import LotteryEntry, LotteryRun
from app.services.admission_service import _build_error
from app.services.campaign_service import get_campaign_or_404

logger = logging.getLogger(__name__)


async def promote_next_standby(
    db: AsyncSession,
    campaign_id: uuid.UUID,
    admin_id: uuid.UUID | None = None,
    request_id: str = "",
) -> dict[str, Any]:
    """
    Atomically checks available capacity and promotes the next ranked standby participant
    by issuing a new short-lived Entitlement and recording an immutable StandbyPromotion entry.
    """
    now = datetime.now(timezone.utc)
    campaign = await get_campaign_or_404(db, campaign_id, request_id)

    if campaign.status not in ("CLAIMING", "FROZEN", "ACTIVE", "OPEN"):
        raise _build_error(
            "INVALID_STATE_TRANSITION",
            f"Cannot promote standby in campaign status '{campaign.status}'. Must be in active claim phase.",
            request_id,
            status.HTTP_409_CONFLICT,
        )

    # 1. Compute committed/claimed allocations
    stmt_bookings = select(func.count(Booking.id)).where(Booking.campaign_id == campaign_id)
    confirmed_count = (await db.execute(stmt_bookings)).scalar_one()

    stmt_active_ent = select(func.count(Entitlement.id)).where(
        Entitlement.campaign_id == campaign_id,
        Entitlement.status.in_(["SELECTED", "CLAIM_PENDING", "HELD"]),
        Entitlement.expires_at > now,
    )
    active_ent_count = (await db.execute(stmt_active_ent)).scalar_one()

    total_in_flight = confirmed_count + active_ent_count
    available_capacity = campaign.capacity - total_in_flight

    if available_capacity <= 0:
        return {
            "promoted": False,
            "reason": "NO_CAPACITY_AVAILABLE",
            "message": "Campaign has no available capacity for standby promotion.",
            "available_capacity": 0,
            "campaign_id": str(campaign_id),
        }

    # 2. Fetch LotteryRun
    stmt_run = select(LotteryRun).where(LotteryRun.campaign_id == campaign_id)
    lottery_run = (await db.execute(stmt_run)).scalar_one_or_none()

    if lottery_run is None:
        raise _build_error(
            "LOTTERY_NOT_FOUND",
            "No lottery draw record found for this campaign.",
            request_id,
            status.HTTP_404_NOT_FOUND,
        )

    # 3. Find already promoted standby positions
    stmt_promoted = select(StandbyPromotion.standby_position).where(
        StandbyPromotion.campaign_id == campaign_id
    )
    promoted_positions = set((await db.execute(stmt_promoted)).scalars().all())

    # 4. Fetch next available standby participant
    conds = [
        LotteryEntry.lottery_run_id == lottery_run.id,
        LotteryEntry.selected.is_(False),
        LotteryEntry.standby_position.is_not(None),
    ]
    if promoted_positions:
        conds.append(~LotteryEntry.standby_position.in_(promoted_positions))

    stmt_next = (
        select(LotteryEntry)
        .where(*conds)
        .order_by(LotteryEntry.standby_position.asc())
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    next_entry = (await db.execute(stmt_next)).scalar_one_or_none()

    if next_entry is None:
        return {
            "promoted": False,
            "reason": "STANDBY_QUEUE_EMPTY",
            "message": "No remaining standby participants in queue.",
            "available_capacity": available_capacity,
            "campaign_id": str(campaign_id),
        }

    # 5. Create winning Entitlement for the promoted participant
    settings = lru_settings()
    redemption_window = settings.ABSOLUTE_REDEMPTION_SECONDS or 300
    expires_at = now + timedelta(seconds=redemption_window)

    nonce_raw = f"{lottery_run.id}:{next_entry.participant_id}:{secrets.token_hex(16)}"
    nonce_hash = hashlib.sha256(nonce_raw.encode("utf-8")).hexdigest()

    entitlement = Entitlement(
        id=uuid.uuid4(),
        campaign_id=campaign_id,
        participant_id=next_entry.participant_id,
        lottery_run_id=lottery_run.id,
        nonce_hash=nonce_hash,
        status="SELECTED",
        expires_at=expires_at,
        created_at=now,
        updated_at=now,
    )
    db.add(entitlement)
    await db.flush()

    # 6. Record StandbyPromotion
    promotion = StandbyPromotion(
        id=uuid.uuid4(),
        campaign_id=campaign_id,
        lottery_run_id=lottery_run.id,
        participant_id=next_entry.participant_id,
        standby_position=next_entry.standby_position,
        entitlement_id=entitlement.id,
        reason="CAPACITY_RELEASED",
        promoted_at=now,
    )
    db.add(promotion)

    req_id = request_id or f"standby-promo-{uuid.uuid4().hex[:8]}"

    # 7. Audit Log
    db.add(
        AuditEvent(
            campaign_id=campaign_id,
            participant_id=next_entry.participant_id,
            actor_type="ADMIN" if admin_id else "WORKER",
            actor_id=admin_id,
            event_type="STANDBY_PROMOTED",
            request_id=req_id,
            metadata_json={
                "standby_position": next_entry.standby_position,
                "entitlement_id": str(entitlement.id),
                "expires_at": expires_at.isoformat(),
            },
        )
    )

    # 8. Metric Event
    db.add(
        MetricEvent(
            campaign_id=campaign_id,
            metric_name="standby_promoted_count",
            metric_value=1.0,
            tags={"standby_position": str(next_entry.standby_position)},
        )
    )

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        logger.warning(
            "Integrity conflict during standby promotion (likely already promoted concurrently): %s",
            exc,
        )
        return {
            "promoted": False,
            "reason": "ALREADY_PROMOTED",
            "message": "Standby position was already promoted by another process.",
            "campaign_id": str(campaign_id),
        }

    return {
        "promoted": True,
        "campaign_id": str(campaign_id),
        "participant_id": str(next_entry.participant_id),
        "standby_position": next_entry.standby_position,
        "entitlement_id": str(entitlement.id),
        "expires_at": expires_at.isoformat(),
        "remaining_capacity_after": available_capacity - 1,
        "message": f"Successfully promoted standby participant at position #{next_entry.standby_position}.",
    }

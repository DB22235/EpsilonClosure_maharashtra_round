"""
Background worker to expire stale entitlements and release any associated active seat holds.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import lru_settings
from app.models.audit import AuditEvent, MetricEvent
from app.models.entitlement import Entitlement
from app.models.inventory import Seat

logger = logging.getLogger(__name__)


async def expire_stale_entitlements(db: AsyncSession) -> dict[str, int]:
    """
    Identifies unconsumed entitlements past their redemption deadline.
    Atomically transitions them to EXPIRED and unlocks any seat held by that entitlement.
    Uses FOR UPDATE SKIP LOCKED for high-concurrency safety.
    """
    settings = lru_settings()
    now = datetime.now(timezone.utc)
    batch_size = settings.WORKER_BATCH_SIZE

    stmt = (
        select(Entitlement)
        .where(
            Entitlement.status.in_(["SELECTED", "CLAIM_PENDING", "HELD"]),
            Entitlement.expires_at <= now,
        )
        .order_by(Entitlement.expires_at.asc())
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    )
    stale_entitlements = list((await db.execute(stmt)).scalars().all())

    if not stale_entitlements:
        return {"entitlements_expired": 0, "seats_freed": 0}

    entitlements_expired = 0
    seats_freed = 0

    for ent in stale_entitlements:
        ent.status = "EXPIRED"
        ent.updated_at = now
        entitlements_expired += 1

        # If a seat is held by this entitlement, release it
        if ent.held_seat_id is not None:
            stmt_seat = (
                select(Seat)
                .where(
                    Seat.id == ent.held_seat_id,
                    Seat.campaign_id == ent.campaign_id,
                )
                .with_for_update(skip_locked=True)
            )
            seat = (await db.execute(stmt_seat)).scalar_one_or_none()

            if seat is not None and seat.status == "HELD" and seat.held_by_entitlement_id == ent.id:
                seat.status = "AVAILABLE"
                seat.held_by_entitlement_id = None
                seat.hold_expires_at = None
                seat.version += 1
                seats_freed += 1

            ent.held_seat_id = None

        req_id = f"worker-ent-expiry-{uuid.uuid4().hex[:8]}"

        # Audit trail
        db.add(
            AuditEvent(
                campaign_id=ent.campaign_id,
                participant_id=ent.participant_id,
                actor_type="WORKER",
                actor_id=None,
                event_type="ENTITLEMENT_EXPIRED",
                request_id=req_id,
                metadata_json={
                    "entitlement_id": str(ent.id),
                    "lottery_run_id": str(ent.lottery_run_id),
                },
            )
        )

        # Metric event
        db.add(
            MetricEvent(
                campaign_id=ent.campaign_id,
                metric_name="entitlements_expired_count",
                metric_value=1.0,
                tags={"participant_id": str(ent.participant_id)},
            )
        )

    logger.info(
        "Entitlement expiry worker expired %d entitlements (freed %d seats)",
        entitlements_expired,
        seats_freed,
    )

    return {
        "entitlements_expired": entitlements_expired,
        "seats_freed": seats_freed,
    }

"""
Background worker to expire stale seat holds and return seats to the available inventory pool.
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


async def expire_stale_seat_holds(db: AsyncSession) -> dict[str, int]:
    """
    Identifies and frees seats whose hold window has expired.
    Safely resets the seat status to AVAILABLE and adjusts associated entitlement state.
    Uses FOR UPDATE SKIP LOCKED to ensure zero lock contention with active hold operations.
    """
    settings = lru_settings()
    now = datetime.now(timezone.utc)
    batch_size = settings.WORKER_BATCH_SIZE

    stmt = (
        select(Seat)
        .where(
            Seat.status == "HELD",
            Seat.hold_expires_at <= now,
        )
        .order_by(Seat.hold_expires_at.asc())
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    )
    stale_seats = list((await db.execute(stmt)).scalars().all())

    if not stale_seats:
        return {"seats_freed": 0, "entitlements_reverted": 0, "entitlements_expired": 0}

    seats_freed = 0
    entitlements_reverted = 0
    entitlements_expired = 0

    for seat in stale_seats:
        old_entitlement_id = seat.held_by_entitlement_id
        campaign_id = seat.campaign_id

        # 1. Reset seat status to AVAILABLE
        seat.status = "AVAILABLE"
        seat.held_by_entitlement_id = None
        seat.hold_expires_at = None
        seat.version += 1
        seats_freed += 1

        # 2. Adjust linked entitlement if one was held
        if old_entitlement_id is not None:
            stmt_ent = (
                select(Entitlement)
                .where(
                    Entitlement.id == old_entitlement_id,
                    Entitlement.status == "HELD",
                )
                .with_for_update(skip_locked=True)
            )
            entitlement = (await db.execute(stmt_ent)).scalar_one_or_none()

            if entitlement is not None:
                entitlement.held_seat_id = None
                if entitlement.expires_at > now:
                    entitlement.status = "SELECTED"
                    entitlements_reverted += 1
                else:
                    entitlement.status = "EXPIRED"
                    entitlements_expired += 1
                entitlement.updated_at = now

        req_id = f"worker-hold-expiry-{uuid.uuid4().hex[:8]}"

        # 3. Audit trail
        db.add(
            AuditEvent(
                campaign_id=campaign_id,
                actor_type="WORKER",
                actor_id=None,
                event_type="SEAT_HOLD_EXPIRED",
                request_id=req_id,
                metadata_json={
                    "seat_id": str(seat.id),
                    "seat_label": seat.seat_label,
                    "previous_entitlement_id": str(old_entitlement_id) if old_entitlement_id else None,
                },
            )
        )

        # 4. Metric event
        db.add(
            MetricEvent(
                campaign_id=campaign_id,
                metric_name="seats_holds_expired_count",
                metric_value=1.0,
                tags={"seat_id": str(seat.id)},
            )
        )

    logger.info(
        "Hold expiry worker freed %d seats (%d entitlements reverted, %d expired)",
        seats_freed,
        entitlements_reverted,
        entitlements_expired,
    )

    return {
        "seats_freed": seats_freed,
        "entitlements_reverted": entitlements_reverted,
        "entitlements_expired": entitlements_expired,
    }

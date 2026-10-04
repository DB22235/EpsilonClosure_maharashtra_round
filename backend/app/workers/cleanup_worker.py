"""
Background worker to clean up expired sessions and compact stale idempotency records.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import lru_settings
from app.models.audit import MetricEvent
from app.models.participant import Session
from app.models.registration import IdempotencyRecord

logger = logging.getLogger(__name__)


async def cleanup_expired_sessions_and_records(db: AsyncSession) -> dict[str, int]:
    """
    Performs routine operational hygiene:
    1. Expires idle or absolute-time-exhausted sessions.
    2. Purges stale idempotency records past retention window.
    NOTE: Audit events are never deleted or modified.
    """
    settings = lru_settings()
    now = datetime.now(timezone.utc)

    # 1. Expire stale sessions
    stmt_sessions = (
        update(Session)
        .where(
            Session.status == "ACTIVE",
            (Session.idle_expires_at <= now) | (Session.absolute_expires_at <= now),
        )
        .values(status="EXPIRED")
    )
    res_sess = await db.execute(stmt_sessions)
    sessions_expired = res_sess.rowcount or 0

    # 2. Compact expired idempotency records
    retention_cutoff = now - timedelta(days=settings.IDEMPOTENCY_RETENTION_DAYS)
    stmt_idemp = delete(IdempotencyRecord).where(
        IdempotencyRecord.expires_at <= retention_cutoff
    )
    res_idemp = await db.execute(stmt_idemp)
    idemp_purged = res_idemp.rowcount or 0

    # 3. Metrics
    if sessions_expired > 0:
        db.add(
            MetricEvent(
                metric_name="sessions_expired_cleanup_count",
                metric_value=float(sessions_expired),
            )
        )
    if idemp_purged > 0:
        db.add(
            MetricEvent(
                metric_name="idempotency_records_purged_count",
                metric_value=float(idemp_purged),
            )
        )

    logger.info(
        "Cleanup worker expired %d sessions, purged %d old idempotency records",
        sessions_expired,
        idemp_purged,
    )

    return {
        "sessions_expired": sessions_expired,
        "idempotency_records_purged": idemp_purged,
    }

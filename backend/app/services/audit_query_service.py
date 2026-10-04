"""
Audit query service providing role-aware, sanitized access to platform audit event streams.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditEvent
from app.schemas.audit import AuditEventItem, AuditListResponse

logger = logging.getLogger(__name__)

SENSITIVE_METADATA_KEYS = {
    "admission_token",
    "nonce",
    "nonce_hash",
    "entitlement_token",
    "secret",
    "password",
    "access_token",
}


def _sanitize_metadata(meta: dict[str, Any] | None) -> dict[str, Any]:
    """Redact any sensitive tokens or cryptographic secrets from metadata JSON."""
    if not meta:
        return {}
    sanitized: dict[str, Any] = {}
    for k, v in meta.items():
        if k in SENSITIVE_METADATA_KEYS:
            sanitized[k] = "[REDACTED]"
        elif isinstance(v, dict):
            sanitized[k] = _sanitize_metadata(v)
        else:
            sanitized[k] = v
    return sanitized


async def list_audit_events(
    db: AsyncSession,
    campaign_id: uuid.UUID,
    *,
    participant_id: uuid.UUID | None = None,
    is_admin: bool = False,
    event_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> AuditListResponse:
    """
    Retrieves a paginated list of audit events for a campaign.
    Enforces participant isolation: non-admin participants only receive their own records.
    """
    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    conds = [AuditEvent.campaign_id == campaign_id]

    if not is_admin:
        if participant_id is None:
            return AuditListResponse(data=[], total=0, limit=limit, offset=offset)
        conds.append(AuditEvent.participant_id == participant_id)
    elif participant_id is not None:
        conds.append(AuditEvent.participant_id == participant_id)

    if event_type:
        conds.append(AuditEvent.event_type == event_type.strip())

    # Count total
    count_stmt = select(func.count(AuditEvent.id)).where(*conds)
    total = (await db.execute(count_stmt)).scalar_one()

    # Query page
    data_stmt = (
        select(AuditEvent)
        .where(*conds)
        .order_by(AuditEvent.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    events = list((await db.execute(data_stmt)).scalars().all())

    items = [
        AuditEventItem(
            id=ev.id,
            campaign_id=ev.campaign_id,
            participant_id=ev.participant_id,
            actor_type=ev.actor_type,
            actor_id=ev.actor_id,
            event_type=ev.event_type,
            reason_code=ev.reason_code,
            metadata_json=_sanitize_metadata(ev.metadata_json),
            request_id=ev.request_id,
            created_at=ev.created_at,
        )
        for ev in events
    ]

    return AuditListResponse(
        data=items,
        total=total,
        limit=limit,
        offset=offset,
    )

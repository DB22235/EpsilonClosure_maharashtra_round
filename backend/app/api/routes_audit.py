"""
Audit trail route handlers.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_profile
from app.models.participant import Participant, Profile
from app.schemas.audit import AuditListResponse
from app.security.request_ids import get_request_id
from app.services.audit_query_service import list_audit_events

router = APIRouter(tags=["audit"])


@router.get(
    "/campaigns/{campaign_id}/audit",
    response_model=AuditListResponse,
    summary="Query verifiable audit event log",
    description="Returns a paginated list of audit events. Non-admin participants receive only their own actions; admins receive the full campaign event stream.",
)
async def get_campaign_audit_endpoint(
    campaign_id: uuid.UUID,
    request: Request,
    event_type: str | None = Query(default=None, description="Optional filter by normalized event_type."),
    limit: int = Query(default=50, ge=1, le=100, description="Items per page (max 100)."),
    offset: int = Query(default=0, ge=0, description="Offset for pagination."),
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
) -> AuditListResponse:
    request_id = await get_request_id(request)
    is_admin = profile.role.upper() == "ADMIN"

    participant_id = None
    if not is_admin:
        stmt = select(Participant).where(Participant.account_id == profile.id)
        participant = (await db.execute(stmt)).scalar_one_or_none()
        if participant:
            participant_id = participant.id

    return await list_audit_events(
        db=db,
        campaign_id=campaign_id,
        participant_id=participant_id,
        is_admin=is_admin,
        event_type=event_type,
        limit=limit,
        offset=offset,
    )

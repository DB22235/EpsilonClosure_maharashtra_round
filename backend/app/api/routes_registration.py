"""
Campaign admission and registration route handlers.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import lru_settings
from app.database import get_db
from app.dependencies import get_current_profile, require_verified_participant
from app.middleware.rate_limit import enforce_rate_limit, get_client_ip
from app.models.participant import Participant, Profile
from app.models.registration import IdempotencyRecord
from app.schemas.registration import JoinRequest, JoinResponse, RegisterRequest, RegisterResponse
from app.security.request_ids import get_request_id
from app.services.admission_service import _build_error, create_admission_permit
from app.services.registration_service import _compute_canonical_request_hash, register_participant

router = APIRouter(prefix="/campaigns", tags=["registration"])
settings = lru_settings()


@router.post(
    "/{campaign_id}/join",
    response_model=JoinResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Join campaign waiting room and obtain cryptographic admission permit",
    description="Validates campaign state and issues a short-lived, HMAC-SHA256 signed admission permit token.",
)
async def join_campaign_endpoint(
    campaign_id: uuid.UUID,
    request: Request,
    body: JoinRequest | None = None,
    participant: Participant = Depends(require_verified_participant),
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
) -> JoinResponse:
    request_id = await get_request_id(request)

    # Rate limiting: scoped per participant and per IP
    await enforce_rate_limit(
        scope="participant_join",
        key_identifier=str(participant.id),
        limit=settings.RL_JOIN_PER_MIN,
        request_id=request_id,
    )

    return await create_admission_permit(
        db,
        campaign_id=campaign_id,
        participant_id=participant.id,
        subject_id=profile.id,
        request_id=request_id,
    )


@router.post(
    "/{campaign_id}/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register participant entry for campaign with idempotency",
    description="Atomically consumes the admission permit, evaluates risk/challenge seams, and creates a unique registration entry.",
)
async def register_campaign_endpoint(
    campaign_id: uuid.UUID,
    request: Request,
    response: Response,
    body: RegisterRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    participant: Participant = Depends(require_verified_participant),
    db: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    request_id = await get_request_id(request)

    if not idempotency_key or not idempotency_key.strip():
        raise _build_error(
            "IDEMPOTENCY_KEY_REQUIRED",
            "Idempotency-Key header is required for registration",
            request_id,
            status.HTTP_400_BAD_REQUEST,
        )

    clean_idempotency_key = idempotency_key.strip()
    scope = f"register:{campaign_id}"
    req_hash = _compute_canonical_request_hash(body, participant.id, campaign_id)

    # Check if this is a valid idempotent replay
    stmt = select(IdempotencyRecord).where(
        IdempotencyRecord.scope == scope,
        IdempotencyRecord.key == clean_idempotency_key,
    )
    existing_record = (await db.execute(stmt)).scalar_one_or_none()

    # Only enforce rate limit on fresh requests (not existing replay with matching hash)
    if existing_record is None or existing_record.request_hash != req_hash:
        await enforce_rate_limit(
            scope="participant_register",
            key_identifier=str(participant.id),
            limit=settings.RL_REGISTER_PER_MIN,
            request_id=request_id,
        )

    res_model, status_code = await register_participant(
        db,
        campaign_id=campaign_id,
        participant_id=participant.id,
        body=body,
        idempotency_key=clean_idempotency_key,
        request_id=request_id,
    )

    response.status_code = status_code
    return res_model


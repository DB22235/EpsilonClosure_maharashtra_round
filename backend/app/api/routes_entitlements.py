"""
Seat hold, booking redemption, and hold release route handlers.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import lru_settings
from app.database import get_db
from app.dependencies import require_verified_participant
from app.middleware.rate_limit import enforce_rate_limit
from app.models.participant import Participant
from app.models.registration import IdempotencyRecord
from app.schemas.entitlement import (
    BookingRedeemRequest,
    BookingRedeemResponse,
    SeatHoldRequest,
    SeatHoldResponse,
    SeatReleaseRequest,
    SeatReleaseResponse,
)
from app.security.request_ids import get_request_id
from app.services.admission_service import _build_error
from app.services.entitlement_service import (
    _compute_hash,
    hold_entitlement_seat,
    redeem_entitlement_booking,
    release_entitlement_hold,
)

router = APIRouter(prefix="/entitlements", tags=["entitlements"])
settings = lru_settings()


@router.post(
    "/{campaign_id}/hold",
    response_model=SeatHoldResponse,
    status_code=status.HTTP_200_OK,
    summary="Acquire or re-confirm an atomic seat hold",
    description="Acquires a row-level lock on an available seat using FOR UPDATE SKIP LOCKED. Requires Idempotency-Key header.",
)
async def hold_seat_endpoint(
    campaign_id: uuid.UUID,
    request: Request,
    response: Response,
    body: SeatHoldRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    participant: Participant = Depends(require_verified_participant),
    db: AsyncSession = Depends(get_db),
) -> SeatHoldResponse:
    request_id = await get_request_id(request)

    if not idempotency_key or not idempotency_key.strip():
        raise _build_error(
            "IDEMPOTENCY_KEY_REQUIRED",
            "Idempotency-Key header is required for seat hold",
            request_id,
            status.HTTP_400_BAD_REQUEST,
        )

    clean_idempotency_key = idempotency_key.strip()
    scope = f"hold:{campaign_id}"
    req_hash = _compute_hash(
        {
            "campaign_id": str(campaign_id),
            "participant_id": str(participant.id),
            "entitlement_token": body.entitlement_token,
            "seat_id": str(body.seat_id) if body.seat_id else None,
        }
    )

    # Check for existing idempotency match before tripping rate limits
    stmt = select(IdempotencyRecord).where(
        IdempotencyRecord.scope == scope,
        IdempotencyRecord.key == clean_idempotency_key,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()

    if existing is None or existing.request_hash != req_hash:
        await enforce_rate_limit(
            scope="participant_hold",
            key_identifier=str(participant.id),
            limit=settings.RL_HOLD_PER_MIN,
            request_id=request_id,
        )

    dto, resp_status = await hold_entitlement_seat(
        db=db,
        campaign_id=campaign_id,
        participant_id=participant.id,
        body=body,
        idempotency_key=clean_idempotency_key,
        request_id=request_id,
    )
    response.status_code = resp_status
    return dto


@router.post(
    "/{campaign_id}/redeem",
    response_model=BookingRedeemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Confirm held seat and redeem entitlement into a booking",
    description="Transitions held seat and entitlement to CONFIRMED, generating a verifiable booking receipt. Requires Idempotency-Key header.",
)
async def redeem_booking_endpoint(
    campaign_id: uuid.UUID,
    request: Request,
    response: Response,
    body: BookingRedeemRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    participant: Participant = Depends(require_verified_participant),
    db: AsyncSession = Depends(get_db),
) -> BookingRedeemResponse:
    request_id = await get_request_id(request)

    if not idempotency_key or not idempotency_key.strip():
        raise _build_error(
            "IDEMPOTENCY_KEY_REQUIRED",
            "Idempotency-Key header is required for booking redemption",
            request_id,
            status.HTTP_400_BAD_REQUEST,
        )

    clean_idempotency_key = idempotency_key.strip()
    scope = f"redeem:{campaign_id}"
    req_hash = _compute_hash(
        {
            "campaign_id": str(campaign_id),
            "participant_id": str(participant.id),
            "entitlement_token": body.entitlement_token,
            "seat_id": str(body.seat_id),
        }
    )

    # Check for existing idempotency match before tripping rate limits
    stmt = select(IdempotencyRecord).where(
        IdempotencyRecord.scope == scope,
        IdempotencyRecord.key == clean_idempotency_key,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()

    if existing is None or existing.request_hash != req_hash:
        await enforce_rate_limit(
            scope="participant_redeem",
            key_identifier=str(participant.id),
            limit=settings.RL_REDEEM_PER_MIN,
            request_id=request_id,
        )

    dto, resp_status = await redeem_entitlement_booking(
        db=db,
        campaign_id=campaign_id,
        participant_id=participant.id,
        body=body,
        idempotency_key=clean_idempotency_key,
        request_id=request_id,
    )
    response.status_code = resp_status
    return dto


@router.post(
    "/{campaign_id}/release",
    response_model=SeatReleaseResponse,
    status_code=status.HTTP_200_OK,
    summary="Release active seat hold",
    description="Explicitly releases a held seat back into the available inventory pool.",
)
async def release_seat_endpoint(
    campaign_id: uuid.UUID,
    request: Request,
    body: SeatReleaseRequest,
    participant: Participant = Depends(require_verified_participant),
    db: AsyncSession = Depends(get_db),
) -> SeatReleaseResponse:
    request_id = await get_request_id(request)

    await enforce_rate_limit(
        scope="participant_release",
        key_identifier=str(participant.id),
        limit=settings.RL_HOLD_PER_MIN,
        request_id=request_id,
    )

    return await release_entitlement_hold(
        db=db,
        campaign_id=campaign_id,
        participant_id=participant.id,
        body=body,
        request_id=request_id,
    )


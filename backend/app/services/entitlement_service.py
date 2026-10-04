"""
Entitlement and Booking service orchestrating holds, two-phase redemption, and hold release.
"""

from __future__ import annotations

import hashlib
import json
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import lru_settings
from app.models.audit import AuditEvent
from app.models.campaign import Campaign
from app.models.entitlement import Entitlement
from app.models.inventory import Booking, Seat
from app.models.registration import IdempotencyRecord
from app.schemas.entitlement import (
    BookingRedeemRequest,
    BookingRedeemResponse,
    SeatHoldRequest,
    SeatHoldResponse,
    SeatReleaseRequest,
    SeatReleaseResponse,
)
from app.services.admission_service import _build_error
from app.services.campaign_service import get_campaign_or_404
from app.services.inventory_service import (
    confirm_seat_atomically,
    hold_seat_atomically,
    release_seat_hold,
)

logger = logging.getLogger(__name__)


def _compute_hash(data: dict[str, Any]) -> str:
    """Deterministic canonical SHA-256 hash for idempotency payloads."""
    serialized = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


async def _verify_entitlement(
    db: AsyncSession,
    campaign_id: uuid.UUID,
    participant_id: uuid.UUID,
    entitlement_token: str,
    request_id: str,
) -> Entitlement:
    """
    Authenticate and lock entitlement record for the participant.
    Matches either entitlement ID (UUID) or cryptographic token nonce hash.
    """
    token_uuid = None
    try:
        token_uuid = uuid.UUID(entitlement_token)
    except ValueError:
        pass

    token_sha = hashlib.sha256(entitlement_token.encode("utf-8")).hexdigest()

    conds = [
        Entitlement.nonce_hash == entitlement_token,
        Entitlement.nonce_hash == token_sha,
    ]
    if token_uuid is not None:
        conds.append(Entitlement.id == token_uuid)

    stmt = (
        select(Entitlement)
        .where(
            Entitlement.campaign_id == campaign_id,
            Entitlement.participant_id == participant_id,
            or_(*conds),
        )
        .with_for_update()
    )
    entitlement = (await db.execute(stmt)).scalar_one_or_none()

    if entitlement is None:
        raise _build_error(
            "ENTITLEMENT_NOT_FOUND",
            "No valid entitlement found matching token for participant.",
            request_id,
            status.HTTP_404_NOT_FOUND,
        )

    if entitlement.status == "CONFIRMED":
        raise _build_error(
            "ENTITLEMENT_REPLAYED",
            "This entitlement has already been redeemed and confirmed.",
            request_id,
            status.HTTP_409_CONFLICT,
        )

    now = datetime.now(timezone.utc)
    if entitlement.status == "EXPIRED" or (entitlement.expires_at and entitlement.expires_at < now):
        entitlement.status = "EXPIRED"
        raise _build_error(
            "ENTITLEMENT_EXPIRED",
            "The entitlement redemption deadline has passed.",
            request_id,
            status.HTTP_410_GONE,
        )

    return entitlement


async def hold_entitlement_seat(
    db: AsyncSession,
    *,
    campaign_id: uuid.UUID,
    participant_id: uuid.UUID,
    body: SeatHoldRequest,
    idempotency_key: str,
    request_id: str,
) -> tuple[SeatHoldResponse, int]:
    """
    Acquire or re-confirm a temporary seat hold for an authorized entitlement winner.
    """
    scope = f"hold:{campaign_id}"
    req_hash = _compute_hash(
        {
            "campaign_id": str(campaign_id),
            "participant_id": str(participant_id),
            "entitlement_token": body.entitlement_token,
            "seat_id": str(body.seat_id) if body.seat_id else None,
        }
    )

    # 1. Check Idempotency
    stmt_idemp = select(IdempotencyRecord).where(
        IdempotencyRecord.scope == scope,
        IdempotencyRecord.key == idempotency_key,
    )
    cached = (await db.execute(stmt_idemp)).scalar_one_or_none()
    if cached is not None:
        if cached.request_hash == req_hash:
            return SeatHoldResponse(**cached.response_body_json), cached.response_status
        raise _build_error(
            "IDEMPOTENCY_CONFLICT",
            "A different request was already submitted with this idempotency key.",
            request_id,
            status.HTTP_409_CONFLICT,
        )

    # 2. Campaign validation
    campaign = await get_campaign_or_404(db, campaign_id, request_id)
    if campaign.status not in ("CLAIMING", "FROZEN", "ACTIVE", "OPEN"):
        raise _build_error(
            "CAMPAIGN_NOT_IN_CLAIM_STATE",
            f"Campaign is in {campaign.status} state; seat holds are not currently open.",
            request_id,
            status.HTTP_409_CONFLICT,
        )

    # 3. Verify entitlement
    entitlement = await _verify_entitlement(
        db, campaign_id, participant_id, body.entitlement_token, request_id
    )

    # 4. Hold seat atomically
    settings = lru_settings()
    duration = body.hold_duration_seconds or settings.SEAT_HOLD_SECONDS
    seat = await hold_seat_atomically(
        db,
        campaign_id=campaign_id,
        participant_id=participant_id,
        entitlement_id=entitlement.id,
        requested_seat_id=body.seat_id,
        hold_duration_seconds=duration,
        request_id=request_id,
    )

    # Update entitlement state
    entitlement.held_seat_id = seat.id
    entitlement.status = "HELD"
    entitlement.updated_at = datetime.now(timezone.utc)

    # Audit log
    db.add(
        AuditEvent(
            campaign_id=campaign_id,
            participant_id=participant_id,
            actor_type="USER",
            actor_id=participant_id,
            event_type="SEAT_HOLD_CREATED",
            request_id=request_id,
            metadata_json={
                "seat_id": str(seat.id),
                "seat_label": seat.seat_label,
                "entitlement_id": str(entitlement.id),
                "hold_expires_at": seat.hold_expires_at.isoformat() if seat.hold_expires_at else None,
            },
        )
    )

    resp_dto = SeatHoldResponse(
        seat_id=seat.id,
        seat_label=seat.seat_label,
        section=seat.section,
        row_label=seat.row_label,
        seat_number=seat.seat_number,
        hold_expires_at=seat.hold_expires_at,
        entitlement_id=entitlement.id,
        message="Seat successfully held.",
    )

    # Store Idempotency
    now = datetime.now(timezone.utc)
    idemp_rec = IdempotencyRecord(
        id=uuid.uuid4(),
        scope=scope,
        key=idempotency_key,
        actor_id=participant_id,
        campaign_id=campaign_id,
        request_hash=req_hash,
        response_status=status.HTTP_200_OK,
        response_body_json=json.loads(resp_dto.model_dump_json()),
        resource_type="SEAT_HOLD",
        resource_id=seat.id,
        expires_at=now + timedelta(hours=24),
        created_at=now,
    )
    db.add(idemp_rec)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        logger.error("Integrity error during seat hold: %s", exc)
        raise _build_error(
            "SEAT_HOLD_FAILED",
            "Could not finalize seat hold due to database contention.",
            request_id,
            status.HTTP_409_CONFLICT,
        )

    return resp_dto, status.HTTP_200_OK


async def redeem_entitlement_booking(
    db: AsyncSession,
    *,
    campaign_id: uuid.UUID,
    participant_id: uuid.UUID,
    body: BookingRedeemRequest,
    idempotency_key: str,
    request_id: str,
) -> tuple[BookingRedeemResponse, int]:
    """
    Redeem entitlement, confirm seat reservation, and generate authoritative booking receipt.
    """
    scope = f"redeem:{campaign_id}"
    req_hash = _compute_hash(
        {
            "campaign_id": str(campaign_id),
            "participant_id": str(participant_id),
            "entitlement_token": body.entitlement_token,
            "seat_id": str(body.seat_id),
        }
    )

    # 1. Check Idempotency
    stmt_idemp = select(IdempotencyRecord).where(
        IdempotencyRecord.scope == scope,
        IdempotencyRecord.key == idempotency_key,
    )
    cached = (await db.execute(stmt_idemp)).scalar_one_or_none()
    if cached is not None:
        if cached.request_hash == req_hash:
            return BookingRedeemResponse(**cached.response_body_json), cached.response_status
        raise _build_error(
            "IDEMPOTENCY_CONFLICT",
            "A different request was already submitted with this idempotency key.",
            request_id,
            status.HTTP_409_CONFLICT,
        )

    # 2. Campaign validation
    campaign = await get_campaign_or_404(db, campaign_id, request_id)
    if campaign.status not in ("CLAIMING", "FROZEN", "ACTIVE", "OPEN"):
        raise _build_error(
            "CAMPAIGN_NOT_IN_CLAIM_STATE",
            f"Campaign is in {campaign.status} state; booking redemption is not open.",
            request_id,
            status.HTTP_409_CONFLICT,
        )

    # 3. Verify entitlement
    entitlement = await _verify_entitlement(
        db, campaign_id, participant_id, body.entitlement_token, request_id
    )

    # 4. Confirm seat atomically
    seat = await confirm_seat_atomically(
        db,
        campaign_id=campaign_id,
        seat_id=body.seat_id,
        entitlement_id=entitlement.id,
        participant_id=participant_id,
        request_id=request_id,
    )

    now = datetime.now(timezone.utc)

    # 5. Create Booking record
    receipt_id = f"rcpt_{campaign_id.hex[:8]}_{secrets.token_hex(8)}"
    booking = Booking(
        id=uuid.uuid4(),
        campaign_id=campaign_id,
        participant_id=participant_id,
        entitlement_id=entitlement.id,
        seat_id=seat.id,
        status="CONFIRMED",
        receipt_id=receipt_id,
        confirmed_at=now,
        created_at=now,
    )
    db.add(booking)

    # 6. Update entitlement status -> CONFIRMED
    entitlement.status = "CONFIRMED"
    entitlement.redeemed_at = now
    entitlement.held_seat_id = seat.id
    entitlement.updated_at = now

    # 7. Audit log
    db.add(
        AuditEvent(
            campaign_id=campaign_id,
            participant_id=participant_id,
            actor_type="USER",
            actor_id=participant_id,
            event_type="BOOKING_CONFIRMED",
            request_id=request_id,
            metadata_json={
                "booking_id": str(booking.id),
                "receipt_id": receipt_id,
                "seat_id": str(seat.id),
                "seat_label": seat.seat_label,
                "entitlement_id": str(entitlement.id),
            },
        )
    )

    resp_dto = BookingRedeemResponse(
        booking_id=booking.id,
        receipt_id=receipt_id,
        campaign_id=campaign_id,
        participant_id=participant_id,
        seat_id=seat.id,
        seat_label=seat.seat_label,
        section=seat.section,
        row_label=seat.row_label,
        seat_number=seat.seat_number,
        confirmed_at=now,
        message="Booking confirmed successfully.",
    )

    # Store Idempotency
    idemp_rec = IdempotencyRecord(
        id=uuid.uuid4(),
        scope=scope,
        key=idempotency_key,
        actor_id=participant_id,
        campaign_id=campaign_id,
        request_hash=req_hash,
        response_status=status.HTTP_201_CREATED,
        response_body_json=json.loads(resp_dto.model_dump_json()),
        resource_type="BOOKING",
        resource_id=booking.id,
        expires_at=now + timedelta(days=7),
        created_at=now,
    )
    db.add(idemp_rec)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        logger.error("Integrity error during booking redemption: %s", exc)
        raise _build_error(
            "BOOKING_FAILED",
            "Could not confirm booking due to concurrency conflict.",
            request_id,
            status.HTTP_409_CONFLICT,
        )

    return resp_dto, status.HTTP_201_CREATED


async def release_entitlement_hold(
    db: AsyncSession,
    *,
    campaign_id: uuid.UUID,
    participant_id: uuid.UUID,
    body: SeatReleaseRequest,
    request_id: str,
) -> SeatReleaseResponse:
    """
    Explicitly release a held seat reservation prior to hold expiration.
    """
    entitlement = await _verify_entitlement(
        db, campaign_id, participant_id, body.entitlement_token, request_id
    )

    released = await release_seat_hold(
        db,
        campaign_id=campaign_id,
        seat_id=body.seat_id,
        entitlement_id=entitlement.id,
        request_id=request_id,
    )

    if entitlement.held_seat_id == body.seat_id:
        entitlement.held_seat_id = None
        entitlement.status = "SELECTED"
        entitlement.updated_at = datetime.now(timezone.utc)

    # Audit log
    db.add(
        AuditEvent(
            campaign_id=campaign_id,
            participant_id=participant_id,
            actor_type="USER",
            actor_id=participant_id,
            event_type="SEAT_HOLD_RELEASED",
            request_id=request_id,
            metadata_json={
                "seat_id": str(body.seat_id),
                "entitlement_id": str(entitlement.id),
                "was_held": released,
            },
        )
    )

    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        logger.error("Error committing seat release: %s", exc)
        raise _build_error(
            "RELEASE_FAILED",
            "Could not release seat hold.",
            request_id,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return SeatReleaseResponse(
        status="RELEASED",
        seat_id=body.seat_id,
        message="Seat hold successfully released.",
    )

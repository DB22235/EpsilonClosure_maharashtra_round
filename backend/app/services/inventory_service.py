"""
Inventory service for atomic seat locking, allocation, confirmation, and release.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import Seat
from app.services.admission_service import _build_error

logger = logging.getLogger(__name__)


async def hold_seat_atomically(
    db: AsyncSession,
    *,
    campaign_id: uuid.UUID,
    participant_id: uuid.UUID,
    entitlement_id: uuid.UUID,
    requested_seat_id: uuid.UUID | None = None,
    hold_duration_seconds: int = 120,
    request_id: str = "",
) -> Seat:
    """
    Atomically acquire or re-confirm a hold on an available seat using row-level locking.
    Uses FOR UPDATE SKIP LOCKED when auto-assigning to prevent concurrent contention and overselling.
    """
    now = datetime.now(timezone.utc)

    # 1. Release any previously held seats by this entitlement that are not the target
    old_held_stmt = (
        select(Seat)
        .where(
            Seat.campaign_id == campaign_id,
            Seat.held_by_entitlement_id == entitlement_id,
            Seat.status == "HELD",
        )
        .with_for_update()
    )
    old_held_seats = (await db.execute(old_held_stmt)).scalars().all()

    target_seat: Seat | None = None

    if requested_seat_id is not None:
        # Specific seat requested
        stmt = (
            select(Seat)
            .where(
                Seat.id == requested_seat_id,
                Seat.campaign_id == campaign_id,
            )
            .with_for_update()
        )
        target_seat = (await db.execute(stmt)).scalar_one_or_none()

        if target_seat is None:
            raise _build_error(
                "SEAT_NOT_FOUND",
                f"Seat {requested_seat_id} not found in campaign.",
                request_id,
                status.HTTP_404_NOT_FOUND,
            )

        if target_seat.status == "CONFIRMED":
            raise _build_error(
                "SEAT_ALREADY_CONFIRMED",
                "The selected seat is already confirmed and booked.",
                request_id,
                status.HTTP_409_CONFLICT,
            )

        if target_seat.status == "HELD":
            is_our_hold = target_seat.held_by_entitlement_id == entitlement_id
            is_expired = target_seat.hold_expires_at is not None and target_seat.hold_expires_at < now

            if not is_our_hold and not is_expired:
                raise _build_error(
                    "SEAT_UNAVAILABLE",
                    "The selected seat is currently held by another user.",
                    request_id,
                    status.HTTP_409_CONFLICT,
                )
    else:
        # Auto-assign: check if we already hold an unexpired seat
        for s in old_held_seats:
            if s.hold_expires_at and s.hold_expires_at >= now:
                target_seat = s
                break

        if target_seat is None:
            # Pick first available seat with SKIP LOCKED
            stmt = (
                select(Seat)
                .where(
                    Seat.campaign_id == campaign_id,
                    or_(
                        Seat.status == "AVAILABLE",
                        and_(Seat.status == "HELD", Seat.hold_expires_at < now),
                    ),
                )
                .order_by(Seat.seat_label.asc())
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            target_seat = (await db.execute(stmt)).scalar_one_or_none()

            if target_seat is None:
                raise _build_error(
                    "NO_SEATS_AVAILABLE",
                    "No available seats remaining in this campaign.",
                    request_id,
                    status.HTTP_409_CONFLICT,
                )

    # Release any other seats previously held by this entitlement
    for old_s in old_held_seats:
        if old_s.id != target_seat.id:
            old_s.status = "AVAILABLE"
            old_s.held_by_entitlement_id = None
            old_s.hold_expires_at = None
            old_s.version += 1

    # Apply hold
    target_seat.status = "HELD"
    target_seat.held_by_entitlement_id = entitlement_id
    target_seat.hold_expires_at = now + timedelta(seconds=hold_duration_seconds)
    target_seat.version += 1

    return target_seat


async def confirm_seat_atomically(
    db: AsyncSession,
    *,
    campaign_id: uuid.UUID,
    seat_id: uuid.UUID,
    entitlement_id: uuid.UUID,
    participant_id: uuid.UUID,
    request_id: str = "",
) -> Seat:
    """
    Atomically confirm a held seat into a final booking state.
    """
    now = datetime.now(timezone.utc)

    stmt = (
        select(Seat)
        .where(
            Seat.id == seat_id,
            Seat.campaign_id == campaign_id,
        )
        .with_for_update()
    )
    seat = (await db.execute(stmt)).scalar_one_or_none()

    if seat is None:
        raise _build_error(
            "SEAT_NOT_FOUND",
            f"Seat {seat_id} not found in campaign.",
            request_id,
            status.HTTP_404_NOT_FOUND,
        )

    if seat.status == "CONFIRMED":
        if seat.confirmed_by_participant_id == participant_id:
            return seat
        raise _build_error(
            "SEAT_ALREADY_CONFIRMED",
            "This seat has already been booked by another participant.",
            request_id,
            status.HTTP_409_CONFLICT,
        )

    if seat.status != "HELD" or seat.held_by_entitlement_id != entitlement_id:
        raise _build_error(
            "SEAT_HOLD_INVALID",
            "Participant does not hold an active reservation for this seat.",
            request_id,
            status.HTTP_409_CONFLICT,
        )

    if seat.hold_expires_at is not None and seat.hold_expires_at < now:
        seat.status = "AVAILABLE"
        seat.held_by_entitlement_id = None
        seat.hold_expires_at = None
        seat.version += 1
        raise _build_error(
            "HOLD_EXPIRED",
            "The hold on this seat has expired. Please request a new hold.",
            request_id,
            status.HTTP_410_GONE,
        )

    seat.status = "CONFIRMED"
    seat.confirmed_by_participant_id = participant_id
    seat.confirmed_at = now
    seat.held_by_entitlement_id = None
    seat.hold_expires_at = None
    seat.version += 1

    return seat


async def release_seat_hold(
    db: AsyncSession,
    *,
    campaign_id: uuid.UUID,
    seat_id: uuid.UUID,
    entitlement_id: uuid.UUID,
    request_id: str = "",
) -> bool:
    """
    Explicitly release a held seat back to the pool.
    """
    stmt = (
        select(Seat)
        .where(
            Seat.id == seat_id,
            Seat.campaign_id == campaign_id,
        )
        .with_for_update()
    )
    seat = (await db.execute(stmt)).scalar_one_or_none()

    if seat is None:
        raise _build_error(
            "SEAT_NOT_FOUND",
            f"Seat {seat_id} not found in campaign.",
            request_id,
            status.HTTP_404_NOT_FOUND,
        )

    if seat.status == "HELD" and seat.held_by_entitlement_id == entitlement_id:
        seat.status = "AVAILABLE"
        seat.held_by_entitlement_id = None
        seat.hold_expires_at = None
        seat.version += 1
        return True

    return False


async def get_campaign_seats(
    db: AsyncSession,
    campaign_id: uuid.UUID,
    limit: int = 500,
    offset: int = 0,
) -> dict:
    """
    Fetch live seat inventory for a campaign, reconciling expired holds on the fly.
    """
    now = datetime.now(timezone.utc)

    stmt = (
        select(Seat)
        .where(Seat.campaign_id == campaign_id)
        .order_by(Seat.section, Seat.row_label, Seat.seat_number, Seat.seat_label)
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    seats = result.scalars().all()

    seat_items = []
    available_count = 0
    held_count = 0
    confirmed_count = 0

    for s in seats:
        st = s.status
        if st == "HELD" and s.hold_expires_at and s.hold_expires_at < now:
            st = "AVAILABLE"

        if st == "AVAILABLE":
            available_count += 1
        elif st == "HELD":
            held_count += 1
        elif st == "CONFIRMED":
            confirmed_count += 1

        seat_items.append(
            {
                "id": s.id,
                "seat_label": s.seat_label,
                "section": s.section,
                "row_label": s.row_label,
                "seat_number": s.seat_number,
                "status": st,
                "hold_expires_at": s.hold_expires_at if st == "HELD" else None,
            }
        )

    count_stmt = select(func.count(Seat.id)).where(Seat.campaign_id == campaign_id)
    total_count = (await db.execute(count_stmt)).scalar_one() or len(seat_items)

    return {
        "campaign_id": campaign_id,
        "total_seats": total_count,
        "available_seats": available_count,
        "held_seats": held_count,
        "confirmed_seats": confirmed_count,
        "seats": seat_items,
    }


"""
Pydantic schemas for atomic seat holds, entitlement redemption, and hold release.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SeatHoldRequest(BaseModel):
    """Payload to request holding a seat."""

    entitlement_token: str = Field(
        description="Entitlement ID or cryptographic token awarded during lottery.",
    )
    seat_id: uuid.UUID | None = Field(
        default=None,
        description="Optional specific seat ID to hold. If omitted, best available seat is assigned.",
    )
    hold_duration_seconds: int | None = Field(
        default=120,
        description="Duration in seconds for the hold.",
    )


class SeatHoldResponse(BaseModel):
    """Authoritative response confirming atomic seat hold."""

    seat_id: uuid.UUID
    seat_label: str
    section: str | None = None
    row_label: str | None = None
    seat_number: int | None = None
    hold_expires_at: datetime
    entitlement_id: uuid.UUID
    message: str = "Seat successfully held."

    model_config = ConfigDict(from_attributes=True)


class BookingRedeemRequest(BaseModel):
    """Payload to redeem entitlement and confirm booking."""

    entitlement_token: str = Field(
        description="Entitlement ID or cryptographic token.",
    )
    seat_id: uuid.UUID = Field(
        description="ID of the held seat to confirm into a booking.",
    )


class BookingRedeemResponse(BaseModel):
    """Authoritative response confirming two-phase booking redemption."""

    booking_id: uuid.UUID
    receipt_id: str
    campaign_id: uuid.UUID
    participant_id: uuid.UUID
    seat_id: uuid.UUID
    seat_label: str
    section: str | None = None
    row_label: str | None = None
    seat_number: int | None = None
    confirmed_at: datetime
    message: str = "Booking confirmed successfully."

    model_config = ConfigDict(from_attributes=True)


class SeatReleaseRequest(BaseModel):
    """Payload to release an active seat hold."""

    entitlement_token: str = Field(
        description="Entitlement ID or cryptographic token.",
    )
    seat_id: uuid.UUID = Field(
        description="ID of the held seat to release.",
    )


class SeatReleaseResponse(BaseModel):
    """Response confirming release of held seat back to inventory pool."""

    status: str = "RELEASED"
    seat_id: uuid.UUID
    message: str = "Seat hold successfully released."

    model_config = ConfigDict(from_attributes=True)


class SeatItemResponse(BaseModel):
    """Details of a single seat in the venue seat map."""

    id: uuid.UUID
    seat_label: str
    section: str | None = None
    row_label: str | None = None
    seat_number: int | None = None
    status: str  # AVAILABLE, HELD, CONFIRMED
    hold_expires_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class SeatMapResponse(BaseModel):
    """Live seat map for a campaign."""

    campaign_id: uuid.UUID
    total_seats: int
    available_seats: int
    held_seats: int
    confirmed_seats: int
    seats: list[SeatItemResponse]

    model_config = ConfigDict(from_attributes=True)


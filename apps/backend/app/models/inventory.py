"""
Seat and Booking models.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Seat(Base, UUIDMixin, TimestampMixin):
    """
    Allocatable seat in an event campaign.
    Circular foreign key to entitlements uses use_alter=True to resolve DDL dependency cycles.
    """

    __tablename__ = "seats"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    seat_label: Mapped[str] = mapped_column(String(50), nullable=False)
    section: Mapped[str | None] = mapped_column(String(50), nullable=True)
    row_label: Mapped[str | None] = mapped_column(String(20), nullable=True)
    seat_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="AVAILABLE")
    held_by_entitlement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("entitlements.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
    )
    hold_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    confirmed_by_participant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("participants.id", ondelete="SET NULL"),
        nullable=True,
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")

    __table_args__ = (
        UniqueConstraint("campaign_id", "seat_label", name="uq_seats_campaign_label"),
        CheckConstraint("status IN ('AVAILABLE','HELD','CONFIRMED')", name="ck_seats_status"),
        Index("ix_seats_campaign_status", "campaign_id", "status"),
    )


class Booking(Base, UUIDMixin):
    """
    Confirmed booking reservation binding participant, seat, and entitlement.
    """

    __tablename__ = "bookings"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"),
        nullable=False,
    )
    entitlement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("entitlements.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    seat_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("seats.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="CONFIRMED")
    confirmed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    receipt_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

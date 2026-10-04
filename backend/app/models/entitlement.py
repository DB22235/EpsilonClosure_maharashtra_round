"""
Entitlement model for allocation redemption rights.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Entitlement(Base, UUIDMixin, TimestampMixin):
    """
    Entitlement grant giving a participant the right to claim/hold/book a seat.
    """

    __tablename__ = "entitlements"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"),
        nullable=False,
    )
    lottery_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lottery_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    nonce_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="SELECTED",
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    held_seat_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("seats.id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('SELECTED','CLAIM_PENDING','HELD','CONFIRMED','EXPIRED')",
            name="ck_entitlements_status",
        ),
        Index("ix_entitlements_campaign_participant", "campaign_id", "participant_id"),
        Index("ix_entitlements_status_expires", "status", "expires_at"),
    )

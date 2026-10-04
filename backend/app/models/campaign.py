"""
Campaign and CampaignPolicySnapshot models.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class CampaignStatus(str, Enum):
    """Lifecycle status values for campaigns."""

    DRAFT = "DRAFT"
    PREPARING = "PREPARING"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    FROZEN = "FROZEN"
    DRAWING = "DRAWING"
    CLAIMING = "CLAIMING"
    COMPLETED = "COMPLETED"


class Campaign(Base, UUIDMixin, TimestampMixin):
    """
    Campaign entity representing a drop event.
    """

    __tablename__ = "campaigns"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    venue: Mapped[str | None] = mapped_column(String(255), nullable=True)
    event_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    registration_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    registration_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    redemption_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    max_tickets_per_participant: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="1",
    )
    allocation_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default="UNIFORM_LOTTERY",
    )
    standby_policy: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default="FIXED_ORDER",
    )
    policy_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default="v1.0",
    )
    policy_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="DRAFT")
    admission_paused: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    registration_paused: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    redemption_paused: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("profiles.id"), nullable=False)

    __table_args__ = (
        CheckConstraint("capacity > 0", name="ck_campaigns_capacity_positive"),
        CheckConstraint("max_tickets_per_participant > 0", name="ck_campaigns_max_tickets_positive"),
        CheckConstraint(
            "status IN ('DRAFT','PREPARING','OPEN','CLOSED','FROZEN','DRAWING','CLAIMING','COMPLETED')",
            name="ck_campaigns_status",
        ),
    )


class CampaignPolicySnapshot(Base, UUIDMixin):
    """
    Immutable policy snapshot captured for a campaign.
    """

    __tablename__ = "campaign_policy_snapshots"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    policy_version: Mapped[str] = mapped_column(String(50), nullable=False)
    policy_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    snapshot_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

"""
Registration and IdempotencyRecord models.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Registration(Base, UUIDMixin, TimestampMixin):
    """
    Participant registration entry for a campaign.
    """

    __tablename__ = "registrations"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"),
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="RECEIVED")
    eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    risk_level: Mapped[str] = mapped_column(String(10), nullable=False, server_default="LOW")
    reason_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("campaign_id", "participant_id", name="uq_registrations_campaign_participant"),
        UniqueConstraint("campaign_id", "idempotency_key", name="uq_registrations_campaign_idempotency"),
        CheckConstraint(
            "status IN ('RECEIVED','VALIDATING','ACCEPTED','DUPLICATE','REJECTED','QUARANTINED')",
            name="ck_registrations_status",
        ),
        Index("ix_registrations_campaign_status", "campaign_id", "status"),
    )


class IdempotencyRecord(Base, UUIDMixin):
    """
    Generic record for deduplicating mutation requests.
    """

    __tablename__ = "idempotency_records"

    scope: Mapped[str] = mapped_column(String(50), nullable=False)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("campaigns.id", ondelete="SET NULL"),
        nullable=True,
    )
    request_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    response_status: Mapped[int] = mapped_column(Integer, nullable=False)
    response_body_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("scope", "key", name="uq_idempotency_scope_key"),
        Index("ix_idempotency_expires", "expires_at"),
    )

"""
AdmissionPermit model for cryptographic admission passes.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class AdmissionPermit(Base, UUIDMixin):
    """
    Cryptographic admission permit token granting specific operations.
    """

    __tablename__ = "admission_permits"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"),
        nullable=False,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    nonce: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    allowed_operation: Mapped[str] = mapped_column(String(50), nullable=False)
    key_id: Mapped[str] = mapped_column(String(100), nullable=False)
    signature: Mapped[str] = mapped_column(Text, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_admission_permits_campaign_participant", "campaign_id", "participant_id"),
        Index("ix_admission_permits_nonce", "nonce"),
    )

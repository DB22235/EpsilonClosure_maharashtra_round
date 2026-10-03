"""
Participant, Profile, and Session models.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Profile(Base):
    """
    User profile linked to Supabase auth.users.
    Primary key matches Supabase auth.users.id, so no auto-generated default is used.
    """

    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(10), nullable=False, server_default="USER")
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    phone_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    institute_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint("role IN ('USER','ADMIN')", name="ck_profiles_role"),
    )


class Participant(Base, UUIDMixin, TimestampMixin):
    """
    Participant record representing a user's verification and risk state in Fair Drop.
    """

    __tablename__ = "participants"

    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    email_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    phone_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    verification_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="PENDING",
    )
    risk_level: Mapped[str] = mapped_column(String(10), nullable=False, server_default="LOW")

    __table_args__ = (
        CheckConstraint(
            "verification_status IN ('PENDING','VERIFIED','REJECTED')",
            name="ck_participants_verification",
        ),
        CheckConstraint(
            "risk_level IN ('LOW','MEDIUM','HIGH')",
            name="ck_participants_risk",
        ),
    )


class Session(Base, UUIDMixin):
    """
    Participant admission and interaction session.
    Note: This is the domain Session model, not the SQLAlchemy AsyncSession.
    """

    __tablename__ = "sessions"

    participant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"),
        nullable=False,
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("campaigns.id", ondelete="SET NULL"),
        nullable=True,
    )
    supabase_subject: Mapped[uuid.UUID] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    absolute_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    idle_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="ACTIVE")
    last_ip_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    user_agent_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE','EXPIRED','REVOKED')", name="ck_sessions_status"),
        Index("ix_sessions_participant_campaign", "participant_id", "campaign_id"),
    )

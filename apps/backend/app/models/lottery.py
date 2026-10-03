"""
LotteryRun and LotteryEntry models.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class LotteryRun(Base, UUIDMixin):
    """
    Cryptographically verifiable lottery execution record for a campaign.
    Only one draw is allowed per campaign (enforced by unique=True on campaign_id).
    """

    __tablename__ = "lottery_runs"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    policy_version: Mapped[str] = mapped_column(String(50), nullable=False)
    policy_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    roster_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    randomness_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    randomness_commitment: Mapped[str] = mapped_column(String(255), nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(50), nullable=False)
    winner_count: Mapped[int] = mapped_column(Integer, nullable=False)
    standby_count: Mapped[int] = mapped_column(Integer, nullable=False)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    executed_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("profiles.id"), nullable=False)


class LotteryEntry(Base, UUIDMixin):
    """
    Individual participant result in a lottery run.
    """

    __tablename__ = "lottery_entries"

    lottery_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lottery_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"),
        nullable=False,
    )
    registration_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("registrations.id", ondelete="CASCADE"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    selected: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    standby_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "lottery_run_id",
            "participant_id",
            name="uq_lottery_entries_run_participant",
        ),
        Index("ix_lottery_entries_run_selected", "lottery_run_id", "selected"),
        Index("ix_lottery_entries_standby", "lottery_run_id", "standby_position"),
    )

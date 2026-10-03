"""
Models package exports.

Registers all declarative models on Base.metadata for Alembic discovery and init_db.
"""

from __future__ import annotations

from app.models.admission import AdmissionPermit
from app.models.audit import AuditEvent, MetricEvent, StandbyPromotion
from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.campaign import Campaign, CampaignPolicySnapshot, CampaignStatus
from app.models.challenge import Challenge
from app.models.entitlement import Entitlement
from app.models.inventory import Booking, Seat
from app.models.lottery import LotteryEntry, LotteryRun
from app.models.participant import Participant, Profile, Session
from app.models.registration import IdempotencyRecord, Registration

__all__ = [
    "Base",
    "UUIDMixin",
    "TimestampMixin",
    "Profile",
    "Participant",
    "Session",
    "Campaign",
    "CampaignPolicySnapshot",
    "CampaignStatus",
    "Registration",
    "IdempotencyRecord",
    "AdmissionPermit",
    "Challenge",
    "LotteryRun",
    "LotteryEntry",
    "Seat",
    "Booking",
    "Entitlement",
    "AuditEvent",
    "StandbyPromotion",
    "MetricEvent",
]

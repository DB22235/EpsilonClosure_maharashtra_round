"""
Pydantic schemas for campaign metrics and cryptographic fairness evidence.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CampaignMetricsResponse(BaseModel):
    """Real-time operational and allocation metrics for a campaign."""

    campaign_id: uuid.UUID
    name: str
    status: str
    capacity: int
    registrations_count: int = Field(description="Total registration submissions.")
    eligible_roster_count: int = Field(description="Accepted eligible registrations locked for draw.")
    winners_count: int = Field(description="Total winners awarded allocation rights.")
    standby_count: int = Field(description="Total participants positioned in standby queue.")
    seats_total: int = Field(description="Total seat inventory configured.")
    seats_available: int = Field(description="Current unassigned available seats.")
    seats_held: int = Field(description="Seats currently under temporary hold.")
    seats_confirmed: int = Field(description="Seats with confirmed booking redemption.")
    bookings_count: int = Field(description="Total completed bookings.")
    challenges_passed: int = Field(description="Count of successfully verified proof-of-human challenges.")
    challenges_failed: int = Field(description="Count of failed/expired verification challenges.")
    holds_expired_count: int = Field(description="Count of seat holds that expired.")
    entitlements_expired_count: int = Field(description="Count of entitlements that expired without redemption.")
    duplicate_allocation_count: int = Field(
        default=0,
        description="Duplicate participant allocation violations (strictly 0).",
    )
    oversell_count: int = Field(
        default=0,
        description="Confirmed seats exceeding campaign capacity (strictly 0).",
    )
    generated_at: datetime = Field(description="Metrics generation timestamp.")

    model_config = ConfigDict(from_attributes=True)


class FairnessEvidenceResponse(BaseModel):
    """Authoritative cryptographic fairness and draw reproducibility proof."""

    campaign_id: uuid.UUID
    roster_hash: str = Field(description="SHA-256 hash of immutable locked roster.")
    randomness_seed: str | None = Field(
        default=None,
        description="Revealed draw seed (included in admin response; redacted for public).",
    )
    randomness_commitment: str = Field(description="SHA-256 commitment of the draw seed.")
    lottery_run_id: uuid.UUID | None = Field(default=None, description="Lottery run identifier.")
    total_eligible: int = Field(description="Total eligible participants in the draw.")
    capacity: int = Field(description="Ticket allocation quota.")
    selection_probability: float = Field(
        description="Theoretical probability of winning: min(1.0, capacity / total_eligible).",
    )
    statement: str = Field(
        default="selection probability is independent of request rate",
        description="Mathematical fairness guarantee statement.",
    )
    reproducibility_notes: str = Field(
        description="Instructions and algorithm parameters for independent third-party verification.",
    )
    evidence_hash: str = Field(description="Deterministic SHA-256 hash over canonical evidence dictionary.")
    draw_executed_at: datetime | None = Field(
        default=None,
        description="Timestamp when lottery draw was executed.",
    )

    model_config = ConfigDict(from_attributes=True)

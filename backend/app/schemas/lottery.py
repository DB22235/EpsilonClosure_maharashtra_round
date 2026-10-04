"""
Pydantic schemas for Roster Freeze, Lottery Draw, and Results.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FreezeRosterResponse(BaseModel):
    """Response returned upon freezing campaign registration roster."""

    campaign_id: uuid.UUID
    status: str = Field(description="Updated campaign status (e.g. FROZEN).")
    roster_count: int = Field(description="Total count of eligible accepted registrations locked for draw.")
    frozen_at: datetime
    message: str = Field(default="Campaign registration roster successfully frozen.")

    model_config = ConfigDict(from_attributes=True)


class LotteryDrawRequest(BaseModel):
    """Optional payload for executing lottery draw."""

    randomness_seed: str | None = Field(
        default=None,
        description="Optional operator-provided 32-char hex seed. Auto-generated via secrets.token_hex(16) if omitted.",
    )


class LotteryDrawResponse(BaseModel):
    """Authoritative response confirming execution of deterministic uniform lottery draw."""

    run_id: uuid.UUID
    campaign_id: uuid.UUID
    seed: str = Field(description="Revealed randomness reference / seed for audit verification.")
    seed_hash: str = Field(description="SHA-256 commitment of the seed.")
    total_eligible: int = Field(description="Total participants considered in the draw.")
    total_winners: int = Field(description="Total number of winning allocations awarded.")
    total_waitlisted: int = Field(description="Total number of non-winning participants waitlisted.")
    inventory_cap: int = Field(description="Total quota/inventory available.")
    executed_at: datetime
    message: str = Field(default="Lottery draw executed successfully.")

    model_config = ConfigDict(from_attributes=True)


class ParticipantResultResponse(BaseModel):
    """Participant query response for lottery outcome and entitlement status."""

    campaign_id: uuid.UUID
    participant_id: uuid.UUID
    status: str = Field(description="Result status: 'WON', 'WAITLISTED', or 'NOT_REGISTERED'.")
    is_winner: bool = Field(description="Whether participant secured a winning allocation.")
    rank: int | None = Field(default=None, description="Assigned random draw position (1-indexed).")
    entitlement_id: uuid.UUID | None = Field(default=None, description="ID of generated entitlement if winner.")
    entitlement_status: str | None = Field(default=None, description="Status of entitlement (e.g. SELECTED).")
    expires_at: datetime | None = Field(default=None, description="Expiration time window for claim/purchase.")
    randomness_commitment: str | None = Field(default=None, description="SHA-256 commitment hash of draw seed.")
    draw_executed_at: datetime | None = Field(default=None, description="Timestamp when lottery draw was finalized.")

    model_config = ConfigDict(from_attributes=True)

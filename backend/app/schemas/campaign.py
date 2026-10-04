"""
Pydantic schemas for Campaign management, public listing, and participant recovery.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal
from typing_extensions import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CampaignCreateRequest(BaseModel):
    """Payload for creating a new campaign in DRAFT state."""

    name: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=5000)
    venue: str | None = Field(default=None, max_length=255)
    event_start: datetime | None = None
    capacity: int = Field(gt=0, le=100000)
    registration_start: datetime
    registration_end: datetime
    redemption_deadline: datetime
    max_tickets_per_participant: int = Field(default=1, gt=0, le=100)
    allocation_method: Literal["UNIFORM_LOTTERY"] = "UNIFORM_LOTTERY"
    standby_policy: Literal["FIXED_ORDER"] = "FIXED_ORDER"
    policy_version: str = Field(default="v1.0", max_length=50)

    @model_validator(mode="after")
    def validate_timeline(self) -> Self:
        if self.registration_end <= self.registration_start:
            raise ValueError("registration_end must be strictly after registration_start")
        if self.redemption_deadline <= self.registration_end:
            raise ValueError("redemption_deadline must be strictly after registration_end")
        return self


class CampaignUpdateRequest(BaseModel):
    """Payload for updating an existing DRAFT or PREPARING campaign."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1, max_length=5000)
    venue: str | None = Field(default=None, max_length=255)
    event_start: datetime | None = None
    capacity: int | None = Field(default=None, gt=0, le=100000)
    registration_start: datetime | None = None
    registration_end: datetime | None = None
    redemption_deadline: datetime | None = None
    max_tickets_per_participant: int | None = Field(default=None, gt=0, le=100)
    allocation_method: Literal["UNIFORM_LOTTERY"] | None = None
    standby_policy: Literal["FIXED_ORDER"] | None = None
    policy_version: str | None = Field(default=None, max_length=50)

    @model_validator(mode="after")
    def validate_chronology_if_provided(self) -> Self:
        if self.registration_start and self.registration_end:
            if self.registration_end <= self.registration_start:
                raise ValueError("registration_end must be strictly after registration_start")
        if self.registration_end and self.redemption_deadline:
            if self.redemption_deadline <= self.registration_end:
                raise ValueError("redemption_deadline must be strictly after registration_end")
        return self


class CampaignPublicResponse(BaseModel):
    """Public representation of a published campaign."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str
    venue: str | None
    event_start: datetime | None
    capacity: int
    registration_start: datetime
    registration_end: datetime
    redemption_deadline: datetime
    max_tickets_per_participant: int
    allocation_method: str
    standby_policy: str
    status: str
    policy_version: str
    published_at: datetime | None


class CampaignListResponse(BaseModel):
    """Paginated collection of public campaign records."""

    data: list[CampaignPublicResponse]
    meta: dict[str, Any] = Field(
        description="Pagination metadata: page, page_size, total",
    )


class CampaignAdminResponse(CampaignPublicResponse):
    """Full admin representation of a campaign including counts and pauses."""

    admission_paused: bool
    registration_paused: bool
    redemption_paused: bool
    policy_hash: str | None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
    seat_counts: dict[str, int] = Field(
        default_factory=lambda: {"available": 0, "held": 0, "confirmed": 0, "total": 0},
    )
    registration_counts: dict[str, int] = Field(
        default_factory=lambda: {"total": 0, "accepted": 0, "duplicate": 0, "rejected": 0},
    )


class CampaignStatusResponse(BaseModel):
    """Client recovery endpoint response returning server truth for a participant."""

    campaign: dict[str, Any]
    participant_state: str = Field(
        description="One of: NOT_REGISTERED, REGISTERED, SELECTED, STANDBY, etc.",
    )
    registration: dict[str, Any] | None = None
    registration_slice: dict[str, Any] | None = None
    admission: dict[str, Any] | None = None
    challenge: None = None
    entitlement: None = None
    seat_hold: None = None


class PauseRequest(BaseModel):
    """Request payload to pause an operational scope."""

    scope: Literal["ADMISSION", "REGISTRATION", "REDEMPTION"]
    reason: str = Field(min_length=1, max_length=500)


class ResumeRequest(BaseModel):
    """Request payload to resume an operational scope."""

    scope: Literal["ADMISSION", "REGISTRATION", "REDEMPTION"]


class CampaignTransitionResponse(BaseModel):
    """Response returned upon lifecycle state transition."""

    campaign_id: uuid.UUID
    previous_status: str
    new_status: str
    message: str
    server_time: datetime

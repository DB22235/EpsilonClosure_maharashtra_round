"""
Pydantic schemas for Campaign Join, Admission Permits, and Fair Registration.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class JoinRequest(BaseModel):
    """Optional payload for requesting an admission permit."""

    client_meta: dict[str, Any] | None = Field(
        default=None,
        description="Optional client telemetry or environment context.",
    )


class JoinResponse(BaseModel):
    """Response returned upon joining a campaign waiting room."""

    permit_id: uuid.UUID
    admission_token: str = Field(
        description="Signed cryptographic admission permit token to present on registration.",
    )
    nonce: str = Field(
        description="Cryptographically secure 32-character single-use nonce.",
    )
    expires_at: datetime
    campaign_id: uuid.UUID
    server_time: datetime

    model_config = ConfigDict(from_attributes=True)


class RegisterRequest(BaseModel):
    """Payload submitted to complete registration."""

    admission_token: str = Field(
        min_length=1,
        description="Signed admission token received from /join.",
    )
    nonce: str = Field(
        min_length=16,
        description="Cryptographic nonce matching the issued admission permit.",
    )
    client_meta: dict[str, Any] | None = Field(
        default=None,
        description="Optional client telemetry/device metadata.",
    )


class RegisterResponse(BaseModel):
    """Authoritative confirmation of a successfully registered participant entry."""

    registration_id: uuid.UUID
    campaign_id: uuid.UUID
    participant_id: uuid.UUID
    status: str = Field(
        default="REGISTERED",
        description="Registration lifecycle status (e.g. REGISTERED).",
    )
    registered_at: datetime
    risk_level: str = Field(
        default="LOW",
        description="Evaluated risk tier (LOW, MEDIUM, HIGH).",
    )
    challenge_required: bool = Field(
        default=False,
        description="Whether an additional proof-of-human challenge is required.",
    )
    message: str = Field(
        default="Registration accepted successfully",
        description="Human-readable status summary.",
    )

    model_config = ConfigDict(from_attributes=True)


class RegistrationStatusSlice(BaseModel):
    """Participant registration state slice exposed in campaign recovery status."""

    is_registered: bool
    registration_id: uuid.UUID | None = None
    registered_at: datetime | None = None
    risk_level: str | None = None

    model_config = ConfigDict(from_attributes=True)

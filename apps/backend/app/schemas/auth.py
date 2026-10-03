"""
Authentication and user identity Pydantic schemas.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProfileResponse(BaseModel):
    """Public profile representation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(description="Supabase user UUID")
    display_name: str | None = Field(default=None, description="User display name")
    role: Literal["USER", "ADMIN"] = Field(description="Platform authorization role")
    email_verified: bool = Field(description="Email verification status")
    phone_verified: bool = Field(description="Phone verification status")
    institute_verified: bool = Field(description="Institute verification status")
    created_at: datetime = Field(description="Account creation timestamp")


class ParticipantResponse(BaseModel):
    """Participant risk and verification status representation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(description="Participant UUID")
    account_id: uuid.UUID = Field(description="Linked Profile UUID")
    verification_status: Literal["PENDING", "VERIFIED", "REJECTED"] = Field(
        description="Fair Drop participant verification status",
    )
    risk_level: Literal["LOW", "MEDIUM", "HIGH"] = Field(
        description="Assigned participant risk score level",
    )
    created_at: datetime = Field(description="Participant record creation timestamp")


class CurrentUserResponse(BaseModel):
    """Combined response returned by /auth/me representing the authenticated identity."""

    profile: ProfileResponse
    participant: ParticipantResponse
    server_time: datetime = Field(description="Server timestamp in UTC")

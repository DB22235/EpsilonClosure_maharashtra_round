"""
Pydantic schemas for proof-of-human challenges.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ChallengeType(str, Enum):
    TURNSTILE = "TURNSTILE"
    MEDIAPIPE = "MEDIAPIPE"
    VISUAL = "VISUAL"
    MOCK = "MOCK"


class ChallengeStatus(str, Enum):
    PENDING = "PENDING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    CONSUMED = "CONSUMED"


class ChallengeOperation(str, Enum):
    REGISTER = "REGISTER"
    REDEEM = "REDEEM"


class ChallengeCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    campaign_id: uuid.UUID = Field(description="Campaign ID for which challenge is requested")
    type: ChallengeType = Field(description="Type of challenge requested")
    operation: str = Field(description="Operation triggering challenge e.g. REGISTER, REDEEM")
    requested_reason: str = Field(description="Reason for challenge e.g. MEDIUM_RISK")
    fallback_requested: bool = Field(default=False, description="Whether accessibility fallback mode is requested")
    accessibility_reason: str | None = Field(default=None, description="Reason for accessibility fallback e.g. CAMERA_DENIED")


class ChallengeCreateResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    challenge_id: uuid.UUID = Field(description="Issued challenge unique ID")
    type: ChallengeType = Field(description="Challenge type")
    status: ChallengeStatus = Field(default=ChallengeStatus.PENDING, description="Current challenge status")
    nonce: str = Field(description="Raw verification nonce (issued once)")
    expires_at: datetime = Field(description="UTC timestamp when challenge expires")
    max_attempts: int = Field(default=2, description="Maximum allowable verification attempts")
    implementation_version: str = Field(description="Version string of verification model")
    instructions: dict[str, Any] = Field(
        default_factory=dict,
        description="Challenge instructions e.g. gesture pose or side",
    )


# Alias for backward compatibility
ChallengeResponse = ChallengeCreateResponse


class ChallengeVerifyRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    nonce: str = Field(description="Raw verification nonce")
    type: ChallengeType = Field(description="Challenge type being verified")
    result: Literal["SUCCESS", "FAILURE"] = Field(description="Verification result")
    confidence: float | None = Field(default=None, ge=0.0, le=1.0, description="Model confidence score between 0 and 1")
    duration_ms: int = Field(ge=0, description="Execution duration in milliseconds")
    implementation_version: str = Field(description="Version string of verification model")
    turnstile_token: str | None = Field(default=None, description="Turnstile token if applicable")
    hand_used: str | None = Field(default=None, description="Hand used during gesture verification e.g. LEFT or RIGHT")
    model_metadata: dict[str, Any] | None = Field(
        default=None,
        description="Extra execution metadata from model",
    )


class ChallengeVerifyResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    challenge_id: uuid.UUID = Field(description="Verified challenge unique ID")
    status: ChallengeStatus = Field(description="Resulting challenge status")
    risk_level: Literal["LOW", "MEDIUM", "HIGH"] = Field(description="Assessed risk level")
    reason_code: str = Field(description="Verification outcome reason code")
    verified_until: datetime = Field(description="UTC timestamp until which verification remains valid")


class ChallengeTypeBreakdown(BaseModel):
    total: int = Field(default=0, description="Total challenges issued for this type")
    passed: int = Field(default=0, description="Total passed challenges for this type")
    failed: int = Field(default=0, description="Total failed challenges for this type")
    abandoned: int = Field(default=0, description="Total abandoned challenges for this type")
    pass_rate_percentage: float = Field(default=0.0, description="Pass rate percentage for this type")
    avg_duration_ms: float = Field(default=0.0, description="Average verification latency in milliseconds for this type")


class ChallengeMetricsSummaryResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    campaign_id: uuid.UUID | None = Field(default=None, description="Campaign ID or None for global aggregate")
    total_challenges_issued: int = Field(description="Total challenges issued")
    total_passed: int = Field(description="Total challenges passed")
    total_failed: int = Field(description="Total challenges failed")
    total_abandoned: int = Field(description="Total abandoned/expired challenges")
    pass_rate_percentage: float = Field(description="Overall pass rate percentage")
    avg_duration_ms: float = Field(description="Average verification latency in milliseconds")
    p90_duration_ms: float = Field(description="P90 verification latency in milliseconds")
    fallback_count: int = Field(description="Count of fallback triggers (e.g. MEDIAPIPE to VISUAL)")
    cooldown_triggers_count: int = Field(description="Count of cooldown triggers")
    by_type_breakdown: dict[str, ChallengeTypeBreakdown] = Field(description="Metrics breakdown by challenge type")
    by_risk_level_breakdown: dict[str, int] = Field(description="Count breakdown by risk level")
    generated_at: datetime = Field(description="UTC timestamp of report generation")

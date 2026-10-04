"""
Pydantic schemas for platform audit logging and verifiable event streams.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AuditEventItem(BaseModel):
    """Immutable audit event entry representing a state transition or platform operation."""

    id: uuid.UUID
    campaign_id: uuid.UUID | None = None
    participant_id: uuid.UUID | None = None
    actor_type: str = Field(description="Actor role: USER, ADMIN, SYSTEM, WORKER.")
    actor_id: uuid.UUID | None = None
    event_type: str = Field(description="Normalized action identifier.")
    reason_code: str | None = None
    metadata_json: dict = Field(default_factory=dict, description="Structured event metadata (secrets redacted).")
    request_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditListResponse(BaseModel):
    """Paginated collection of audit log events."""

    data: list[AuditEventItem]
    total: int
    limit: int
    offset: int

    model_config = ConfigDict(from_attributes=True)

"""
Common Pydantic schemas, types, and envelope models.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

# UUID aliases
UUID = uuid.UUID
UUID4 = uuid.UUID


class BaseResponse(BaseModel):
    """
    Base response envelope containing request trace ID and UTC server timestamp.
    """

    model_config = ConfigDict(populate_by_name=True)

    request_id: str = Field(description="Unique request trace identifier")
    server_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Server timestamp in UTC",
    )


class ErrorDetail(BaseModel):
    """
    Standard error payload structure.
    """

    code: str = Field(description="Standardized error code")
    message: str = Field(description="Human-readable error message")
    request_id: str = Field(description="Unique request trace identifier")
    details: dict[str, Any] | None = Field(
        default=None,
        description="Optional error details or validation context",
    )


class ErrorResponse(BaseModel):
    """
    Standard error response matching {'error': {'code': ..., 'message': ..., ...}}.
    """

    error: ErrorDetail


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Standard envelope for paginated resource lists.
    """

    data: list[T] = Field(description="Items in the current page")
    page: int = Field(ge=1, description="Current page number (1-indexed)")
    page_size: int = Field(ge=1, description="Number of items per page")
    total: int = Field(ge=0, description="Total count across all pages")

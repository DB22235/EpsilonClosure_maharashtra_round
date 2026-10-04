"""Fair Drop backend Pydantic schemas."""

from app.schemas.auth import (
    CurrentUserResponse,
    ParticipantResponse,
    ProfileResponse,
)
from app.schemas.campaign import (
    CampaignAdminResponse,
    CampaignCreateRequest,
    CampaignListResponse,
    CampaignPublicResponse,
    CampaignStatusResponse,
    CampaignTransitionResponse,
    CampaignUpdateRequest,
    PauseRequest,
    ResumeRequest,
)
from app.schemas.common import BaseResponse, ErrorDetail, ErrorResponse, PaginatedResponse
from app.schemas.lottery import (
    FreezeRosterResponse,
    LotteryDrawRequest,
    LotteryDrawResponse,
    ParticipantResultResponse,
)
from app.schemas.registration import (
    JoinRequest,
    JoinResponse,
    RegisterRequest,
    RegisterResponse,
    RegistrationStatusSlice,
)

__all__ = [
    "CurrentUserResponse",
    "ParticipantResponse",
    "ProfileResponse",
    "CampaignAdminResponse",
    "CampaignCreateRequest",
    "CampaignListResponse",
    "CampaignPublicResponse",
    "CampaignStatusResponse",
    "CampaignTransitionResponse",
    "CampaignUpdateRequest",
    "PauseRequest",
    "ResumeRequest",
    "BaseResponse",
    "ErrorDetail",
    "ErrorResponse",
    "PaginatedResponse",
    "FreezeRosterResponse",
    "LotteryDrawRequest",
    "LotteryDrawResponse",
    "ParticipantResultResponse",
    "JoinRequest",
    "JoinResponse",
    "RegisterRequest",
    "RegisterResponse",
    "RegistrationStatusSlice",
]

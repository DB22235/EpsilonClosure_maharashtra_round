"""
Authentication and identity verification endpoints.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.dependencies import get_current_identity, require_admin
from app.models.participant import Participant, Profile
from app.schemas.auth import CurrentUserResponse, ParticipantResponse, ProfileResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    summary="Get current user identity",
    description="Resolves caller identity via Supabase JWT, triggers JIT provisioning on first call, and returns profile + participant state.",
)
async def get_me(
    identity: tuple[Profile, Participant] = Depends(get_current_identity),
) -> CurrentUserResponse:
    profile, participant = identity
    return CurrentUserResponse(
        profile=ProfileResponse.model_validate(profile),
        participant=ParticipantResponse.model_validate(participant),
        server_time=datetime.now(timezone.utc),
    )


@router.get(
    "/me/admin",
    response_model=ProfileResponse,
    summary="Verify admin access",
    description="Returns caller profile if they hold ADMIN role in the profiles table, otherwise returns 403 Forbidden.",
)
async def get_me_admin(
    profile: Profile = Depends(require_admin),
) -> ProfileResponse:
    return ProfileResponse.model_validate(profile)

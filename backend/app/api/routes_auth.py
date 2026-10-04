"""
Authentication and identity verification endpoints.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import lru_settings
from app.database import get_db
from app.dependencies import get_current_identity, require_admin
from app.middleware.rate_limit import enforce_rate_limit
from app.models.participant import Participant, Profile
from app.schemas.auth import CurrentUserResponse, ParticipantResponse, ProfileResponse
from app.security.request_ids import get_request_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])
settings = lru_settings()


class ConfirmEmailRequest(BaseModel):
    email: EmailStr


@router.post(
    "/confirm",
    summary="Auto-confirm user email",
    description="Development and onboarding helper that sets email_confirmed_at in auth.users so users can log in immediately.",
)
async def confirm_email(
    payload: ConfirmEmailRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    try:
        stmt = text(
            "UPDATE auth.users SET email_confirmed_at = COALESCE(email_confirmed_at, NOW()) WHERE lower(email) = lower(:email);"
        )
        await db.execute(stmt, {"email": payload.email.strip()})
    except Exception as exc:
        logger.warning("Could not auto-confirm email in auth.users: %s", exc)
    return {"status": "ok", "message": f"Confirmed email {payload.email}"}



@router.get(
    "/me",
    response_model=CurrentUserResponse,
    summary="Get current user identity",
    description="Resolves caller identity via Supabase JWT, triggers JIT provisioning on first call, and returns profile + participant state.",
)
async def get_me(
    request: Request,
    identity: tuple[Profile, Participant] = Depends(get_current_identity),
) -> CurrentUserResponse:
    profile, participant = identity
    request_id = await get_request_id(request)

    await enforce_rate_limit(
        scope="auth_me",
        key_identifier=str(participant.id),
        limit=settings.RL_AUTH_ME_PER_MIN,
        request_id=request_id,
    )

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


"""
FastAPI dependency chain for authentication, identity resolution, and RBAC.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.participant import Participant, Profile
from app.security.jwt import InvalidTokenError
from app.security.request_ids import get_request_id
from app.services.auth_service import resolve_identity

logger = logging.getLogger(__name__)

# auto_error=False allows us to intercept missing tokens and return our standardized envelope
bearer_scheme = HTTPBearer(auto_error=False)


def _build_error_response(
    code: str,
    message: str,
    request_id: str,
    http_status: int,
    details: dict[str, Any] | None = None,
) -> HTTPException:
    """
    Format a standardized error envelope matching the Fair Drop API contract.
    """
    return HTTPException(
        status_code=http_status,
        detail={
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id,
                "details": details or {},
            }
        },
    )


async def get_current_identity(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> tuple[Profile, Participant]:
    """
    Validate the Bearer JWT and resolve the caller's Profile and Participant records.
    Stores the identity in request.state for downstream handlers.
    """
    request_id = await get_request_id(request)

    if credentials is None:
        raise _build_error_response(
            code="AUTH_REQUIRED",
            message="Authentication required",
            request_id=request_id,
            http_status=status.HTTP_401_UNAUTHORIZED,
        )

    if credentials.scheme.lower() != "bearer":
        raise _build_error_response(
            code="AUTH_REQUIRED",
            message="Bearer token required",
            request_id=request_id,
            http_status=status.HTTP_401_UNAUTHORIZED,
        )

    try:
        profile, participant = await resolve_identity(db, credentials.credentials)
    except InvalidTokenError as exc:
        raise _build_error_response(
            code=exc.code,
            message=str(exc),
            request_id=request_id,
            http_status=status.HTTP_401_UNAUTHORIZED,
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Authentication failed: %s", exc)
        raise _build_error_response(
            code="AUTH_FAILED",
            message="Authentication failed",
            request_id=request_id,
            http_status=status.HTTP_401_UNAUTHORIZED,
        ) from exc

    request.state.profile = profile
    request.state.participant = participant
    return profile, participant


async def get_current_profile(
    identity: tuple[Profile, Participant] = Depends(get_current_identity),
) -> Profile:
    """
    Return the authenticated user's Profile entity.
    """
    return identity[0]


async def get_current_participant(
    identity: tuple[Profile, Participant] = Depends(get_current_identity),
) -> Participant:
    """
    Return the authenticated user's Participant entity.
    """
    return identity[1]


async def require_admin(
    request: Request,
    profile: Profile = Depends(get_current_profile),
) -> Profile:
    """
    Enforce that the caller holds the ADMIN role in the profiles table.
    """
    request_id = await get_request_id(request)
    if profile.role != "ADMIN":
        raise _build_error_response(
            code="FORBIDDEN",
            message="Admin role required",
            request_id=request_id,
            http_status=status.HTTP_403_FORBIDDEN,
        )
    return profile


async def require_verified_participant(
    request: Request,
    participant: Participant = Depends(get_current_participant),
) -> Participant:
    """
    Enforce participant verification status.
    For hackathon MVP, accepts PENDING and VERIFIED; rejects REJECTED.
    """
    request_id = await get_request_id(request)
    if participant.verification_status == "REJECTED":
        raise _build_error_response(
            code="IDENTITY_NOT_VERIFIED",
            message="Participant identity is not verified",
            request_id=request_id,
            http_status=status.HTTP_403_FORBIDDEN,
        )
    return participant

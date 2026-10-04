"""
Challenge management and verification API endpoints.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_identity
from app.models.participant import Participant, Profile
from app.schemas.challenge import (
    ChallengeCreateRequest,
    ChallengeCreateResponse,
    ChallengeMetricsSummaryResponse,
    ChallengeVerifyRequest,
    ChallengeVerifyResponse,
)
from app.security.request_ids import get_request_id
from app.services.challenge_service import (
    create_challenge,
    get_challenge_metrics_summary,
    verify_challenge,
)

router = APIRouter(prefix="/challenges", tags=["challenges"])


@router.get(
    "/metrics",
    response_model=ChallengeMetricsSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Challenge analytics summary",
    description="Aggregated telemetry metrics for challenge verification performance and anti-abuse effectiveness.",
)
async def get_challenge_metrics(
    campaign_id: uuid.UUID | None = None,
    request: Request = ...,
    identity: tuple[Profile, Participant] = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> ChallengeMetricsSummaryResponse:
    return await get_challenge_metrics_summary(db=db, campaign_id=campaign_id)


@router.post(
    "",
    response_model=ChallengeCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new challenge",
    description="Issues a proof-of-human challenge for a given campaign and operation.",
)
async def request_challenge(
    payload: ChallengeCreateRequest,
    request: Request,
    identity: tuple[Profile, Participant] = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> ChallengeCreateResponse:
    request_id = await get_request_id(request)
    _, participant = identity

    # Stub session_id = participant.id until Dhruv's sessions table is active in Step 5
    user_session_id = participant.id

    return await create_challenge(
        db=db,
        user_session_id=user_session_id,
        request_data=payload,
        participant_id=participant.id,
        request_id=request_id,
    )


@router.post(
    "/{challenge_id}/verify",
    response_model=ChallengeVerifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify challenge attempt",
    description="Verifies a submitted challenge response against nonce, model parameters, and expiration.",
)
async def submit_challenge_verification(
    challenge_id: uuid.UUID,
    payload: ChallengeVerifyRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    identity: tuple[Profile, Participant] = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> ChallengeVerifyResponse:
    request_id = await get_request_id(request)
    _, participant = identity

    user_session_id = participant.id

    return await verify_challenge(
        db=db,
        user_session_id=user_session_id,
        challenge_id=challenge_id,
        request_data=payload,
        idempotency_key=idempotency_key,
        request_id=request_id,
    )

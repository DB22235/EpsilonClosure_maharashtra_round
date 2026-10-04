"""
Authenticated participant campaign routes (recovery endpoint and lottery result endpoint).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_participant
from app.models.participant import Participant
from app.schemas.campaign import CampaignStatusResponse
from app.schemas.entitlement import SeatMapResponse
from app.schemas.lottery import ParticipantResultResponse
from app.security.request_ids import get_request_id
from app.services.campaign_service import get_campaign_or_404, get_campaign_status
from app.services.inventory_service import get_campaign_seats
from app.services.lottery_service import get_participant_result

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get(
    "/{campaign_id}/status",
    response_model=CampaignStatusResponse,
    summary="Get participant campaign status (recovery endpoint)",
    description="Returns current participant registration state, admission availability, and campaign lifecycle state from server truth.",
)
async def get_campaign_status_endpoint(
    campaign_id: uuid.UUID,
    request: Request,
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
) -> CampaignStatusResponse:
    request_id = await get_request_id(request)
    campaign = await get_campaign_or_404(db, campaign_id, request_id)
    status_data = await get_campaign_status(db, campaign, participant.id, request_id)
    return CampaignStatusResponse(**status_data)


@router.get(
    "/{campaign_id}/result",
    response_model=ParticipantResultResponse,
    summary="Get participant lottery draw result",
    description="Returns personal draw result: WON (with rank and entitlement), WAITLISTED, or NOT_REGISTERED.",
)
async def get_participant_result_endpoint(
    campaign_id: uuid.UUID,
    request: Request,
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
) -> ParticipantResultResponse:
    request_id = await get_request_id(request)
    return await get_participant_result(
        db=db,
        campaign_id=campaign_id,
        participant_id=participant.id,
        request_id=request_id,
    )


@router.get(
    "/{campaign_id}/seats",
    response_model=SeatMapResponse,
    summary="Get live campaign seat map",
    description="Returns live seat inventory, hold statuses, and section layout for interactive booking.",
)
async def get_campaign_seats_endpoint(
    campaign_id: uuid.UUID,
    request: Request,
    limit: int = 500,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> SeatMapResponse:
    request_id = await get_request_id(request)
    await get_campaign_or_404(db, campaign_id, request_id)
    seat_data = await get_campaign_seats(db, campaign_id, limit=limit, offset=offset)
    return SeatMapResponse(**seat_data)


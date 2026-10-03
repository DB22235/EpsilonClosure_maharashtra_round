"""
Admin campaign lifecycle management endpoints.
All routes require require_admin authorization.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_admin
from app.models.campaign import Campaign
from app.models.participant import Profile
from app.schemas.campaign import (
    CampaignAdminResponse,
    CampaignCreateRequest,
    CampaignTransitionResponse,
    CampaignUpdateRequest,
    PauseRequest,
    ResumeRequest,
)
from app.security.request_ids import get_request_id
from app.services.campaign_service import (
    create_campaign,
    get_campaign_or_404,
    get_registration_counts,
    get_seat_counts,
    pause_campaign_scope,
    prepare_campaign,
    resume_campaign_scope,
    transition_campaign,
    update_campaign_draft,
)

router = APIRouter(prefix="/admin/campaigns", tags=["admin"])


async def _build_admin_response(db: AsyncSession, campaign: Campaign) -> CampaignAdminResponse:
    seat_counts = await get_seat_counts(db, campaign.id)
    registration_counts = await get_registration_counts(db, campaign.id)
    admin_data = CampaignAdminResponse.model_validate(campaign)
    admin_data.seat_counts = seat_counts
    admin_data.registration_counts = registration_counts
    return admin_data


@router.post(
    "",
    response_model=CampaignAdminResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create campaign (DRAFT)",
    description="Creates a new campaign in DRAFT state. Seats are not generated until prepare step.",
)
async def create_campaign_endpoint(
    data: CampaignCreateRequest,
    request: Request,
    profile: Profile = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> CampaignAdminResponse:
    request_id = await get_request_id(request)
    campaign = await create_campaign(
        db=db,
        data=data.model_dump(),
        admin_id=profile.id,
        request_id=request_id,
    )
    return await _build_admin_response(db, campaign)


@router.get(
    "",
    response_model=list[CampaignAdminResponse],
    summary="List all campaigns (admin)",
    description="Returns all campaigns including DRAFT and PREPARING, with aggregated seat and registration metrics.",
)
async def list_campaigns_admin(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    profile: Profile = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[CampaignAdminResponse]:
    stmt = (
        select(Campaign)
        .order_by(Campaign.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    campaigns = list(result.scalars().all())

    responses: list[CampaignAdminResponse] = []
    for c in campaigns:
        responses.append(await _build_admin_response(db, c))
    return responses


@router.get(
    "/{campaign_id}",
    response_model=CampaignAdminResponse,
    summary="Get campaign detail (admin)",
    description="Returns full administrative view of campaign with inventory counts and pauses.",
)
async def get_campaign_admin(
    campaign_id: uuid.UUID,
    request: Request,
    profile: Profile = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> CampaignAdminResponse:
    request_id = await get_request_id(request)
    campaign = await get_campaign_or_404(db, campaign_id, request_id)
    return await _build_admin_response(db, campaign)


@router.patch(
    "/{campaign_id}",
    response_model=CampaignAdminResponse,
    summary="Update campaign (DRAFT or PREPARING only)",
    description="Updates policy and metadata fields while campaign is in DRAFT or PREPARING state.",
)
async def update_campaign_endpoint(
    campaign_id: uuid.UUID,
    data: CampaignUpdateRequest,
    request: Request,
    profile: Profile = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> CampaignAdminResponse:
    request_id = await get_request_id(request)
    campaign = await get_campaign_or_404(db, campaign_id, request_id)
    updated = await update_campaign_draft(
        db=db,
        campaign=campaign,
        data=data.model_dump(exclude_unset=True),
        admin_id=profile.id,
        request_id=request_id,
    )
    return await _build_admin_response(db, updated)


@router.post(
    "/{campaign_id}/prepare",
    response_model=CampaignTransitionResponse,
    summary="Prepare campaign and generate seat inventory",
    description="Transitions DRAFT -> PREPARING, calculates policy hash, and bulk-inserts initial seat inventory.",
)
async def prepare_campaign_endpoint(
    campaign_id: uuid.UUID,
    request: Request,
    profile: Profile = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> CampaignTransitionResponse:
    request_id = await get_request_id(request)
    campaign = await get_campaign_or_404(db, campaign_id, request_id)
    previous_status = campaign.status
    prepared = await prepare_campaign(
        db=db,
        campaign=campaign,
        admin_id=profile.id,
        request_id=request_id,
    )
    return CampaignTransitionResponse(
        campaign_id=prepared.id,
        previous_status=previous_status,
        new_status=prepared.status,
        message="Campaign prepared and seat inventory generated",
        server_time=datetime.now(timezone.utc),
    )


@router.post(
    "/{campaign_id}/publish",
    response_model=CampaignTransitionResponse,
    summary="Publish and open campaign",
    description="Transitions PREPARING -> OPEN. Makes campaign visible to the public and open for registrations.",
)
async def publish_campaign_endpoint(
    campaign_id: uuid.UUID,
    request: Request,
    profile: Profile = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> CampaignTransitionResponse:
    request_id = await get_request_id(request)
    campaign = await get_campaign_or_404(db, campaign_id, request_id)
    previous_status = campaign.status
    published = await transition_campaign(
        db=db,
        campaign=campaign,
        target_status="OPEN",
        admin_id=profile.id,
        request_id=request_id,
    )
    return CampaignTransitionResponse(
        campaign_id=published.id,
        previous_status=previous_status,
        new_status=published.status,
        message="Campaign published and open for registrations",
        server_time=datetime.now(timezone.utc),
    )


@router.post(
    "/{campaign_id}/close",
    response_model=CampaignTransitionResponse,
    summary="Close campaign registrations",
    description="Transitions OPEN -> CLOSED. Halts all new registrations.",
)
async def close_campaign_endpoint(
    campaign_id: uuid.UUID,
    request: Request,
    profile: Profile = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> CampaignTransitionResponse:
    request_id = await get_request_id(request)
    campaign = await get_campaign_or_404(db, campaign_id, request_id)
    previous_status = campaign.status
    closed = await transition_campaign(
        db=db,
        campaign=campaign,
        target_status="CLOSED",
        admin_id=profile.id,
        request_id=request_id,
    )
    return CampaignTransitionResponse(
        campaign_id=closed.id,
        previous_status=previous_status,
        new_status=closed.status,
        message="Campaign registrations closed",
        server_time=datetime.now(timezone.utc),
    )


@router.post(
    "/{campaign_id}/freeze",
    response_model=CampaignTransitionResponse,
    summary="Freeze campaign policy and roster",
    description="Transitions CLOSED -> FROZEN. Captures immutable policy snapshot in campaign_policy_snapshots.",
)
async def freeze_campaign_endpoint(
    campaign_id: uuid.UUID,
    request: Request,
    profile: Profile = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> CampaignTransitionResponse:
    request_id = await get_request_id(request)
    campaign = await get_campaign_or_404(db, campaign_id, request_id)
    previous_status = campaign.status
    frozen = await transition_campaign(
        db=db,
        campaign=campaign,
        target_status="FROZEN",
        admin_id=profile.id,
        request_id=request_id,
    )
    return CampaignTransitionResponse(
        campaign_id=frozen.id,
        previous_status=previous_status,
        new_status=frozen.status,
        message="Campaign policy and roster frozen for draw",
        server_time=datetime.now(timezone.utc),
    )


@router.post(
    "/{campaign_id}/draw",
    response_model=CampaignTransitionResponse,
    summary="Initiate lottery draw",
    description="Validates that campaign is FROZEN and transitions to DRAWING.",
)
async def draw_campaign_endpoint(
    campaign_id: uuid.UUID,
    request: Request,
    profile: Profile = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> CampaignTransitionResponse:
    request_id = await get_request_id(request)
    campaign = await get_campaign_or_404(db, campaign_id, request_id)

    if campaign.status != "FROZEN":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "INVALID_STATE_TRANSITION",
                    "message": f"Cannot initiate draw on campaign in {campaign.status} state. Must be FROZEN.",
                    "request_id": request_id,
                    "details": {"current_status": campaign.status, "required_status": "FROZEN"},
                }
            },
        )

    previous_status = campaign.status
    # TODO: Full lottery execution (shuffle, winner selection, standby ordering) will be implemented in Step 7
    drawing = await transition_campaign(
        db=db,
        campaign=campaign,
        target_status="DRAWING",
        admin_id=profile.id,
        request_id=request_id,
    )
    return CampaignTransitionResponse(
        campaign_id=drawing.id,
        previous_status=previous_status,
        new_status=drawing.status,
        message="Lottery draw initiated",
        server_time=datetime.now(timezone.utc),
    )


@router.post(
    "/{campaign_id}/pause",
    response_model=CampaignAdminResponse,
    summary="Pause operational scope",
    description="Pauses ADMISSION, REGISTRATION, or REDEMPTION without altering lifecycle state.",
)
async def pause_campaign_endpoint(
    campaign_id: uuid.UUID,
    body: PauseRequest,
    request: Request,
    profile: Profile = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> CampaignAdminResponse:
    request_id = await get_request_id(request)
    campaign = await get_campaign_or_404(db, campaign_id, request_id)
    paused = await pause_campaign_scope(
        db=db,
        campaign=campaign,
        scope=body.scope,
        reason=body.reason,
        admin_id=profile.id,
        request_id=request_id,
    )
    return await _build_admin_response(db, paused)


@router.post(
    "/{campaign_id}/resume",
    response_model=CampaignAdminResponse,
    summary="Resume operational scope",
    description="Resumes ADMISSION, REGISTRATION, or REDEMPTION.",
)
async def resume_campaign_endpoint(
    campaign_id: uuid.UUID,
    body: ResumeRequest,
    request: Request,
    profile: Profile = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> CampaignAdminResponse:
    request_id = await get_request_id(request)
    campaign = await get_campaign_or_404(db, campaign_id, request_id)
    resumed = await resume_campaign_scope(
        db=db,
        campaign=campaign,
        scope=body.scope,
        admin_id=profile.id,
        request_id=request_id,
    )
    return await _build_admin_response(db, resumed)

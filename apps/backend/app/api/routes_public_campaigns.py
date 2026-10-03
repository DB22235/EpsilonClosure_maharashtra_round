"""
Publicly accessible campaign catalog endpoints (no authentication required).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.campaign import (
    CampaignListResponse,
    CampaignPublicResponse,
)
from app.security.request_ids import get_request_id
from app.services.campaign_service import get_campaign_or_404, list_public_campaigns

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get(
    "",
    response_model=CampaignListResponse,
    summary="List published campaigns",
    description="Returns a paginated list of non-draft campaigns. Supports optional status filtering.",
)
async def list_campaigns(
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> CampaignListResponse:
    campaigns, total_count = await list_public_campaigns(
        db=db,
        status_filter=status_filter,
        page=page,
        page_size=page_size,
    )
    return CampaignListResponse(
        data=[CampaignPublicResponse.model_validate(c) for c in campaigns],
        meta={"page": page, "page_size": page_size, "total": total_count},
    )


@router.get(
    "/{campaign_id}",
    response_model=CampaignPublicResponse,
    summary="Get public campaign details",
    description="Returns public details for an open or completed campaign. Draft campaigns return 404.",
)
async def get_campaign(
    campaign_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> CampaignPublicResponse:
    request_id = await get_request_id(request)
    campaign = await get_campaign_or_404(db, campaign_id, request_id)

    # Draft and Preparing campaigns are not visible to the general public
    if campaign.status in ("DRAFT", "PREPARING"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "CAMPAIGN_NOT_FOUND",
                    "message": f"Campaign {campaign_id} not found",
                    "request_id": request_id,
                    "details": {},
                }
            },
        )

    return CampaignPublicResponse.model_validate(campaign)

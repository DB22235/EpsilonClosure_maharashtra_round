"""
Metrics and Fairness Evidence route handlers.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_profile, require_admin
from app.models.participant import Profile
from app.schemas.metrics import CampaignMetricsResponse, FairnessEvidenceResponse
from app.security.request_ids import get_request_id
from app.services.metrics_service import get_campaign_metrics, get_fairness_evidence

router = APIRouter(tags=["metrics"])


@router.get(
    "/campaigns/{campaign_id}/metrics",
    response_model=CampaignMetricsResponse,
    summary="Get real-time campaign allocation & operational metrics",
    description="Returns aggregate counts of registrations, lottery winners, seats, bookings, and verified zero-oversell invariants.",
)
async def get_campaign_metrics_endpoint(
    campaign_id: uuid.UUID,
    request: Request,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
) -> CampaignMetricsResponse:
    request_id = await get_request_id(request)
    return await get_campaign_metrics(db, campaign_id, request_id)


@router.get(
    "/campaigns/{campaign_id}/fairness",
    response_model=FairnessEvidenceResponse,
    summary="Get public verifiable cryptographic fairness proof",
    description="Returns draw randomness commitment, roster hash, selection probability, and canonical evidence hash (seed redacted for public transparency).",
)
async def get_fairness_summary_endpoint(
    campaign_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> FairnessEvidenceResponse:
    request_id = await get_request_id(request)
    return await get_fairness_evidence(db, campaign_id, include_seed=False, request_id=request_id)


@router.get(
    "/admin/campaigns/{campaign_id}/fairness-evidence",
    response_model=FairnessEvidenceResponse,
    summary="Get authoritative full cryptographic draw reproducibility package (Admin)",
    description="Returns the unredacted draw seed, commitment, roster hash, and complete verification parameters for audit.",
)
async def get_admin_fairness_evidence_endpoint(
    campaign_id: uuid.UUID,
    request: Request,
    admin_profile: Profile = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> FairnessEvidenceResponse:
    request_id = await get_request_id(request)
    return await get_fairness_evidence(db, campaign_id, include_seed=True, request_id=request_id)

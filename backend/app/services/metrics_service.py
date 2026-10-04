"""
Metrics and Cryptographic Fairness Evidence Service.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditEvent
from app.models.campaign import Campaign
from app.models.challenge import Challenge
from app.models.entitlement import Entitlement
from app.models.inventory import Booking, Seat
from app.models.lottery import LotteryEntry, LotteryRun
from app.models.registration import Registration
from app.schemas.metrics import CampaignMetricsResponse, FairnessEvidenceResponse
from app.services.admission_service import _build_error
from app.services.campaign_service import get_campaign_or_404

logger = logging.getLogger(__name__)


async def get_campaign_metrics(
    db: AsyncSession,
    campaign_id: uuid.UUID,
    request_id: str = "",
) -> CampaignMetricsResponse:
    """
    Computes real-time verifiable operational metrics for a campaign from primary database truth.
    Ensures zero overselling and zero duplicate participant allocations.
    """
    campaign = await get_campaign_or_404(db, campaign_id, request_id)
    now = datetime.now(timezone.utc)

    # 1. Registrations
    stmt_reg_all = select(func.count(Registration.id)).where(Registration.campaign_id == campaign_id)
    registrations_count = (await db.execute(stmt_reg_all)).scalar_one()

    stmt_reg_elig = select(func.count(Registration.id)).where(
        Registration.campaign_id == campaign_id,
        Registration.status == "ACCEPTED",
        Registration.eligible.is_(True),
    )
    eligible_roster_count = (await db.execute(stmt_reg_elig)).scalar_one()

    # 2. Lottery & Entitlements
    stmt_ent_all = select(func.count(Entitlement.id)).where(Entitlement.campaign_id == campaign_id)
    winners_count = (await db.execute(stmt_ent_all)).scalar_one()

    stmt_run = select(LotteryRun).where(LotteryRun.campaign_id == campaign_id)
    lottery_run = (await db.execute(stmt_run)).scalar_one_or_none()
    standby_count = lottery_run.standby_count if lottery_run else 0

    # 3. Seats inventory breakdown
    stmt_seats_tot = select(func.count(Seat.id)).where(Seat.campaign_id == campaign_id)
    seats_total = (await db.execute(stmt_seats_tot)).scalar_one()

    stmt_seats_avail = select(func.count(Seat.id)).where(
        Seat.campaign_id == campaign_id,
        Seat.status == "AVAILABLE",
    )
    seats_available = (await db.execute(stmt_seats_avail)).scalar_one()

    stmt_seats_held = select(func.count(Seat.id)).where(
        Seat.campaign_id == campaign_id,
        Seat.status == "HELD",
    )
    seats_held = (await db.execute(stmt_seats_held)).scalar_one()

    stmt_seats_conf = select(func.count(Seat.id)).where(
        Seat.campaign_id == campaign_id,
        Seat.status == "CONFIRMED",
    )
    seats_confirmed = (await db.execute(stmt_seats_conf)).scalar_one()

    # 4. Bookings
    stmt_bookings = select(func.count(Booking.id)).where(Booking.campaign_id == campaign_id)
    bookings_count = (await db.execute(stmt_bookings)).scalar_one()

    # 5. Challenges
    stmt_chal_pass = select(func.count(Challenge.id)).where(
        Challenge.campaign_id == campaign_id,
        Challenge.status == "PASSED",
    )
    challenges_passed = (await db.execute(stmt_chal_pass)).scalar_one()

    stmt_chal_fail = select(func.count(Challenge.id)).where(
        Challenge.campaign_id == campaign_id,
        Challenge.status.in_(["FAILED", "EXPIRED"]),
    )
    challenges_failed = (await db.execute(stmt_chal_fail)).scalar_one()

    # 6. Expiry counters
    stmt_holds_exp = select(func.count(AuditEvent.id)).where(
        AuditEvent.campaign_id == campaign_id,
        AuditEvent.event_type == "SEAT_HOLD_EXPIRED",
    )
    holds_expired_count = (await db.execute(stmt_holds_exp)).scalar_one()

    stmt_ent_exp = select(func.count(Entitlement.id)).where(
        Entitlement.campaign_id == campaign_id,
        Entitlement.status == "EXPIRED",
    )
    entitlements_expired_count = (await db.execute(stmt_ent_exp)).scalar_one()

    # 7. Invariants: oversell and duplicate allocation verification
    oversell_count = max(0, seats_confirmed - campaign.capacity)

    stmt_dups = (
        select(Booking.participant_id)
        .where(Booking.campaign_id == campaign_id)
        .group_by(Booking.participant_id)
        .having(func.count(Booking.id) > 1)
    )
    duplicate_participant_ids = list((await db.execute(stmt_dups)).scalars().all())
    duplicate_allocation_count = len(duplicate_participant_ids)

    return CampaignMetricsResponse(
        campaign_id=campaign.id,
        name=campaign.name,
        status=campaign.status,
        capacity=campaign.capacity,
        registrations_count=registrations_count,
        eligible_roster_count=eligible_roster_count,
        winners_count=winners_count,
        standby_count=standby_count,
        seats_total=seats_total,
        seats_available=seats_available,
        seats_held=seats_held,
        seats_confirmed=seats_confirmed,
        bookings_count=bookings_count,
        challenges_passed=challenges_passed,
        challenges_failed=challenges_failed,
        holds_expired_count=holds_expired_count,
        entitlements_expired_count=entitlements_expired_count,
        duplicate_allocation_count=duplicate_allocation_count,
        oversell_count=oversell_count,
        generated_at=now,
    )


async def get_fairness_evidence(
    db: AsyncSession,
    campaign_id: uuid.UUID,
    include_seed: bool = False,
    request_id: str = "",
) -> FairnessEvidenceResponse:
    """
    Constructs a verifiable cryptographic proof package for a campaign's lottery draw.
    Includes the commitment, roster hash, selection probability, and canonical evidence hash.
    """
    campaign = await get_campaign_or_404(db, campaign_id, request_id)

    stmt_run = select(LotteryRun).where(LotteryRun.campaign_id == campaign_id)
    lottery_run = (await db.execute(stmt_run)).scalar_one_or_none()

    if lottery_run is None:
        raise _build_error(
            "LOTTERY_NOT_DRAWN",
            "Lottery draw has not yet been finalized for this campaign.",
            request_id,
            status.HTTP_404_NOT_FOUND,
        )

    total_eligible = lottery_run.winner_count + lottery_run.standby_count
    selection_probability = (
        round(min(1.0, campaign.capacity / total_eligible), 6) if total_eligible > 0 else 0.0
    )

    evidence_data = {
        "algorithm_version": lottery_run.algorithm_version,
        "campaign_id": str(campaign_id),
        "capacity": campaign.capacity,
        "policy_hash": lottery_run.policy_hash,
        "policy_version": lottery_run.policy_version,
        "randomness_commitment": lottery_run.randomness_commitment,
        "roster_hash": lottery_run.roster_hash,
        "total_eligible": total_eligible,
        "total_winners": lottery_run.winner_count,
    }
    evidence_json = json.dumps(evidence_data, sort_keys=True, separators=(",", ":"))
    evidence_hash = hashlib.sha256(evidence_json.encode("utf-8")).hexdigest()

    reproducibility_notes = (
        f"Verifiable uniform lottery draw executed with HMAC-SHA256 (version: {lottery_run.algorithm_version}). "
        f"Deterministic score formula: HMAC_SHA256(seed, participant_id). "
        f"Seed commitment hash: {lottery_run.randomness_commitment}. "
        "Any independent observer with the seed and frozen roster hash can verify identical ranking."
    )

    return FairnessEvidenceResponse(
        campaign_id=campaign.id,
        roster_hash=lottery_run.roster_hash,
        randomness_seed=lottery_run.randomness_reference if include_seed else None,
        randomness_commitment=lottery_run.randomness_commitment,
        lottery_run_id=lottery_run.id,
        total_eligible=total_eligible,
        capacity=campaign.capacity,
        selection_probability=selection_probability,
        statement="selection probability is independent of request rate",
        reproducibility_notes=reproducibility_notes,
        evidence_hash=evidence_hash,
        draw_executed_at=lottery_run.executed_at,
    )

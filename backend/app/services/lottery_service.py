"""
Deterministic Uniform Lottery & Roster Management Service.

Implements cryptographically verifiable lottery draws:
- Immutable roster freezing and hashing
- Deterministic HMAC-SHA256 shuffling
- Winner selection and standby/waitlist positioning
- Entitlement generation for selected winners
- Participant result retrieval
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditEvent
from app.models.campaign import Campaign, CampaignPolicySnapshot
from app.models.entitlement import Entitlement
from app.models.lottery import LotteryEntry, LotteryRun
from app.models.registration import Registration
from app.schemas.lottery import (
    FreezeRosterResponse,
    LotteryDrawResponse,
    ParticipantResultResponse,
)
from app.services.campaign_service import get_campaign_or_404, transition_campaign

logger = logging.getLogger(__name__)


def compute_participant_score(seed: str, participant_id: uuid.UUID) -> str:
    """
    Deterministically computes a uniform draw score using HMAC-SHA256.
    Ensures identical inputs yield the exact same verifiable score.
    """
    return hmac.new(
        seed.encode("utf-8"),
        str(participant_id).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


async def freeze_roster(
    db: AsyncSession,
    campaign_id: uuid.UUID,
    admin_id: uuid.UUID,
    request_id: str,
) -> FreezeRosterResponse:
    """
    Freeze campaign registration roster and lock participants for lottery draw.
    Transitions campaign to FROZEN if it is OPEN or CLOSED.
    """
    campaign = await get_campaign_or_404(db, campaign_id, request_id)

    if campaign.status not in ("OPEN", "CLOSED", "FROZEN"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "INVALID_STATE_TRANSITION",
                    "message": f"Cannot freeze campaign in {campaign.status} state. Must be OPEN, CLOSED, or FROZEN.",
                    "request_id": request_id,
                    "details": {"current_status": campaign.status},
                }
            },
        )

    # If in OPEN or CLOSED, transition to FROZEN (auto-closes if OPEN)
    if campaign.status == "OPEN":
        campaign = await transition_campaign(db, campaign, "CLOSED", admin_id, request_id)
        campaign = await transition_campaign(db, campaign, "FROZEN", admin_id, request_id)
    elif campaign.status == "CLOSED":
        campaign = await transition_campaign(db, campaign, "FROZEN", admin_id, request_id)

    # Count eligible accepted registrations
    stmt = (
        select(func.count(Registration.id))
        .where(
            Registration.campaign_id == campaign_id,
            Registration.status == "ACCEPTED",
            Registration.eligible.is_(True),
        )
    )
    result = await db.execute(stmt)
    roster_count = result.scalar_one()

    return FreezeRosterResponse(
        campaign_id=campaign.id,
        status=campaign.status,
        roster_count=roster_count,
        frozen_at=datetime.now(timezone.utc),
        message="Campaign registration roster successfully frozen.",
    )


async def execute_lottery_draw(
    db: AsyncSession,
    campaign_id: uuid.UUID,
    seed: str | None,
    admin_id: uuid.UUID,
    request_id: str,
) -> LotteryDrawResponse:
    """
    Executes an atomic, deterministic uniform lottery draw for a FROZEN campaign.
    Generates LotteryRun, LotteryEntries, and Entitlements for winners.
    Transitions campaign state: FROZEN -> DRAWING -> CLAIMING.
    """
    campaign = await get_campaign_or_404(db, campaign_id, request_id)

    # Check for duplicate execution
    stmt_run = select(LotteryRun).where(LotteryRun.campaign_id == campaign_id)
    existing_run = (await db.execute(stmt_run)).scalar_one_or_none()
    if existing_run is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "LOTTERY_ALREADY_EXECUTED",
                    "message": "Lottery draw has already been executed for this campaign.",
                    "request_id": request_id,
                    "details": {"lottery_run_id": str(existing_run.id)},
                }
            },
        )

    if campaign.status != "FROZEN":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "INVALID_STATE_TRANSITION",
                    "message": f"Cannot execute draw on campaign in {campaign.status} state. Must be FROZEN.",
                    "request_id": request_id,
                    "details": {"current_status": campaign.status, "required_status": "FROZEN"},
                }
            },
        )

    # Transition to DRAWING state
    campaign = await transition_campaign(db, campaign, "DRAWING", admin_id, request_id)

    # Fetch all eligible accepted registrations with stable sorting
    stmt_reg = (
        select(Registration)
        .where(
            Registration.campaign_id == campaign_id,
            Registration.status == "ACCEPTED",
            Registration.eligible.is_(True),
        )
        .order_by(Registration.received_at.asc(), Registration.participant_id.asc())
    )
    registrations = list((await db.execute(stmt_reg)).scalars().all())

    # Compute stable roster hash
    roster_ids = [str(r.participant_id) for r in registrations]
    roster_hash = hashlib.sha256(",".join(roster_ids).encode("utf-8")).hexdigest()

    # Generate or sanitize randomness seed
    if not seed or not seed.strip():
        seed = secrets.token_hex(16)
    else:
        seed = seed.strip()

    seed_hash = hashlib.sha256(seed.encode("utf-8")).hexdigest()

    # Deterministic scoring & ranking
    scored_items: list[tuple[str, str, Registration]] = []
    for r in registrations:
        score = compute_participant_score(seed, r.participant_id)
        # Tiebreak on participant_id string for absolute reproducibility
        scored_items.append((score, str(r.participant_id), r))

    scored_items.sort(key=lambda item: (item[0], item[1]))

    now = datetime.now(timezone.utc)
    lottery_run_id = uuid.uuid4()
    total_eligible = len(scored_items)
    capacity = campaign.capacity
    total_winners = min(total_eligible, capacity)
    total_waitlisted = max(0, total_eligible - capacity)

    policy_v = campaign.policy_version or "v1.0"
    policy_h = campaign.policy_hash or hashlib.sha256(f"{campaign.id}:{policy_v}:{capacity}".encode("utf-8")).hexdigest()

    # 1. Create LotteryRun
    lottery_run = LotteryRun(
        id=lottery_run_id,
        campaign_id=campaign.id,
        policy_version=policy_v,
        policy_hash=policy_h,
        roster_hash=roster_hash,
        randomness_reference=seed,
        randomness_commitment=seed_hash,
        algorithm_version="hmac_sha256_v1",
        winner_count=total_winners,
        standby_count=total_waitlisted,
        executed_at=now,
        executed_by=admin_id,
    )
    db.add(lottery_run)
    await db.flush()

    # 2. Assign positions, create LotteryEntries and Entitlements
    for position, (_, _, reg) in enumerate(scored_items, start=1):
        is_winner = position <= capacity
        standby_pos = (position - capacity) if not is_winner else None

        entry = LotteryEntry(
            id=uuid.uuid4(),
            lottery_run_id=lottery_run_id,
            participant_id=reg.participant_id,
            registration_id=reg.id,
            position=position,
            selected=is_winner,
            standby_position=standby_pos,
            created_at=now,
        )
        db.add(entry)

        if is_winner:
            nonce_raw = f"{lottery_run_id}:{reg.participant_id}:{secrets.token_hex(16)}"
            nonce_hash = hashlib.sha256(nonce_raw.encode("utf-8")).hexdigest()

            entitlement = Entitlement(
                id=uuid.uuid4(),
                campaign_id=campaign.id,
                participant_id=reg.participant_id,
                lottery_run_id=lottery_run_id,
                nonce_hash=nonce_hash,
                status="SELECTED",
                expires_at=campaign.redemption_deadline,
                created_at=now,
                updated_at=now,
            )
            db.add(entitlement)

    # 3. Transition campaign: DRAWING -> CLAIMING
    campaign.status = "CLAIMING"
    campaign.updated_at = now

    # 4. Audit Log
    audit_event = AuditEvent(
        campaign_id=campaign.id,
        actor_type="ADMIN",
        actor_id=admin_id,
        event_type="LOTTERY_DRAW_EXECUTED",
        request_id=request_id,
        metadata_json={
            "lottery_run_id": str(lottery_run_id),
            "seed_hash": seed_hash,
            "total_eligible": total_eligible,
            "winner_count": total_winners,
            "standby_count": total_waitlisted,
            "capacity": capacity,
        },
    )
    db.add(audit_event)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        logger.error("Integrity error during lottery draw execution: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "LOTTERY_DRAW_CONFLICT",
                    "message": "A conflict occurred while executing the lottery draw. A draw may already exist.",
                    "request_id": request_id,
                    "details": {},
                }
            },
        )

    return LotteryDrawResponse(
        run_id=lottery_run_id,
        campaign_id=campaign.id,
        seed=seed,
        seed_hash=seed_hash,
        total_eligible=total_eligible,
        total_winners=total_winners,
        total_waitlisted=total_waitlisted,
        inventory_cap=capacity,
        executed_at=now,
        message="Lottery draw executed successfully.",
    )


async def get_participant_result(
    db: AsyncSession,
    campaign_id: uuid.UUID,
    participant_id: uuid.UUID,
    request_id: str,
) -> ParticipantResultResponse:
    """
    Retrieve authoritative lottery outcome and entitlement status for an individual participant.
    """
    campaign = await get_campaign_or_404(db, campaign_id, request_id)

    # Fetch lottery run for the campaign
    stmt_run = select(LotteryRun).where(LotteryRun.campaign_id == campaign_id)
    run = (await db.execute(stmt_run)).scalar_one_or_none()

    if run is None:
        # Check if participant is at least registered
        stmt_reg = select(Registration).where(
            Registration.campaign_id == campaign_id,
            Registration.participant_id == participant_id,
        )
        reg = (await db.execute(stmt_reg)).scalar_one_or_none()
        status_label = "PENDING_DRAW" if reg is not None else "NOT_REGISTERED"

        return ParticipantResultResponse(
            campaign_id=campaign_id,
            participant_id=participant_id,
            status=status_label,
            is_winner=False,
            rank=None,
            entitlement_id=None,
            entitlement_status=None,
            expires_at=None,
            randomness_commitment=None,
            draw_executed_at=None,
        )

    # Fetch lottery entry for the participant in this run
    stmt_entry = select(LotteryEntry).where(
        LotteryEntry.lottery_run_id == run.id,
        LotteryEntry.participant_id == participant_id,
    )
    entry = (await db.execute(stmt_entry)).scalar_one_or_none()

    if entry is None:
        return ParticipantResultResponse(
            campaign_id=campaign_id,
            participant_id=participant_id,
            status="NOT_REGISTERED",
            is_winner=False,
            rank=None,
            entitlement_id=None,
            entitlement_status=None,
            expires_at=None,
            randomness_commitment=run.randomness_commitment,
            draw_executed_at=run.executed_at,
        )

    if entry.selected:
        # Fetch entitlement details
        stmt_ent = select(Entitlement).where(
            Entitlement.campaign_id == campaign_id,
            Entitlement.participant_id == participant_id,
            Entitlement.lottery_run_id == run.id,
        )
        entitlement = (await db.execute(stmt_ent)).scalar_one_or_none()

        return ParticipantResultResponse(
            campaign_id=campaign_id,
            participant_id=participant_id,
            status="WON",
            is_winner=True,
            rank=entry.position,
            entitlement_id=entitlement.id if entitlement else None,
            entitlement_status=entitlement.status if entitlement else "SELECTED",
            expires_at=entitlement.expires_at if entitlement else campaign.redemption_deadline,
            randomness_commitment=run.randomness_commitment,
            draw_executed_at=run.executed_at,
        )

    return ParticipantResultResponse(
        campaign_id=campaign_id,
        participant_id=participant_id,
        status="WAITLISTED",
        is_winner=False,
        rank=entry.position,
        entitlement_id=None,
        entitlement_status=None,
        expires_at=None,
        randomness_commitment=run.randomness_commitment,
        draw_executed_at=run.executed_at,
    )

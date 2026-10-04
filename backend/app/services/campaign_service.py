"""
Core campaign business logic service.

Enforces the explicit 8-stage state machine, deterministic policy hashing,
bulk seat inventory generation, audit logging, and participant recovery evaluation.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditEvent
from app.models.campaign import Campaign, CampaignPolicySnapshot
from app.models.inventory import Seat
from app.models.registration import Registration

logger = logging.getLogger(__name__)

# Explicit state transition graph
VALID_TRANSITIONS: dict[str, list[str]] = {
    "DRAFT": ["PREPARING", "OPEN"],
    "PREPARING": ["DRAFT", "OPEN"],
    "OPEN": ["CLOSED"],
    "CLOSED": ["FROZEN"],
    "FROZEN": ["DRAWING"],
    "DRAWING": ["CLAIMING"],
    "CLAIMING": ["COMPLETED"],
    "COMPLETED": [],
}

SCOPE_MAP: dict[str, str] = {
    "ADMISSION": "admission_paused",
    "REGISTRATION": "registration_paused",
    "REDEMPTION": "redemption_paused",
}


def validate_transition(current: str, target: str, request_id: str) -> None:
    """
    Ensure the target status is a valid successor of the current status.
    Raises 409 Conflict with code INVALID_STATE_TRANSITION on invalid progression.
    """
    allowed = VALID_TRANSITIONS.get(current, [])
    if target not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "INVALID_STATE_TRANSITION",
                    "message": f"Cannot transition campaign from {current} to {target}",
                    "request_id": request_id,
                    "details": {"current_status": current, "target_status": target},
                }
            },
        )


def compute_policy_hash(campaign: Campaign) -> str:
    """
    Compute a deterministic SHA-256 hash across immutable policy fields.
    """
    policy_dict = {
        "allocation_method": campaign.allocation_method,
        "capacity": campaign.capacity,
        "max_tickets_per_participant": campaign.max_tickets_per_participant,
        "policy_version": campaign.policy_version,
        "redemption_deadline": campaign.redemption_deadline.isoformat(),
        "registration_end": campaign.registration_end.isoformat(),
        "registration_start": campaign.registration_start.isoformat(),
        "standby_policy": campaign.standby_policy,
    }
    serialized = json.dumps(policy_dict, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def generate_seat_labels(capacity: int) -> list[dict]:
    """
    Generate deterministic seat labels distributed evenly across sections.
    Sections A-Z (26 sections), expanding to AA, AB... if capacity > 520.
    """
    base_letters = [chr(c) for c in range(ord("A"), ord("Z") + 1)]
    if capacity <= 520:
        section_names = base_letters
    else:
        section_names = list(base_letters)
        for c1 in base_letters:
            for c2 in base_letters:
                section_names.append(f"{c1}{c2}")
                if len(section_names) * 20 >= capacity:
                    break
            if len(section_names) * 20 >= capacity:
                break

    num_sections = len(section_names)
    seats_per_section = (capacity + num_sections - 1) // num_sections

    seats: list[dict] = []
    created_count = 0

    for section in section_names:
        for seat_num in range(1, seats_per_section + 1):
            if created_count >= capacity:
                break
            seats.append({
                "seat_label": f"{section}-{seat_num}",
                "section": section,
                "row_label": section,
                "seat_number": seat_num,
            })
            created_count += 1
        if created_count >= capacity:
            break

    return seats


async def get_seat_counts(db: AsyncSession, campaign_id: uuid.UUID) -> dict[str, int]:
    """Aggregate seat inventory counts by status for a campaign."""
    stmt = (
        select(Seat.status, func.count(Seat.id))
        .where(Seat.campaign_id == campaign_id)
        .group_by(Seat.status)
    )
    result = await db.execute(stmt)
    counts = {"available": 0, "held": 0, "confirmed": 0, "total": 0}
    for status_val, count_val in result.all():
        key = status_val.lower()
        if key in counts:
            counts[key] = count_val
        counts["total"] += count_val
    return counts


async def get_registration_counts(db: AsyncSession, campaign_id: uuid.UUID) -> dict[str, int]:
    """Aggregate participant registrations by status for a campaign."""
    stmt = (
        select(Registration.status, func.count(Registration.id))
        .where(Registration.campaign_id == campaign_id)
        .group_by(Registration.status)
    )
    result = await db.execute(stmt)
    counts = {"total": 0, "accepted": 0, "duplicate": 0, "rejected": 0}
    for status_val, count_val in result.all():
        key = status_val.lower()
        if key in counts:
            counts[key] = count_val
        counts["total"] += count_val
    return counts


async def create_campaign(
    db: AsyncSession,
    data: dict,
    admin_id: uuid.UUID,
    request_id: str,
) -> Campaign:
    """Create a new campaign in DRAFT state and record an audit event."""
    campaign = Campaign(
        **data,
        status="DRAFT",
        created_by=admin_id,
    )
    db.add(campaign)
    await db.flush()

    audit_event = AuditEvent(
        campaign_id=campaign.id,
        actor_type="ADMIN",
        actor_id=admin_id,
        event_type="CAMPAIGN_CREATED",
        request_id=request_id,
        metadata_json={"name": campaign.name, "capacity": campaign.capacity},
    )
    db.add(audit_event)
    await db.commit()
    await db.refresh(campaign)
    return campaign


async def get_campaign_or_404(
    db: AsyncSession,
    campaign_id: uuid.UUID,
    request_id: str = "unknown",
) -> Campaign:
    """Retrieve campaign by ID or raise 404 CAMPAIGN_NOT_FOUND."""
    stmt = select(Campaign).where(Campaign.id == campaign_id)
    result = await db.execute(stmt)
    campaign = result.scalar_one_or_none()

    if campaign is None:
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
    return campaign


async def update_campaign_draft(
    db: AsyncSession,
    campaign: Campaign,
    data: dict,
    admin_id: uuid.UUID,
    request_id: str,
) -> Campaign:
    """Update editable fields while campaign is in DRAFT or PREPARING."""
    if campaign.status not in ("DRAFT", "PREPARING"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "CAMPAIGN_NOT_EDITABLE",
                    "message": f"Campaign in {campaign.status} state cannot be updated",
                    "request_id": request_id,
                    "details": {"status": campaign.status},
                }
            },
        )

    updated_fields = []
    for key, value in data.items():
        if value is not None and hasattr(campaign, key):
            setattr(campaign, key, value)
            updated_fields.append(key)

    audit_event = AuditEvent(
        campaign_id=campaign.id,
        actor_type="ADMIN",
        actor_id=admin_id,
        event_type="CAMPAIGN_UPDATED",
        request_id=request_id,
        metadata_json={"updated_fields": updated_fields},
    )
    db.add(audit_event)
    await db.commit()
    await db.refresh(campaign)
    return campaign


async def prepare_campaign(
    db: AsyncSession,
    campaign: Campaign,
    admin_id: uuid.UUID,
    request_id: str,
) -> Campaign:
    """
    Transition campaign from DRAFT to PREPARING, compute policy hash,
    and bulk-generate seat inventory.
    """
    validate_transition(campaign.status, "PREPARING", request_id)

    campaign.status = "PREPARING"
    campaign.policy_hash = compute_policy_hash(campaign)

    # Check if seats already exist for this campaign
    seat_count_stmt = select(func.count(Seat.id)).where(Seat.campaign_id == campaign.id)
    count_result = await db.execute(seat_count_stmt)
    existing_seats = count_result.scalar_one()

    seats_generated = 0
    if existing_seats == 0:
        labels = generate_seat_labels(campaign.capacity)
        now_dt = datetime.now(timezone.utc)
        seat_dicts = [
            {
                "id": uuid.uuid4(),
                "campaign_id": campaign.id,
                "seat_label": item["seat_label"],
                "section": item["section"],
                "row_label": item["row_label"],
                "seat_number": item["seat_number"],
                "status": "AVAILABLE",
                "version": 1,
                "created_at": now_dt,
                "updated_at": now_dt,
            }
            for item in labels
        ]
        if seat_dicts:
            await db.execute(insert(Seat), seat_dicts)
        seats_generated = len(seat_dicts)

    audit_event = AuditEvent(
        campaign_id=campaign.id,
        actor_type="ADMIN",
        actor_id=admin_id,
        event_type="CAMPAIGN_PREPARED",
        request_id=request_id,
        metadata_json={
            "seats_generated": seats_generated,
            "policy_hash": campaign.policy_hash,
        },
    )
    db.add(audit_event)
    await db.commit()
    await db.refresh(campaign)
    return campaign


async def transition_campaign(
    db: AsyncSession,
    campaign: Campaign,
    target_status: str,
    admin_id: uuid.UUID,
    request_id: str,
) -> Campaign:
    """
    Transition a campaign to a valid target lifecycle state.
    Handles OPEN published_at logic, FROZEN policy snapshotting, and audit logging.
    """
    validate_transition(campaign.status, target_status, request_id)
    now = datetime.now(timezone.utc)
    previous_status = campaign.status

    if target_status == "OPEN":
        # If transitioning directly from DRAFT, auto-prepare seat inventory first
        if campaign.status == "DRAFT":
            campaign = await prepare_campaign(db, campaign, admin_id, request_id)

        # Advance registration_start to now if configured in the future so registrations are immediately open
        if campaign.registration_start > now:
            campaign.registration_start = now

        # If registration_end expired in the past, extend it 7 days so participants can register
        if campaign.registration_end <= now:
            campaign.registration_end = now + timedelta(days=7)
            campaign.redemption_deadline = campaign.registration_end + timedelta(days=1)

        campaign.status = "OPEN"
        campaign.published_at = now
        campaign.policy_hash = compute_policy_hash(campaign)

    elif target_status == "FROZEN":
        # Capture immutable policy snapshot
        policy_h = campaign.policy_hash or compute_policy_hash(campaign)
        roster_placeholder = hashlib.sha256(
            f"{campaign.id}:{policy_h}:empty-roster".encode("utf-8")
        ).hexdigest()

        snapshot_data = {
            "campaign_id": str(campaign.id),
            "name": campaign.name,
            "description": campaign.description,
            "venue": campaign.venue,
            "capacity": campaign.capacity,
            "allocation_method": campaign.allocation_method,
            "standby_policy": campaign.standby_policy,
            "policy_version": campaign.policy_version,
            "policy_hash": policy_h,
            "roster_hash": roster_placeholder,
            "max_tickets_per_participant": campaign.max_tickets_per_participant,
            "registration_start": campaign.registration_start.isoformat(),
            "registration_end": campaign.registration_end.isoformat(),
            "redemption_deadline": campaign.redemption_deadline.isoformat(),
            "frozen_at": now.isoformat(),
        }

        snapshot = CampaignPolicySnapshot(
            campaign_id=campaign.id,
            policy_version=campaign.policy_version,
            policy_hash=policy_h,
            snapshot_data=snapshot_data,
        )
        db.add(snapshot)

    campaign.status = target_status

    audit_event = AuditEvent(
        campaign_id=campaign.id,
        actor_type="ADMIN",
        actor_id=admin_id,
        event_type=f"CAMPAIGN_{target_status}",
        request_id=request_id,
        metadata_json={"previous_status": previous_status, "new_status": target_status},
    )
    db.add(audit_event)
    await db.commit()
    await db.refresh(campaign)
    return campaign


async def pause_campaign_scope(
    db: AsyncSession,
    campaign: Campaign,
    scope: str,
    reason: str,
    admin_id: uuid.UUID,
    request_id: str,
) -> Campaign:
    """Pause an operational scope without changing campaign lifecycle state."""
    attr_name = SCOPE_MAP.get(scope)
    if not attr_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_SCOPE",
                    "message": f"Invalid pause scope: {scope}",
                    "request_id": request_id,
                    "details": {},
                }
            },
        )
    setattr(campaign, attr_name, True)
    audit_event = AuditEvent(
        campaign_id=campaign.id,
        actor_type="ADMIN",
        actor_id=admin_id,
        event_type="CAMPAIGN_PAUSED",
        reason_code=scope,
        metadata_json={"reason": reason, "scope": scope},
        request_id=request_id,
    )
    db.add(audit_event)
    await db.commit()
    await db.refresh(campaign)
    return campaign


async def resume_campaign_scope(
    db: AsyncSession,
    campaign: Campaign,
    scope: str,
    admin_id: uuid.UUID,
    request_id: str,
) -> Campaign:
    """Resume an operational scope without changing campaign lifecycle state."""
    attr_name = SCOPE_MAP.get(scope)
    if not attr_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_SCOPE",
                    "message": f"Invalid resume scope: {scope}",
                    "request_id": request_id,
                    "details": {},
                }
            },
        )
    setattr(campaign, attr_name, False)
    audit_event = AuditEvent(
        campaign_id=campaign.id,
        actor_type="ADMIN",
        actor_id=admin_id,
        event_type="CAMPAIGN_RESUMED",
        reason_code=scope,
        metadata_json={"scope": scope},
        request_id=request_id,
    )
    db.add(audit_event)
    await db.commit()
    await db.refresh(campaign)
    return campaign


async def list_public_campaigns(
    db: AsyncSession,
    status_filter: str | None,
    page: int,
    page_size: int,
) -> tuple[list[Campaign], int]:
    """Query published campaigns excluding DRAFT and PREPARING."""
    base_conditions = [Campaign.status.notin_(["DRAFT", "PREPARING"])]
    if status_filter:
        base_conditions.append(Campaign.status == status_filter)

    count_stmt = select(func.count(Campaign.id)).where(*base_conditions)
    total_count = (await db.execute(count_stmt)).scalar_one()

    query_stmt = (
        select(Campaign)
        .where(*base_conditions)
        .order_by(Campaign.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query_stmt)
    campaigns = list(result.scalars().all())
    return campaigns, total_count


async def get_campaign_status(
    db: AsyncSession,
    campaign: Campaign,
    participant_id: uuid.UUID,
    request_id: str,
) -> dict:
    """Evaluate full participant state for recovery endpoint."""
    reg_stmt = select(Registration).where(
        Registration.campaign_id == campaign.id,
        Registration.participant_id == participant_id,
    )
    reg_result = await db.execute(reg_stmt)
    registration = reg_result.scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if registration is None:
        participant_state = "NOT_REGISTERED"
        reg_data = None
        reg_slice = {
            "is_registered": False,
            "registration_id": None,
            "registered_at": None,
            "risk_level": None,
        }
    else:
        participant_state = "REGISTERED"
        reg_data = {
            "id": str(registration.id),
            "status": registration.status,
            "eligible": registration.eligible,
            "is_registered": True,
            "registration_id": str(registration.id),
            "registered_at": (
                registration.received_at.isoformat()
                if registration.received_at
                else None
            ),
            "risk_level": registration.risk_level,
            "created_at": (
                registration.received_at.isoformat()
                if registration.received_at
                else None
            ),
        }
        reg_slice = {
            "is_registered": True,
            "registration_id": str(registration.id),
            "registered_at": (
                registration.received_at.isoformat()
                if registration.received_at
                else None
            ),
            "risk_level": registration.risk_level,
        }

    admission_state = None
    if campaign.status == "OPEN":
        admission_state = "OPEN"
    elif campaign.status in ("CLOSED", "FROZEN", "DRAWING"):
        admission_state = "CLOSED"

    admission_data = (
        {"state": admission_state, "permit_expires_at": None}
        if admission_state
        else None
    )

    return {
        "campaign": {
            "id": str(campaign.id),
            "status": campaign.status,
            "registration_end": campaign.registration_end.isoformat(),
            "redemption_deadline": campaign.redemption_deadline.isoformat(),
            "server_time": now.isoformat(),
        },
        "participant_state": participant_state,
        "registration": reg_data,
        "registration_slice": reg_slice,
        "admission": admission_data,
        "challenge": None,
        "entitlement": None,
        "seat_hold": None,
    }

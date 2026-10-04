"""
Registration service orchestrating fair registration, idempotency, and challenge seams.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditEvent
from app.models.campaign import Campaign
from app.models.challenge import Challenge
from app.models.registration import IdempotencyRecord, Registration
from app.schemas.registration import RegisterRequest, RegisterResponse
from app.services.admission_service import _build_error, verify_and_consume_permit

logger = logging.getLogger(__name__)


def _compute_canonical_request_hash(
    body: RegisterRequest,
    participant_id: uuid.UUID,
    campaign_id: uuid.UUID,
) -> str:
    """
    Generate deterministic SHA-256 hash of registration payload + identities.
    """
    data: dict[str, Any] = {
        "admission_token": body.admission_token,
        "campaign_id": str(campaign_id),
        "client_meta": body.client_meta or {},
        "nonce": body.nonce,
        "participant_id": str(participant_id),
    }
    serialized = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


async def _compute_risk_level(
    db: AsyncSession,
    participant_id: uuid.UUID,
    campaign_id: uuid.UUID,
) -> str:
    """
    Risk scoring placeholder seam.
    Step 5 returns LOW. Future steps will evaluate IP velocity, session anomalies, etc.
    """
    return "LOW"


async def _has_valid_passed_challenge(
    db: AsyncSession,
    *,
    participant_id: uuid.UUID,
    session_id: uuid.UUID | None,
    campaign_id: uuid.UUID,
    operation: str = "REGISTER",
) -> bool:
    """
    Integration seam with Naman's Challenge Contract.
    Queries the challenges table (read-only) for a recent PASSED challenge.
    """
    window_start = datetime.now(timezone.utc) - timedelta(minutes=5)
    conditions = [
        Challenge.campaign_id == campaign_id,
        Challenge.status == "PASSED",
        Challenge.created_at >= window_start,
    ]
    if session_id:
        conditions.append(
            (Challenge.session_id == session_id) | (Challenge.participant_id == participant_id)
        )
    else:
        conditions.append(Challenge.participant_id == participant_id)

    stmt = select(Challenge).where(*conditions)
    result = await db.execute(stmt)
    return result.scalars().first() is not None


async def register_participant(
    db: AsyncSession,
    *,
    campaign_id: uuid.UUID,
    participant_id: uuid.UUID,
    session_id: uuid.UUID | None = None,
    body: RegisterRequest,
    idempotency_key: str,
    request_id: str = "unknown",
) -> tuple[RegisterResponse, int]:
    """
    Register participant with full idempotency, single-use permit consumption, and challenge verification.
    Returns (RegisterResponse, status_code) where status_code is 201 for new registrations and 200 for replays.
    """
    scope = f"register:{campaign_id}"
    req_hash = _compute_canonical_request_hash(body, participant_id, campaign_id)

    # ─────────────────────────────────────────────────────────────────────────
    # 1. IDEMPOTENCY GATE (First)
    # ─────────────────────────────────────────────────────────────────────────
    idemp_stmt = select(IdempotencyRecord).where(
        IdempotencyRecord.scope == scope,
        IdempotencyRecord.key == idempotency_key,
    )
    existing_record = (await db.execute(idemp_stmt)).scalar_one_or_none()

    if existing_record is not None:
        if existing_record.request_hash == req_hash:
            logger.info("Idempotent replay detected for key %s", idempotency_key)
            return RegisterResponse(**existing_record.response_body_json), status.HTTP_200_OK

        raise _build_error(
            "IDEMPOTENCY_CONFLICT",
            "Idempotency key has already been used with a different request payload",
            request_id,
            status.HTTP_409_CONFLICT,
            details={"idempotency_key": idempotency_key},
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 2. CAMPAIGN GUARDS
    # ─────────────────────────────────────────────────────────────────────────
    camp_stmt = select(Campaign).where(Campaign.id == campaign_id)
    campaign = (await db.execute(camp_stmt)).scalar_one_or_none()
    if campaign is None:
        raise _build_error(
            "CAMPAIGN_NOT_FOUND",
            f"Campaign {campaign_id} not found",
            request_id,
            status.HTTP_404_NOT_FOUND,
        )

    if campaign.status in ("DRAFT", "PREPARING"):
        raise _build_error(
            "REGISTRATION_NOT_STARTED",
            f"Registration has not started yet (campaign status: {campaign.status})",
            request_id,
            status.HTTP_409_CONFLICT,
        )

    if campaign.status != "OPEN":
        raise _build_error(
            "REGISTRATION_CLOSED",
            f"Registration is closed (campaign status: {campaign.status})",
            request_id,
            status.HTTP_409_CONFLICT,
        )

    if campaign.registration_paused:
        raise _build_error(
            "CAMPAIGN_PAUSED",
            "Campaign registration is temporarily paused",
            request_id,
            status.HTTP_409_CONFLICT,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 3. VERIFY & CONSUME ADMISSION PERMIT
    # ─────────────────────────────────────────────────────────────────────────
    permit = await verify_and_consume_permit(
        db,
        admission_token=body.admission_token,
        nonce=body.nonce,
        campaign_id=campaign_id,
        participant_id=participant_id,
        session_id=session_id,
        request_id=request_id,
    )
    resolved_session_id = permit.session_id

    # ─────────────────────────────────────────────────────────────────────────
    # 4. UNIQUENESS CHECK
    # ─────────────────────────────────────────────────────────────────────────
    reg_stmt = select(Registration).where(
        Registration.campaign_id == campaign_id,
        Registration.participant_id == participant_id,
    )
    existing_reg = (await db.execute(reg_stmt)).scalar_one_or_none()
    if existing_reg is not None:
        raise _build_error(
            "DUPLICATE_ENTRY",
            "Participant is already registered for this campaign",
            request_id,
            status.HTTP_409_CONFLICT,
            details={"registration_id": str(existing_reg.id)},
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 5. CHALLENGE SEAM & RISK GATE
    # ─────────────────────────────────────────────────────────────────────────
    risk = await _compute_risk_level(db, participant_id, campaign_id)
    if risk in ("MEDIUM", "HIGH"):
        has_passed = await _has_valid_passed_challenge(
            db,
            participant_id=participant_id,
            session_id=resolved_session_id,
            campaign_id=campaign_id,
            operation="REGISTER",
        )
        if not has_passed:
            raise _build_error(
                "CHALLENGE_REQUIRED",
                "Proof-of-human challenge verification required before registration",
                request_id,
                status.HTTP_403_FORBIDDEN,
                details={"operation": "REGISTER", "risk_level": risk},
            )

    # ─────────────────────────────────────────────────────────────────────────
    # 6. ATOMIC WRITE: REGISTRATION + IDEMPOTENCY + AUDIT
    # ─────────────────────────────────────────────────────────────────────────
    now = datetime.now(timezone.utc)
    # Stored as 'ACCEPTED' to satisfy PostgreSQL ck_registrations_status constraint
    registration = Registration(
        campaign_id=campaign_id,
        participant_id=participant_id,
        idempotency_key=idempotency_key,
        request_hash=req_hash,
        status="ACCEPTED",
        eligible=True,
        risk_score=0,
        risk_level=risk,
        reason_code=None,
        received_at=now,
        validated_at=now,
    )
    db.add(registration)

    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        err_msg = str(exc).lower()
        if "uq_registrations_campaign_participant" in err_msg or "duplicate" in err_msg:
            raise _build_error(
                "DUPLICATE_ENTRY",
                "Participant is already registered for this campaign",
                request_id,
                status.HTTP_409_CONFLICT,
            ) from exc
        if "uq_registrations_campaign_idempotency" in err_msg or "uq_idempotency" in err_msg:
            raise _build_error(
                "IDEMPOTENCY_CONFLICT",
                "Idempotency conflict detected",
                request_id,
                status.HTTP_409_CONFLICT,
            ) from exc
        raise

    # 7. Formulate API response (status='REGISTERED' returned to client)
    response_model = RegisterResponse(
        registration_id=registration.id,
        campaign_id=campaign_id,
        participant_id=participant_id,
        status="REGISTERED",
        registered_at=registration.received_at,
        risk_level=risk,
        challenge_required=False,
        message="Registration accepted successfully",
    )

    # 8. Persist Idempotency Record
    idemp_rec = IdempotencyRecord(
        scope=scope,
        key=idempotency_key,
        actor_id=participant_id,
        campaign_id=campaign_id,
        request_hash=req_hash,
        response_status=status.HTTP_201_CREATED,
        response_body_json=response_model.model_dump(mode="json"),
        resource_type="registration",
        resource_id=registration.id,
        expires_at=now + timedelta(hours=24),
    )
    db.add(idemp_rec)

    # 9. Audit event
    audit = AuditEvent(
        campaign_id=campaign_id,
        participant_id=participant_id,
        session_id=resolved_session_id,
        actor_type="USER",
        actor_id=participant_id,
        event_type="REGISTRATION_CREATED",
        reason_code=None,
        metadata_json={
            "registration_id": str(registration.id),
            "idempotency_key": idempotency_key,
            "risk_level": risk,
        },
        request_id=request_id,
    )
    db.add(audit)

    await db.commit()
    await db.refresh(registration)

    return response_model, status.HTTP_201_CREATED

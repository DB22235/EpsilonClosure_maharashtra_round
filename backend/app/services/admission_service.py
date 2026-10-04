"""
Admission service for cryptographic waiting room passes and atomic permit consumption.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import lru_settings
from app.models.admission import AdmissionPermit
from app.models.audit import AuditEvent
from app.models.campaign import Campaign
from app.models.participant import Session
from app.schemas.registration import JoinResponse

logger = logging.getLogger(__name__)


def _build_error(
    code: str,
    message: str,
    request_id: str,
    http_status: int,
    details: dict | None = None,
) -> HTTPException:
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


def _get_signing_keys() -> tuple[str, str]:
    settings = lru_settings()
    key_id = settings.SIGNING_KEY_ID or "fair-drop-dev-key-1"
    key = settings.SIGNING_PRIVATE_KEY or f"{settings.EMAIL_HASH_PEPPER}-permit-secret"
    return key_id, key


async def _get_or_create_session(
    db: AsyncSession,
    participant_id: uuid.UUID,
    campaign_id: uuid.UUID,
    subject_id: uuid.UUID | None = None,
) -> uuid.UUID:
    """
    Ensure an active user session exists to satisfy the foreign key on admission_permits.
    """
    now = datetime.now(timezone.utc)
    stmt = (
        select(Session)
        .where(
            Session.participant_id == participant_id,
            Session.campaign_id == campaign_id,
            Session.status == "ACTIVE",
            Session.idle_expires_at > now,
        )
        .order_by(Session.last_activity_at.desc())
    )
    result = await db.execute(stmt)
    existing_session = result.scalars().first()
    if existing_session is not None:
        existing_session.last_activity_at = now
        return existing_session.id

    settings = lru_settings()
    idle_expires = now + timedelta(seconds=settings.IDLE_SESSION_SECONDS)
    absolute_expires = now + timedelta(seconds=settings.ABSOLUTE_REDEMPTION_SECONDS)

    new_session = Session(
        participant_id=participant_id,
        campaign_id=campaign_id,
        supabase_subject=subject_id or participant_id,
        created_at=now,
        last_activity_at=now,
        absolute_expires_at=absolute_expires,
        idle_expires_at=idle_expires,
        status="ACTIVE",
    )
    db.add(new_session)
    await db.flush()
    return new_session.id


async def create_admission_permit(
    db: AsyncSession,
    *,
    campaign_id: uuid.UUID,
    participant_id: uuid.UUID,
    session_id: uuid.UUID | None = None,
    subject_id: uuid.UUID | None = None,
    request_id: str = "unknown",
) -> JoinResponse:
    """
    Issue a short-lived, HMAC-SHA256 signed admission permit for registration entry.
    """
    # 1. Campaign state validation
    stmt = select(Campaign).where(Campaign.id == campaign_id)
    campaign = (await db.execute(stmt)).scalar_one_or_none()
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

    if campaign.admission_paused or campaign.registration_paused:
        raise _build_error(
            "CAMPAIGN_PAUSED",
            "Campaign admission or registration is temporarily paused",
            request_id,
            status.HTTP_409_CONFLICT,
        )

    # 2. Session resolution
    resolved_session_id = session_id
    if resolved_session_id is None:
        resolved_session_id = await _get_or_create_session(
            db, participant_id, campaign_id, subject_id
        )

    # 3. Cryptographic permit generation
    now = datetime.now(timezone.utc)
    settings = lru_settings()
    ttl_seconds = getattr(settings, "ADMISSION_PERMIT_TTL_SECONDS", 300)
    expires_at = now + timedelta(seconds=ttl_seconds)
    nonce = secrets.token_hex(16)  # 32-char cryptographically secure hex
    key_id, signing_key = _get_signing_keys()

    exp_unix = int(expires_at.timestamp())
    payload = f"{campaign_id}|{participant_id}|{resolved_session_id}|{nonce}|{exp_unix}|{key_id}"
    signature = hmac.new(
        signing_key.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    raw_token = f"{payload}:{signature}"
    admission_token = base64.urlsafe_b64encode(raw_token.encode("utf-8")).decode("utf-8")

    # 4. Persist admission permit
    permit = AdmissionPermit(
        campaign_id=campaign_id,
        participant_id=participant_id,
        session_id=resolved_session_id,
        nonce=nonce,
        allowed_operation="REGISTER",
        key_id=key_id,
        signature=signature,
        issued_at=now,
        expires_at=expires_at,
        consumed=False,
    )
    db.add(permit)

    # 5. Audit log event
    audit = AuditEvent(
        campaign_id=campaign_id,
        participant_id=participant_id,
        session_id=resolved_session_id,
        actor_type="USER",
        actor_id=participant_id,
        event_type="ADMISSION_PERMIT_ISSUED",
        reason_code=None,
        metadata_json={
            "permit_id": str(permit.id),
            "key_id": key_id,
            "expires_at": expires_at.isoformat(),
        },
        request_id=request_id,
    )
    db.add(audit)
    await db.commit()
    await db.refresh(permit)

    return JoinResponse(
        permit_id=permit.id,
        admission_token=admission_token,
        nonce=nonce,
        expires_at=expires_at,
        campaign_id=campaign_id,
        server_time=now,
    )


async def verify_and_consume_permit(
    db: AsyncSession,
    *,
    admission_token: str,
    nonce: str,
    campaign_id: uuid.UUID,
    participant_id: uuid.UUID,
    session_id: uuid.UUID | None = None,
    request_id: str = "unknown",
) -> AdmissionPermit:
    """
    Fail-closed cryptographic verification and atomic single-use consumption of an admission permit.
    """
    # 1. Parse and decode token
    try:
        raw_token = base64.urlsafe_b64decode(admission_token.encode("utf-8")).decode("utf-8")
        payload, signature = raw_token.rsplit(":", 1)
        token_camp, token_part, token_sess, token_nonce, exp_unix_str, token_key_id = (
            payload.split("|")
        )
    except Exception as exc:
        logger.warning("Invalid admission token format: %s", exc)
        raise _build_error(
            "ADMISSION_REQUIRED",
            "Invalid admission permit token structure",
            request_id,
            status.HTTP_403_FORBIDDEN,
        ) from exc

    # 2. Cryptographic signature check
    _key_id, signing_key = _get_signing_keys()
    expected_sig = hmac.new(
        signing_key.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(signature, expected_sig):
        raise _build_error(
            "ADMISSION_REQUIRED",
            "Admission permit token signature verification failed",
            request_id,
            status.HTTP_403_FORBIDDEN,
        )

    # 3. Caller and scope binding checks
    if token_camp != str(campaign_id):
        raise _build_error(
            "ADMISSION_REQUIRED",
            "Permit is not valid for this campaign",
            request_id,
            status.HTTP_403_FORBIDDEN,
        )

    if token_part != str(participant_id):
        raise _build_error(
            "ADMISSION_REQUIRED",
            "Permit does not belong to the authenticated participant",
            request_id,
            status.HTTP_403_FORBIDDEN,
        )

    if token_nonce != nonce:
        raise _build_error(
            "ADMISSION_REQUIRED",
            "Permit nonce does not match request nonce",
            request_id,
            status.HTTP_403_FORBIDDEN,
        )

    now = datetime.now(timezone.utc)
    if now.timestamp() > float(exp_unix_str):
        raise _build_error(
            "ADMISSION_PERMIT_EXPIRED",
            "Admission permit token has expired",
            request_id,
            status.HTTP_410_GONE,
        )

    # 4. Database existence and replay verification
    stmt = select(AdmissionPermit).where(
        AdmissionPermit.nonce == nonce,
        AdmissionPermit.campaign_id == campaign_id,
        AdmissionPermit.participant_id == participant_id,
    )
    permit = (await db.execute(stmt)).scalar_one_or_none()
    if permit is None:
        raise _build_error(
            "ADMISSION_REQUIRED",
            "Admission permit record not found in system authority",
            request_id,
            status.HTTP_403_FORBIDDEN,
        )

    if permit.consumed:
        raise _build_error(
            "ADMISSION_PERMIT_REPLAYED",
            "Admission permit has already been consumed",
            request_id,
            status.HTTP_409_CONFLICT,
        )

    if now > permit.expires_at:
        raise _build_error(
            "ADMISSION_PERMIT_EXPIRED",
            "Admission permit record has expired",
            request_id,
            status.HTTP_410_GONE,
        )

    # 5. Atomic single-use consumption update
    update_stmt = (
        update(AdmissionPermit)
        .where(
            AdmissionPermit.id == permit.id,
            AdmissionPermit.consumed.is_(False),
        )
        .values(consumed=True, consumed_at=now)
    )
    res = await db.execute(update_stmt)
    if res.rowcount == 0:
        raise _build_error(
            "ADMISSION_PERMIT_REPLAYED",
            "Admission permit was consumed concurrently",
            request_id,
            status.HTTP_409_CONFLICT,
        )

    # 6. Audit event
    audit = AuditEvent(
        campaign_id=campaign_id,
        participant_id=participant_id,
        session_id=permit.session_id,
        actor_type="USER",
        actor_id=participant_id,
        event_type="ADMISSION_PERMIT_CONSUMED",
        reason_code=None,
        metadata_json={"permit_id": str(permit.id), "nonce": nonce},
        request_id=request_id,
    )
    db.add(audit)

    return permit

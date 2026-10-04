"""
Challenge service for proof-of-human validation flows.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.challenge_adapter import ChallengeAdapter
from app.models.audit import AuditEvent, MetricEvent
from app.models.challenge import Challenge
from app.schemas.challenge import (
    ChallengeCreateRequest,
    ChallengeCreateResponse,
    ChallengeMetricsSummaryResponse,
    ChallengeStatus,
    ChallengeType,
    ChallengeTypeBreakdown,
    ChallengeVerifyRequest,
    ChallengeVerifyResponse,
)


def generate_nonce() -> str:
    """Generate a 32-character hex verification nonce."""
    return secrets.token_hex(16)


def hash_nonce(nonce: str) -> str:
    """Compute SHA-256 hash of a raw verification nonce."""
    return hashlib.sha256(nonce.encode("utf-8")).hexdigest()


async def check_cooldown_status(
    db: AsyncSession,
    session_id: uuid.UUID,
    participant_id: uuid.UUID | None = None,
    cooldown_seconds: int = 300,
    threshold: int = 3,
) -> tuple[bool, int, str | None]:
    """
    Check if a session/participant is under cooldown due to >= 3 failed/expired challenges in the window.
    Returns: (is_active, retry_after_seconds, cooldown_expires_at_iso)
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=cooldown_seconds)

    cond = Challenge.session_id == session_id
    if participant_id:
        cond = (Challenge.session_id == session_id) | (Challenge.participant_id == participant_id)

    stmt = (
        select(Challenge)
        .where(
            cond,
            Challenge.status.in_(["FAILED", "EXPIRED"]),
            Challenge.created_at >= cutoff,
        )
        .order_by(Challenge.created_at.desc())
    )
    res = await db.execute(stmt)
    failures = res.scalars().all()

    if len(failures) >= threshold:
        latest_failure = failures[0].created_at
        if latest_failure.tzinfo is None:
            latest_failure = latest_failure.replace(tzinfo=timezone.utc)
        cooldown_expires_at = latest_failure + timedelta(seconds=cooldown_seconds)
        if cooldown_expires_at > now:
            retry_after = int((cooldown_expires_at - now).total_seconds())
            return True, max(retry_after, 1), cooldown_expires_at.isoformat()

    return False, 0, None


def evaluate_challenge_risk(
    duration_ms: int,
    confidence: float | None,
    attempts: int,
    gesture_type: str,
) -> tuple[str, str]:
    """
    Evaluates verification telemetry and returns (risk_level, reason_code).
    """
    if duration_ms < 800:
        return "HIGH", "TELEMETRY_ANOMALY_TOO_FAST"
    if duration_ms > 15000:
        return "MEDIUM", "TELEMETRY_ANOMALY_TOO_SLOW"
    if confidence is not None and confidence < 0.75:
        return "MEDIUM", "LOW_CONFIDENCE"
    if attempts > 1:
        return "MEDIUM", "REPEATED_ATTEMPTS"
    return "LOW", "CHALLENGE_PASSED"


async def create_challenge(
    db: AsyncSession,
    user_session_id: uuid.UUID,
    request_data: ChallengeCreateRequest,
    participant_id: uuid.UUID | None = None,
    max_attempts: int = 2,
    request_id: str = "unknown",
) -> ChallengeCreateResponse:
    """
    Issue a new challenge record and return ChallengeCreateResponse with raw nonce.
    """
    is_active, retry_after, expires_at_iso = await check_cooldown_status(
        db=db,
        session_id=user_session_id,
        participant_id=participant_id,
    )
    if is_active:
        cooldown_metric = MetricEvent(
            campaign_id=request_data.campaign_id,
            metric_name="cooldown_trigger",
            metric_value=1.0,
            client_class=None,
            tags={
                "retry_after_seconds": retry_after,
                "cooldown_expires_at": expires_at_iso,
            },
        )
        db.add(cooldown_metric)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": {
                    "code": "COOLDOWN_ACTIVE",
                    "message": "Too many failed attempts. Cooldown active.",
                    "request_id": request_id,
                    "details": {
                        "retry_after_seconds": retry_after,
                        "cooldown_expires_at": expires_at_iso,
                    },
                }
            },
        )

    raw_nonce = generate_nonce()
    nonce_h = hash_nonce(raw_nonce)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=5)

    type_val = str(request_data.type.value if isinstance(request_data.type, Enum) else request_data.type).upper()
    is_fallback = False

    if type_val == "MEDIAPIPE" and request_data.fallback_requested:
        type_val = "VISUAL"
        is_fallback = True

    instructions = ChallengeAdapter.get_instructions(type_val)

    if type_val == "MEDIAPIPE":
        gesture = instructions.get("gesture", "THUMBS_UP")
        hand = instructions.get("hand", "LEFT")
        implementation_version = f"mediapipe-v1:{gesture}:{hand}"
    else:
        version_map = {
            "TURNSTILE": "turnstile-v1",
            "MOCK": "mock-v1",
            "VISUAL": "visual-v1",
        }
        implementation_version = version_map.get(type_val, "unknown-v1")

    challenge = Challenge(
        campaign_id=request_data.campaign_id,
        session_id=user_session_id,
        participant_id=participant_id,
        type=type_val,
        nonce_hash=nonce_h,
        status="PENDING",
        expires_at=expires_at,
        attempt_count=0,
        max_attempts=max_attempts,
        implementation_version=implementation_version,
    )
    db.add(challenge)
    await db.commit()

    audit_event = AuditEvent(
        campaign_id=request_data.campaign_id,
        participant_id=participant_id,
        session_id=user_session_id,
        actor_type="USER",
        actor_id=participant_id,
        event_type="CHALLENGE_CREATED",
        request_id=request_id,
        metadata_json={
            "challenge_id": str(challenge.id),
            "type": type_val,
            "operation": request_data.operation,
            "instructions": instructions,
            "is_fallback": is_fallback,
            "accessibility_reason": request_data.accessibility_reason,
        },
    )
    db.add(audit_event)

    metric_created = MetricEvent(
        campaign_id=request_data.campaign_id,
        metric_name="challenge_created",
        metric_value=1.0,
        client_class=type_val,
        tags={
            "challenge_id": str(challenge.id),
            "challenge_type": type_val,
            "operation": request_data.operation,
            "is_fallback": is_fallback,
        },
    )
    db.add(metric_created)

    if is_fallback:
        metric_fallback = MetricEvent(
            campaign_id=request_data.campaign_id,
            metric_name="challenge_fallback_triggered",
            metric_value=1.0,
            client_class="MEDIAPIPE",
            tags={
                "original_type": "MEDIAPIPE",
                "fallback_type": "VISUAL",
                "accessibility_reason": request_data.accessibility_reason,
            },
        )
        db.add(metric_fallback)

    await db.commit()

    return ChallengeCreateResponse(
        challenge_id=challenge.id,
        type=ChallengeType(type_val),
        status=ChallengeStatus.PENDING,
        nonce=raw_nonce,
        expires_at=challenge.expires_at,
        max_attempts=challenge.max_attempts,
        implementation_version=challenge.implementation_version,
        instructions=instructions,
    )


async def verify_challenge(
    db: AsyncSession,
    user_session_id: uuid.UUID,
    challenge_id: uuid.UUID,
    request_data: ChallengeVerifyRequest,
    idempotency_key: str | None = None,
    request_id: str = "unknown",
) -> ChallengeVerifyResponse:
    """
    Validate challenge response against nonce, expiry, session, adapter rules, and telemetry risk analysis.
    """
    is_active, retry_after, expires_at_iso = await check_cooldown_status(
        db=db,
        session_id=user_session_id,
    )
    if is_active:
        cooldown_metric = MetricEvent(
            campaign_id=None,
            metric_name="cooldown_trigger",
            metric_value=1.0,
            client_class=None,
            tags={
                "retry_after_seconds": retry_after,
                "cooldown_expires_at": expires_at_iso,
            },
        )
        db.add(cooldown_metric)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": {
                    "code": "COOLDOWN_ACTIVE",
                    "message": "Too many failed attempts. Cooldown active.",
                    "request_id": request_id,
                    "details": {
                        "retry_after_seconds": retry_after,
                        "cooldown_expires_at": expires_at_iso,
                    },
                }
            },
        )

    stmt = (
        select(Challenge)
        .where(Challenge.id == challenge_id)
        .with_for_update()
    )
    result = await db.execute(stmt)
    challenge = result.scalar_one_or_none()

    if challenge is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "CHALLENGE_NOT_FOUND",
                    "message": f"Challenge {challenge_id} not found",
                    "request_id": request_id,
                    "details": {},
                }
            },
        )

    if challenge.session_id != user_session_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "CHALLENGE_SESSION_MISMATCH",
                    "message": "Challenge session ID does not match request identity",
                    "request_id": request_id,
                    "details": {},
                }
            },
        )

    if challenge.status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "CHALLENGE_REPLAYED",
                    "message": f"Challenge is already in {challenge.status} state",
                    "request_id": request_id,
                    "details": {"status": challenge.status},
                }
            },
        )

    if hash_nonce(request_data.nonce) != challenge.nonce_hash:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "CHALLENGE_NONCE_MISMATCH",
                    "message": "Provided nonce does not match challenge record",
                    "request_id": request_id,
                    "details": {},
                }
            },
        )

    now = datetime.now(timezone.utc)
    exp_at = challenge.expires_at
    if exp_at.tzinfo is None:
        exp_at = exp_at.replace(tzinfo=timezone.utc)

    if exp_at <= now:
        challenge.status = "EXPIRED"
        metric_abandoned = MetricEvent(
            campaign_id=challenge.campaign_id,
            metric_name="challenge_abandoned",
            metric_value=1.0,
            client_class=challenge.type,
            tags={"challenge_id": str(challenge.id)},
        )
        db.add(metric_abandoned)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={
                "error": {
                    "code": "CHALLENGE_EXPIRED",
                    "message": "Challenge has expired",
                    "request_id": request_id,
                    "details": {"expires_at": exp_at.isoformat()},
                }
            },
        )

    # Increment attempt count
    challenge.attempt_count += 1

    if challenge.attempt_count > challenge.max_attempts:
        challenge.status = "FAILED"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": {
                    "code": "CHALLENGE_ATTEMPT_LIMIT",
                    "message": "Maximum verification attempts exceeded",
                    "request_id": request_id,
                    "details": {"max_attempts": challenge.max_attempts},
                }
            },
        )

    # Reconstruct issued instructions for MediaPipe
    instructions = {}
    if challenge.type == "MEDIAPIPE":
        parts = challenge.implementation_version.split(":")
        if len(parts) >= 3:
            instructions = {
                "gesture": parts[1],
                "hand": parts[2],
            }

    # Validate result via ChallengeAdapter (async for Turnstile API verification support)
    is_passed, reason_code = await ChallengeAdapter.validate_result_async(
        challenge_type=request_data.type,
        result=request_data.result,
        confidence=request_data.confidence,
        turnstile_token=request_data.turnstile_token,
        instructions=instructions,
        verify_request=request_data,
    )

    if is_passed:
        challenge.status = "PASSED"
        challenge.consumed_at = now
        risk_level, reason_code = evaluate_challenge_risk(
            duration_ms=request_data.duration_ms,
            confidence=request_data.confidence,
            attempts=challenge.attempt_count,
            gesture_type=challenge.type,
        )
    else:
        challenge.status = "FAILED"
        risk_level = "MEDIUM"

    audit_event = AuditEvent(
        campaign_id=challenge.campaign_id,
        participant_id=challenge.participant_id,
        session_id=challenge.session_id,
        actor_type="USER",
        actor_id=challenge.participant_id,
        event_type="CHALLENGE_VERIFIED" if is_passed else "CHALLENGE_FAILED",
        reason_code=reason_code,
        request_id=request_id,
        metadata_json={
            "challenge_id": str(challenge.id),
            "type": str(request_data.type),
            "result": request_data.result,
            "confidence": request_data.confidence,
            "duration_ms": request_data.duration_ms,
            "attempt_count": challenge.attempt_count,
            "idempotency_key": idempotency_key,
            "reason_code": reason_code,
            "risk_level": risk_level,
        },
    )
    db.add(audit_event)

    metric_verified = MetricEvent(
        campaign_id=challenge.campaign_id,
        metric_name="challenge_verified",
        metric_value=float(request_data.duration_ms),
        client_class=challenge.type,
        tags={
            "challenge_id": str(challenge.id),
            "challenge_type": challenge.type,
            "status": challenge.status,
            "confidence": request_data.confidence,
            "duration_ms": request_data.duration_ms,
            "risk_level": risk_level,
            "reason_code": reason_code,
        },
    )
    db.add(metric_verified)

    await db.commit()

    verified_until = now + timedelta(minutes=5)

    return ChallengeVerifyResponse(
        challenge_id=challenge.id,
        status=ChallengeStatus(challenge.status),
        risk_level=risk_level,
        reason_code=reason_code,
        verified_until=verified_until,
    )


async def get_challenge_metrics_summary(
    db: AsyncSession,
    campaign_id: uuid.UUID | None = None,
) -> ChallengeMetricsSummaryResponse:
    """
    Aggregates challenge performance metrics, pass rates, latency stats, and risk distributions.
    """
    now = datetime.now(timezone.utc)

    # Fetch challenges
    stmt_ch = select(Challenge)
    if campaign_id is not None:
        stmt_ch = stmt_ch.where(Challenge.campaign_id == campaign_id)
    res_ch = await db.execute(stmt_ch)
    challenges = list(res_ch.scalars().all())

    # Fetch metric events
    stmt_me = select(MetricEvent)
    if campaign_id is not None:
        stmt_me = stmt_me.where(MetricEvent.campaign_id == campaign_id)
    res_me = await db.execute(stmt_me)
    metric_events = list(res_me.scalars().all())

    total_challenges_issued = len(challenges)
    total_passed = sum(1 for c in challenges if c.status == "PASSED")
    total_failed = sum(1 for c in challenges if c.status == "FAILED")
    
    total_abandoned = sum(
        1 for c in challenges
        if c.status == "EXPIRED" or (
            c.status == "PENDING" and (
                c.expires_at.replace(tzinfo=timezone.utc) if c.expires_at.tzinfo is None else c.expires_at
            ) <= now
        )
    )

    pass_rate_percentage = round((total_passed / total_challenges_issued * 100), 2) if total_challenges_issued > 0 else 0.0

    verified_metrics = [m for m in metric_events if m.metric_name == "challenge_verified"]
    durations = [float(m.metric_value) for m in verified_metrics if m.metric_value is not None]

    if durations:
        avg_duration_ms = round(sum(durations) / len(durations), 2)
        sorted_durations = sorted(durations)
        p90_idx = int(len(sorted_durations) * 0.9)
        p90_idx = min(p90_idx, len(sorted_durations) - 1)
        p90_duration_ms = round(sorted_durations[p90_idx], 2)
    else:
        avg_duration_ms = 0.0
        p90_duration_ms = 0.0

    fallback_count = sum(1 for m in metric_events if m.metric_name == "challenge_fallback_triggered")
    cooldown_triggers_count = sum(1 for m in metric_events if m.metric_name == "cooldown_trigger")

    by_risk_level_breakdown = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    for m in verified_metrics:
        r_level = (m.tags or {}).get("risk_level")
        if r_level in by_risk_level_breakdown:
            by_risk_level_breakdown[r_level] += 1

    known_types = ["MEDIAPIPE", "TURNSTILE", "VISUAL", "MOCK"]
    by_type_breakdown: dict[str, ChallengeTypeBreakdown] = {}

    for c_type in known_types:
        type_challenges = [c for c in challenges if c.type == c_type]
        t_total = len(type_challenges)
        t_passed = sum(1 for c in type_challenges if c.status == "PASSED")
        t_failed = sum(1 for c in type_challenges if c.status == "FAILED")
        t_abandoned = sum(
            1 for c in type_challenges
            if c.status == "EXPIRED" or (
                c.status == "PENDING" and (
                    c.expires_at.replace(tzinfo=timezone.utc) if c.expires_at.tzinfo is None else c.expires_at
                ) <= now
            )
        )
        t_pass_rate = round((t_passed / t_total * 100), 2) if t_total > 0 else 0.0

        type_verified_metrics = [m for m in verified_metrics if m.client_class == c_type]
        type_durations = [float(m.metric_value) for m in type_verified_metrics if m.metric_value is not None]
        t_avg_dur = round(sum(type_durations) / len(type_durations), 2) if type_durations else 0.0

        by_type_breakdown[c_type] = ChallengeTypeBreakdown(
            total=t_total,
            passed=t_passed,
            failed=t_failed,
            abandoned=t_abandoned,
            pass_rate_percentage=t_pass_rate,
            avg_duration_ms=t_avg_dur,
        )

    return ChallengeMetricsSummaryResponse(
        campaign_id=campaign_id,
        total_challenges_issued=total_challenges_issued,
        total_passed=total_passed,
        total_failed=total_failed,
        total_abandoned=total_abandoned,
        pass_rate_percentage=pass_rate_percentage,
        avg_duration_ms=avg_duration_ms,
        p90_duration_ms=p90_duration_ms,
        fallback_count=fallback_count,
        cooldown_triggers_count=cooldown_triggers_count,
        by_type_breakdown=by_type_breakdown,
        by_risk_level_breakdown=by_risk_level_breakdown,
        generated_at=now,
    )

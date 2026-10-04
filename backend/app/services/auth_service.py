"""
Authentication service orchestrating JWT identity resolution and JIT provisioning.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import lru_settings
from app.models.participant import Participant, Profile
from app.security.hashing import hash_email
from app.security.jwt import decode_supabase_jwt, extract_email, extract_subject

logger = logging.getLogger(__name__)


async def get_or_create_profile(
    db: AsyncSession,
    subject_id: uuid.UUID,
    email: str | None,
) -> Profile:
    """
    Fetch an existing user profile by Supabase subject ID, or provision one via JIT.
    """
    stmt = select(Profile).where(Profile.id == subject_id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if profile is not None:
        return profile

    # JIT provision new profile
    logger.info("JIT provisioning profile for subject %s", subject_id)
    new_profile = Profile(
        id=subject_id,
        role="USER",
        email_verified=bool(email),
    )

    try:
        async with db.begin_nested():
            db.add(new_profile)
            await db.flush()
        return new_profile
    except IntegrityError:
        # Concurrent request already inserted this profile
        logger.info("Profile %s inserted concurrently; fetching committed row", subject_id)
        result = await db.execute(select(Profile).where(Profile.id == subject_id))
        return result.scalar_one()


async def get_or_create_participant(
    db: AsyncSession,
    profile: Profile,
    email: str | None,
) -> Participant:
    """
    Fetch an existing participant record linked to the profile, or provision one via JIT.
    """
    settings = lru_settings()

    stmt = select(Participant).where(Participant.account_id == profile.id)
    result = await db.execute(stmt)
    participant = result.scalar_one_or_none()

    if participant is not None:
        return participant

    if not settings.JIT_PROVISION_PARTICIPANT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PARTICIPANT_NOT_FOUND",
                    "message": "Participant profile not found and JIT provisioning is disabled",
                    "request_id": "unknown",
                    "details": None,
                }
            },
        )

    logger.info("JIT provisioning participant for profile %s", profile.id)
    email_hash_val = hash_email(email) if email else ""

    new_participant = Participant(
        account_id=profile.id,
        email_hash=email_hash_val,
        verification_status="PENDING",
        risk_level="LOW",
    )

    try:
        async with db.begin_nested():
            db.add(new_participant)
            await db.flush()
        return new_participant
    except IntegrityError:
        # Concurrent request already inserted this participant
        logger.info("Participant for %s inserted concurrently; fetching committed row", profile.id)
        result = await db.execute(select(Participant).where(Participant.account_id == profile.id))
        return result.scalar_one()


async def resolve_identity(
    db: AsyncSession,
    token: str,
) -> tuple[Profile, Participant]:
    """
    Verify the Supabase JWT and resolve or provision the (Profile, Participant) identity.
    """
    payload = decode_supabase_jwt(token)
    subject_id = extract_subject(payload)
    email = extract_email(payload)

    profile = await get_or_create_profile(db, subject_id, email)
    participant = await get_or_create_participant(db, profile, email)

    await db.commit()
    return profile, participant

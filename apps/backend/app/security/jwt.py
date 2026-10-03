"""
Supabase JWT verification and claim extraction primitives.
"""

from __future__ import annotations

import logging
import uuid

import jwt

from app.config import lru_settings

logger = logging.getLogger(__name__)


class InvalidTokenError(Exception):
    """Raised when a JWT fails cryptographic validation or claim assertions."""

    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(message or code)
        self.code = code


def decode_supabase_jwt(token: str) -> dict:
    """
    Validate and decode a Supabase-issued HS256 JWT.

    Verifies signature, expiration, audience, and optional issuer.
    Raises InvalidTokenError with a standardized code on any failure.
    """
    settings = lru_settings()

    decode_kwargs: dict = {
        "algorithms": ["HS256"],
        "audience": settings.SUPABASE_JWT_AUDIENCE,
    }

    if settings.SUPABASE_JWT_ISSUER:
        decode_kwargs["issuer"] = settings.SUPABASE_JWT_ISSUER

    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            **decode_kwargs,
        )
        return payload
    except jwt.ExpiredSignatureError as exc:
        raise InvalidTokenError("TOKEN_EXPIRED", "Token signature has expired") from exc
    except jwt.InvalidAudienceError as exc:
        raise InvalidTokenError("INVALID_AUDIENCE", "Token audience is invalid") from exc
    except jwt.InvalidIssuerError as exc:
        raise InvalidTokenError("INVALID_ISSUER", "Token issuer is invalid") from exc
    except jwt.InvalidTokenError as exc:
        raise InvalidTokenError("INVALID_TOKEN", "Malformed or invalid token") from exc
    except Exception as exc:
        logger.warning("Unexpected JWT decode failure: %s", exc)
        raise InvalidTokenError("TOKEN_DECODE_FAILED", "Failed to decode token") from exc


def extract_subject(payload: dict) -> uuid.UUID:
    """
    Extract and validate the Supabase user ID ('sub') as a UUID.
    """
    sub = payload.get("sub")
    if not sub:
        raise InvalidTokenError("INVALID_SUBJECT", "Missing sub claim in token")

    try:
        return uuid.UUID(str(sub))
    except (ValueError, TypeError) as exc:
        raise InvalidTokenError("INVALID_SUBJECT", "Invalid sub claim UUID") from exc


def extract_email(payload: dict) -> str | None:
    """
    Extract the email claim if present.
    """
    return payload.get("email")

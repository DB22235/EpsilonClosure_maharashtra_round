"""
Supabase JWT verification and claim extraction primitives.
"""

from __future__ import annotations

import logging
import uuid

import jwt
from jwt import PyJWKClient

from app.config import lru_settings

logger = logging.getLogger(__name__)

_jwks_client: PyJWKClient | None = None


def get_jwks_client() -> PyJWKClient:
    """Return a cached PyJWKClient pointing to the Supabase JWKS endpoint."""
    global _jwks_client
    if _jwks_client is None:
        settings = lru_settings()
        jwks_url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
        _jwks_client = PyJWKClient(
            jwks_url,
            cache_keys=True,
            max_cached_keys=16,
            cache_jwk_set=True,
            lifespan=3600,
        )
    return _jwks_client


class InvalidTokenError(Exception):
    """Raised when a JWT fails cryptographic validation or claim assertions."""

    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(message or code)
        self.code = code


def decode_supabase_jwt(token: str) -> dict:
    """
    Validate and decode a Supabase-issued JWT.

    Supports both:
      - Asymmetric signing (ES256, RS256) via Supabase JWKS public keys
      - Symmetric signing (HS256) via SUPABASE_JWT_SECRET for test/dev tokens

    Verifies signature, expiration, audience, and optional issuer.
    Raises InvalidTokenError with a standardized code on any failure.
    """
    settings = lru_settings()

    try:
        unverified_header = jwt.get_unverified_header(token)
    except Exception as exc:
        raise InvalidTokenError("INVALID_TOKEN", "Malformed or invalid token") from exc

    alg = unverified_header.get("alg", "HS256")

    decode_kwargs: dict = {
        "audience": settings.SUPABASE_JWT_AUDIENCE,
    }

    if settings.SUPABASE_JWT_ISSUER:
        decode_kwargs["issuer"] = settings.SUPABASE_JWT_ISSUER

    try:
        if alg in ("ES256", "RS256"):
            jwks_client = get_jwks_client()
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            verification_key = signing_key.key
            allowed_algorithms = [alg]
        else:
            verification_key = settings.SUPABASE_JWT_SECRET or "fair-drop-default-test-jwt-secret-key"
            allowed_algorithms = ["HS256"]

        payload = jwt.decode(
            token,
            verification_key,
            algorithms=allowed_algorithms,
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

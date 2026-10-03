"""
Hashing utilities for privacy-preserving sensitive identifiers.
"""

from __future__ import annotations

import hashlib
import re

from app.config import lru_settings


def hash_email(email: str) -> str:
    """
    Produce a deterministic peppered SHA-256 hash of a normalized email address.
    """
    settings = lru_settings()
    normalized = email.strip().lower()
    salted = f"{normalized}:{settings.EMAIL_HASH_PEPPER}"
    return hashlib.sha256(salted.encode("utf-8")).hexdigest()


def hash_phone(phone: str) -> str:
    """
    Produce a deterministic peppered SHA-256 hash of a normalized phone number.
    Removes whitespace and dashes before hashing.
    """
    settings = lru_settings()
    normalized = re.sub(r"[\s\-\(\)\.]", "", phone.strip())
    salted = f"{normalized}:{settings.EMAIL_HASH_PEPPER}"
    return hashlib.sha256(salted.encode("utf-8")).hexdigest()


def hash_generic(value: str) -> str:
    """
    Produce a peppered SHA-256 hash for arbitrary string inputs (e.g. IPs, user agents).
    """
    settings = lru_settings()
    salted = f"{value.strip()}:{settings.EMAIL_HASH_PEPPER}"
    return hashlib.sha256(salted.encode("utf-8")).hexdigest()

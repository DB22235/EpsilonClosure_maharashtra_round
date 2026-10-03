"""
Application configuration.

Loaded once at startup via lru_settings(). All downstream modules
import lru_settings and call it — they never instantiate Settings directly.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",          # don't crash on unknown env vars
    )

    # ── Application ──────────────────────────────────────────────────────────
    APP_ENV: Literal["development", "demo", "production"] = "development"
    APP_NAME: str = "fair-drop"
    API_V1_PREFIX: str = "/api/v1"

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/fairdrop"

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = ""

    # ── Supabase ──────────────────────────────────────────────────────────────
    SUPABASE_URL: str = "https://gjbijluacysjudkvpivd.supabase.co"
    SUPABASE_JWT_SECRET: str = ""
    SUPABASE_JWT_AUDIENCE: str = "authenticated"
    SUPABASE_JWT_ISSUER: str = ""
    EMAIL_HASH_PEPPER: str = "fair-drop-dev-pepper-change-me"
    REQUEST_ID_HEADER: str = "X-Request-ID"
    JIT_PROVISION_PARTICIPANT: bool = True

    # ── Signing keys ──────────────────────────────────────────────────────────
    SIGNING_KEY_ID: str = "fair-drop-dev-key-1"
    SIGNING_PRIVATE_KEY: str = ""

    # ── Server timers (seconds) ───────────────────────────────────────────────
    IDLE_SESSION_SECONDS: int = 120
    ABSOLUTE_REDEMPTION_SECONDS: int = 300
    SEAT_HOLD_SECONDS: int = 120
    COOLDOWN_SECONDS: int = 300
    MAX_CHALLENGE_ATTEMPTS: int = 2

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: object) -> list[str]:
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                return json.loads(v)
            # comma-separated fallback
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        raise ValueError(f"CORS_ORIGINS must be a list or JSON string, got {type(v)}")


@lru_cache(maxsize=1)
def lru_settings() -> Settings:
    """Return the singleton Settings instance. Import this, never Settings()."""
    return Settings()

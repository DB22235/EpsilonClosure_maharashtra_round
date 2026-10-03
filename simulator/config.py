"""Central configuration for the Fair Drop live adversarial simulator.

Reads from a .env file in the simulator/ directory. All settings have
type-safe defaults via pydantic-settings.
"""

from pathlib import Path
from pydantic_settings import BaseSettings

# Resolve the .env file relative to this config.py file (inside simulator/)
_ENV_FILE = Path(__file__).parent / ".env"


class Settings(BaseSettings):
    """Runtime configuration loaded from environment / .env file."""

    # --- Supabase (same project as Dhruv's backend) ---
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""

    # --- Backend API ---
    API_BASE_URL: str = "http://localhost:8000/api/v1"

    # --- Test-user seed pool ---
    TEST_USER_PREFIX: str = "simtest"
    TEST_USER_PASSWORD: str = "SimTestPass123!"
    TEST_USER_COUNT: int = 100

    # --- Admin account (for campaign lifecycle calls) ---
    ADMIN_EMAIL: str = "admin@fairdrop.local"
    ADMIN_PASSWORD: str = "AdminPass123!"

    class Config:
        env_file = str(_ENV_FILE)
        env_file_encoding = "utf-8"
        # Also allow environment variables to override
        case_sensitive = False


settings = Settings()

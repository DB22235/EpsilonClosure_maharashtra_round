"""Central configuration for the Fair Drop live adversarial simulator.

Reads from a .env file in the simulator/ directory. All settings have
type-safe defaults via pydantic-settings.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Runtime configuration loaded from environment / .env file."""

    # --- Supabase (same project as Dhruv's backend) ---
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str

    # --- Backend API ---
    API_BASE_URL: str = "http://localhost:8000/api/v1"

    # --- Test-user seed pool ---
    TEST_USER_PREFIX: str = "simtest"
    TEST_USER_PASSWORD: str = "SimTestPass123!"
    TEST_USER_COUNT: int = 100

    # --- Admin account (for campaign lifecycle calls) ---
    ADMIN_EMAIL: str
    ADMIN_PASSWORD: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

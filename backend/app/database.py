"""
Database engine, session management, and lifecycle hooks.
"""

from __future__ import annotations

import logging
import os
import sys
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import lru_settings

logger = logging.getLogger(__name__)

# Engine creation - reloading configuration
settings = lru_settings()
logger.info("Initializing database engine with URL host: %s", settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'localhost')

engine_kwargs: dict = {
    "echo": (settings.APP_ENV == "development"),
}
if "pytest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
    from sqlalchemy.pool import NullPool
    engine_kwargs["poolclass"] = NullPool
else:
    engine_kwargs.update({
        "pool_size": 20,
        "max_overflow": 10,
        "pool_pre_ping": True,
    })

engine = create_async_engine(
    settings.DATABASE_URL,
    **engine_kwargs,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an async database session with automatic rollback on exception and cleanup.
    Suitable for use with FastAPI Depends().
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Create all tables defined on Base.metadata.
    Used for development table creation; production uses Alembic migrations.
    """
    from app.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """
    Dispose of the engine connection pool.
    """
    await engine.dispose()

"""
Database engine, session factory, and FastAPI dependency.

Uses SQLAlchemy 2.x async engine backed by asyncpg.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

# ---------------------------------------------------------------------------
# Declarative base – shared by all models
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all Atlas AI models."""

    pass


# ---------------------------------------------------------------------------
# Engine & session factory (module-level singletons)
# ---------------------------------------------------------------------------
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _build_engine() -> AsyncEngine:
    return create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DATABASE_ECHO,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_pre_ping=True,
        pool_recycle=3600,
    )


async def init_db() -> None:
    """Initialise the async engine and create tables if needed."""
    global _engine, _session_factory

    _engine = _build_engine()
    _session_factory = async_sessionmaker(
        _engine,
        expire_on_commit=False,
        autoflush=False,
    )

    # Create tables (Alembic handles migrations in prod; this covers dev/test)
    async with _engine.begin() as conn:
        from app.models import AgentRun, Incident, LearningCase  # noqa: F401

        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database initialised", url=settings.DATABASE_URL.split("@")[-1])


async def close_db() -> None:
    """Dispose the engine connection pool."""
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None
        logger.info("Database connection pool closed")


async def check_db_health() -> bool:
    """Return True if the database is reachable."""
    try:
        if _engine is None:
            return False
        async with _engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Database health check failed", error=str(exc))
        return False


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session, committing on success."""
    if _session_factory is None:
        raise RuntimeError("Database not initialised. Call init_db() first.")

    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

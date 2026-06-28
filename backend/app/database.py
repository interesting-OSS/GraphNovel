"""Async database engine and session management with monitoring.

Features:
  - DatabaseEngine singleton with asyncio.Lock
  - SessionTracker for leak detection
  - Three-stage rollback (GeneratorExit → Exception → finally)
  - Configurable pool settings from Settings
"""
import asyncio
import threading
import time
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker, AsyncEngine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)


# ── Session Tracker ─────────────────────────────────────────────────────────

class SessionTracker:
    """Thread-safe session lifecycle tracker for leak detection."""

    _stats: dict[str, int] = {
        "created": 0, "closed": 0, "active": 0,
        "errors": 0, "generator_exits": 0,
    }
    _lock = threading.Lock()

    @classmethod
    def inc(cls, key: str) -> None:
        with cls._lock:
            cls._stats[key] = cls._stats.get(key, 0) + 1
            if key == "created":
                cls._stats["active"] = cls._stats.get("active", 0) + 1
            elif key == "closed":
                cls._stats["active"] = max(0, cls._stats.get("active", 0) - 1)

    @classmethod
    def snapshot(cls) -> dict:
        with cls._lock:
            return dict(cls._stats)


# ── Database Engine ─────────────────────────────────────────────────────────

class DatabaseEngine:
    """Singleton async engine manager with double-checked locking."""

    _engine: AsyncEngine | None = None
    _lock = asyncio.Lock()

    @classmethod
    async def get_engine(cls) -> AsyncEngine:
        if cls._engine is None:
            async with cls._lock:
                if cls._engine is None:
                    db = settings.database
                    cls._engine = create_async_engine(
                        db.database_url or settings.database_url,  # fallback to alias
                        echo=settings.debug,
                        pool_size=db.db_pool_size,
                        max_overflow=db.db_max_overflow,
                        pool_recycle=db.db_pool_recycle,
                        pool_pre_ping=db.db_pool_pre_ping,
                        pool_timeout=db.db_pool_timeout,
                    )
                    logger.info(
                        "Database engine created: pool_size=%d max_overflow=%d recycle=%d",
                        db.db_pool_size, db.db_max_overflow, db.db_pool_recycle,
                    )
        return cls._engine

    @classmethod
    async def close(cls) -> None:
        if cls._engine:
            await cls._engine.dispose()
            cls._engine = None
            logger.info("Database engine disposed")


# ── ORM Base ────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all ORM models."""
    pass


# ── Session Factory ─────────────────────────────────────────────────────────

_async_session_factory: async_sessionmaker | None = None


async def _get_session_factory() -> async_sessionmaker:
    global _async_session_factory
    if _async_session_factory is None:
        engine = await DatabaseEngine.get_engine()
        _async_session_factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False,
        )
    return _async_session_factory


# Backward compatibility: some code imports async_session_factory directly.
# This proxy lazily initializes the real factory on first use.
class _LazySessionFactory:
    """Callable proxy that lazily creates sessions from the async engine."""

    def __call__(self, **kwargs):
        # async_sessionmaker.__call__ is sync — returns an AsyncSession context manager
        if _async_session_factory is None:
            raise RuntimeError(
                "Database engine not initialized. Call 'await _init_factory()' first, "
                "or use 'from app.database import get_db' instead."
            )
        return _async_session_factory(**kwargs)


async_session_factory = _LazySessionFactory()


async def _init_factory():
    """Ensure the async session factory is initialized. Call once at startup."""
    await _get_session_factory()


# ── Session Dependency ─────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields a database session with three-stage rollback.

    Rollback stages:
      1. GeneratorExit (SSE disconnect) → rollback, re-raise
      2. Exception → rollback, re-raise
      3. finally → ensure session is closed
    """
    factory = await _get_session_factory()
    session = factory()
    SessionTracker.inc("created")

    try:
        yield session
        await session.commit()
    except GeneratorExit:
        SessionTracker.inc("generator_exits")
        await session.rollback()
        raise
    except Exception:
        SessionTracker.inc("errors")
        await session.rollback()
        raise
    finally:
        SessionTracker.inc("closed")
        await session.close()


# ── Health Check ────────────────────────────────────────────────────────────

async def check_database_health() -> dict:
    """Check database connectivity and pool status."""
    result = {"status": "healthy", "checks": {}}
    try:
        engine = await DatabaseEngine.get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        result["checks"]["database"] = "ok"
    except Exception as e:
        result["checks"]["database"] = f"error: {str(e)[:100]}"
        result["status"] = "degraded"

    result["pool"] = SessionTracker.snapshot()
    return result

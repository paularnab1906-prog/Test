"""Async SQLAlchemy engine / session setup."""
from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


_settings = get_settings()
# For SQLite (local-dev default), allow a busy timeout so concurrent inline-job
# writes and request reads don't trip "database is locked".
_connect_args = {"timeout": 30} if _settings.database_url.startswith("sqlite") else {}
engine = create_async_engine(
    _settings.database_url, echo=_settings.is_dev, future=True, connect_args=_connect_args
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields a request-scoped session."""
    async with SessionLocal() as session:
        yield session


async def init_models() -> None:
    """Create tables from metadata. Dev convenience — use Alembic in prod."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

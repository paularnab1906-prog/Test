"""Arq enqueue pool used by the API to dispatch jobs to workers."""
from __future__ import annotations

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.config import get_settings

_pool: ArqRedis | None = None


async def get_pool() -> ArqRedis:
    global _pool
    if _pool is None:
        _pool = await create_pool(RedisSettings.from_dsn(get_settings().redis_url))
    return _pool


async def enqueue_generation(job_id: str) -> None:
    pool = await get_pool()
    await pool.enqueue_job("run_generation", job_id)

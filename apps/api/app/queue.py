"""Job dispatch. Two runners, chosen by `job_runner`:

  * inline — run the job in a background asyncio task in this process (no Redis,
             no separate worker). Ideal for local testing.
  * arq    — enqueue to the Redis-backed Arq worker for production.
"""
from __future__ import annotations

import asyncio
import logging

from app.config import get_settings

logger = logging.getLogger("lumina.queue")

_pool = None  # lazily-created Arq pool (arq mode only)


async def enqueue_generation(job_id: str) -> None:
    if get_settings().job_runner == "inline":
        asyncio.create_task(_run_inline(job_id))
        return

    from arq import create_pool
    from arq.connections import RedisSettings

    global _pool
    if _pool is None:
        _pool = await create_pool(RedisSettings.from_dsn(get_settings().redis_url))
    await _pool.enqueue_job("run_generation", job_id)


async def _run_inline(job_id: str) -> None:
    from app.worker import run_generation

    try:
        await run_generation({}, job_id)
    except Exception:  # noqa: BLE001 — never crash the loop; job row carries the error
        logger.exception("inline generation failed for job %s", job_id)

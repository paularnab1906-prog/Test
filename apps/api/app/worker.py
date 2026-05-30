"""Arq worker: consumes generation jobs, calls the provider, stores results.

Run with:  arq app.worker.WorkerSettings
"""
from __future__ import annotations

import asyncio

from app.config import get_settings
from app.db import SessionLocal
from app.models import Asset, Job, JobStatus
from app.providers import get_provider
from app.providers.base import NormalizedRequest, ProviderState
from app.storage import ingest_url

_POLL_INTERVAL_S = 2
_POLL_TIMEOUT_S = 600


async def run_generation(ctx: dict, job_id: str) -> None:
    """Main job handler. Idempotent enough for at-least-once delivery."""
    async with SessionLocal() as session:
        job = await session.get(Job, job_id)
        if job is None or job.status not in (JobStatus.queued, JobStatus.running):
            return

        job.status = JobStatus.running
        await session.commit()

        provider = get_provider(job.provider)
        req = NormalizedRequest(**job.normalized_request)

        try:
            ref = await provider.submit(req)
            job.provider_job_ref = ref
            await session.commit()

            status = await _await_result(provider, ref)

            if status.state is ProviderState.succeeded:
                for i, result in enumerate(status.results):
                    key = f"{job.user_id}/{job.id}/{i}.{_ext(result.kind)}"
                    cdn_url = await ingest_url(result.url, key, _content_type(result.kind))
                    session.add(
                        Asset(
                            job_id=job.id,
                            user_id=job.user_id,
                            kind=result.kind,
                            storage_key=key,
                            cdn_url=cdn_url,
                            thumbnail_url=result.thumbnail_url,
                        )
                    )
                job.status = JobStatus.succeeded
            else:
                job.status = JobStatus.failed
                job.error_code = status.error or "provider_failed"
        except Exception as exc:  # noqa: BLE001 — surface a typed error to the UI
            job.status = JobStatus.failed
            job.error_code = f"worker_error: {exc}"

        from sqlalchemy import func, select

        job.finished_at = (await session.execute(select(func.now()))).scalar()
        await session.commit()
        # NOTE: credit capture/refund settlement hooks here in Phase 3.


async def _await_result(provider, ref: str):
    waited = 0
    while waited < _POLL_TIMEOUT_S:
        status = await provider.poll(ref)
        if status.state is not ProviderState.running:
            return status
        await asyncio.sleep(_POLL_INTERVAL_S)
        waited += _POLL_INTERVAL_S
    from app.providers.base import ProviderStatus

    return ProviderStatus(state=ProviderState.failed, error="timeout")


def _ext(kind: str) -> str:
    return {"video": "mp4", "image": "png", "audio": "mp3"}.get(kind, "bin")


def _content_type(kind: str) -> str:
    return {"video": "video/mp4", "image": "image/png", "audio": "audio/mpeg"}.get(
        kind, "application/octet-stream"
    )


class WorkerSettings:
    functions = [run_generation]

    @staticmethod
    def redis_settings():
        from arq.connections import RedisSettings

        return RedisSettings.from_dsn(get_settings().redis_url)

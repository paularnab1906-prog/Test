"""Arq worker: consumes generation jobs, calls the provider(s), stores results.

Implements primary -> fallback failover across providers using the preset's
target chain (Architecture sections 3.4 & 7).

Run with:  arq app.worker.WorkerSettings
"""
from __future__ import annotations

import asyncio

from sqlalchemy import func, select

from app import presets
from app.config import get_settings
from app.db import SessionLocal
from app.models import Asset, Job, JobStatus
from app.providers import get_provider
from app.providers.base import NormalizedRequest, ProviderState, ProviderStatus

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

        req = NormalizedRequest(**job.normalized_request)
        status, used = await _run_with_failover(session, job, req)

        if status is not None and status.state is ProviderState.succeeded:
            for i, result in enumerate(status.results):
                key = f"{job.user_id}/{job.id}/{i}.{_ext(result.kind)}"
                from app.storage import ingest_url

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
            job.error_code = (status.error if status else None) or "all_providers_failed"

        job.finished_at = (await session.execute(select(func.now()))).scalar()
        await session.commit()
        # NOTE: credit capture/refund settlement hooks here in Phase 3.


async def _run_with_failover(
    session, job: Job, req: NormalizedRequest
) -> tuple[ProviderStatus | None, dict | None]:
    """Try each target in the preset chain until one succeeds."""
    targets = _resolve_targets(job)
    last: ProviderStatus | None = None
    for target in targets:
        job.provider = target["provider"]
        job.model = target["model"]
        req.model = target["model"]
        await session.commit()
        try:
            provider = get_provider(target["provider"])
            ref = await provider.submit(req)
            job.provider_job_ref = ref
            await session.commit()
            status = await _await_result(provider, ref)
            if status.state is ProviderState.succeeded:
                return status, target
            last = status
        except Exception as exc:  # noqa: BLE001 — try the next provider
            last = ProviderStatus(state=ProviderState.failed, error=f"{target['provider']}: {exc}")
    return last, None


def _resolve_targets(job: Job) -> list[dict]:
    """Primary+fallback chain from the preset, or the job's own single target."""
    if job.preset_id:
        preset = presets.get_preset(job.preset_id)
        if preset:
            return presets.targets_for(preset)
    return [{"provider": job.provider, "model": job.model}]


async def _await_result(provider, ref: str) -> ProviderStatus:
    waited = 0
    while waited < _POLL_TIMEOUT_S:
        status = await provider.poll(ref)
        if status.state is not ProviderState.running:
            return status
        await asyncio.sleep(_POLL_INTERVAL_S)
        waited += _POLL_INTERVAL_S
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

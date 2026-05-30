"""Generation endpoints: create a job, read status, list jobs.

This is the heart of the request flow in Architecture section 5. The POST returns
immediately with a job id; a worker does the slow provider call out of band.
"""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import presets
from app.auth import get_current_user
from app.db import get_session
from app.models import Job, JobStatus
from app.providers import get_provider
from app.queue import enqueue_generation
from app.schemas import GenerationCreate, JobOut

router = APIRouter(prefix="/v1/generations", tags=["generations"])


@router.post("", response_model=JobOut, status_code=202)
async def create_generation(
    body: GenerationCreate,
    session: AsyncSession = Depends(get_session),
) -> JobOut:
    preset = presets.get_preset(body.preset_id)
    if preset is None:
        raise HTTPException(404, "preset not found")

    user = await get_current_user(session)

    # Resolve preset -> normalized request -> provider.
    req = presets.build_request(preset, body.prompt, body.image_url, body.params)
    provider_name = presets.provider_for(preset)
    provider = get_provider(provider_name)

    # TODO(Phase 3): moderation + credit pre-authorization (hold) go here.
    cost = preset["credit_cost"]
    if user.credit_balance < cost:
        raise HTTPException(402, "insufficient credits")

    job = Job(
        user_id=user.id,
        preset_id=preset["id"],
        capability=req.capability,
        provider=provider_name,
        model=req.model,
        normalized_request=asdict(req),
        credit_cost=cost,
        status=JobStatus.queued,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    await enqueue_generation(job.id)
    return await _job_out(session, job.id)


@router.get("/{job_id}", response_model=JobOut)
async def get_generation(
    job_id: str,
    session: AsyncSession = Depends(get_session),
) -> JobOut:
    job = await _load(session, job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    return JobOut.model_validate(job)


@router.get("", response_model=list[JobOut])
async def list_generations(
    session: AsyncSession = Depends(get_session),
) -> list[JobOut]:
    user = await get_current_user(session)
    result = await session.execute(
        select(Job)
        .where(Job.user_id == user.id)
        .options(selectinload(Job.assets))
        .order_by(Job.created_at.desc())
        .limit(50)
    )
    return [JobOut.model_validate(j) for j in result.scalars().all()]


async def _load(session: AsyncSession, job_id: str) -> Job | None:
    result = await session.execute(
        select(Job).where(Job.id == job_id).options(selectinload(Job.assets))
    )
    return result.scalar_one_or_none()


async def _job_out(session: AsyncSession, job_id: str) -> JobOut:
    job = await _load(session, job_id)
    return JobOut.model_validate(job)

"""Pydantic request/response schemas for the public API."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models import Capability, JobStatus


class PresetOut(BaseModel):
    id: str
    label: str
    category: str
    capability: Capability
    credit_cost: int


class GenerationCreate(BaseModel):
    preset_id: str
    prompt: str
    image_url: str | None = None
    # Run the prompt through an LLM (OpenRouter) to enrich it before generation.
    enhance_prompt: bool = False
    # User overrides, validated against the preset's allowed ranges.
    params: dict = {}


class PromptEnhanceRequest(BaseModel):
    prompt: str
    capability: str = "text_to_video"


class PromptEnhanceResponse(BaseModel):
    prompt: str


class AssetOut(BaseModel):
    id: str
    kind: str
    cdn_url: str
    thumbnail_url: str | None = None


class JobOut(BaseModel):
    id: str
    status: JobStatus
    capability: Capability
    preset_id: str | None
    provider: str | None
    model: str | None
    credit_cost: int
    error_code: str | None
    created_at: datetime
    finished_at: datetime | None
    assets: list[AssetOut] = []

    class Config:
        from_attributes = True

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
    # Run the idea through the Prompt Director before generating. When true, a
    # vague prompt is expanded into a detailed, style-matched scene.
    enhance_prompt: bool = False
    # Optional example prompts the director should follow (the user's style).
    examples: list[str] = []
    # Draft mode: fast/cheap low-res generation for iteration (BytePlus/Seedance).
    draft: bool = False
    # Optional seed for reproducible generations.
    seed: int | None = None
    # User overrides, validated against the preset's allowed ranges.
    params: dict = {}


class PromptEnhanceRequest(BaseModel):
    prompt: str
    capability: str = "text_to_video"
    category: str = ""
    examples: list[str] = []


class PromptEnhanceResponse(BaseModel):
    original: str
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

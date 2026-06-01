"""Application settings, loaded from environment / .env."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "development"

    # Local-dev defaults: SQLite + local file storage + inline job execution, so
    # the whole app runs with just Python + an OpenRouter key (no Docker).
    # For production set these to Postgres / Redis / S3 (see docker-compose.yml).
    database_url: str = "sqlite+aiosqlite:///./lumina.db"
    redis_url: str = "redis://localhost:6379/0"
    api_base_url: str = "http://localhost:8000"

    # "inline" runs generation in a background task (no Redis/worker needed);
    # "arq" enqueues to the Redis-backed worker for production.
    job_runner: str = "inline"

    # "local" writes media to a folder served at /media; "s3" uses object storage.
    storage_backend: str = "local"
    media_dir: str = "./media"

    # Object storage (S3-compatible) — used when storage_backend == "s3"
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "lumina-media"
    s3_region: str = "us-east-1"
    s3_public_base_url: str = "http://localhost:9000/lumina-media"

    # Media providers — blank key => adapter runs in stub/mock mode.
    fal_api_key: str = ""
    replicate_api_token: str = ""

    # BytePlus ModelArk (ByteDance Ark) — native Seedance video, free credits.
    byteplus_api_key: str = ""
    byteplus_base_url: str = "https://ark.ap-southeast.bytepluses.com/api/v3"
    byteplus_video_model: str = "seedance-1-5-pro-251215"

    # LLM provider (OpenRouter) for text tasks like prompt enhancement.
    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-4o-mini"
    # Image-capable model on OpenRouter (returns images, not just text).
    openrouter_image_model: str = "google/gemini-2.5-flash-image-preview"
    # Video model on OpenRouter (async /api/v1/videos). Seedance 1.5 Pro supports
    # cinematic camera control, which pairs well with our motion presets.
    # Other slugs at https://openrouter.ai/collections/video-models
    openrouter_video_model: str = "bytedance/seedance-1-5-pro"

    @property
    def is_dev(self) -> bool:
        return self.env == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()

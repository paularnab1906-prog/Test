"""Application settings, loaded from environment / .env."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "development"

    database_url: str = "postgresql+asyncpg://lumina:lumina@localhost:5432/lumina"
    redis_url: str = "redis://localhost:6379/0"

    # Object storage (S3-compatible)
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "lumina-media"
    s3_region: str = "us-east-1"
    s3_public_base_url: str = "http://localhost:9000/lumina-media"

    # Media providers — blank key => adapter runs in stub/mock mode.
    fal_api_key: str = ""
    replicate_api_token: str = ""

    # LLM provider (OpenRouter) for text tasks like prompt enhancement.
    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-4o-mini"
    # Image-capable model on OpenRouter (returns images, not just text).
    openrouter_image_model: str = "google/gemini-2.5-flash-image-preview"

    @property
    def is_dev(self) -> bool:
        return self.env == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()

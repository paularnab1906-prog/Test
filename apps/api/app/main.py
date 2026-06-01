"""FastAPI application entrypoint.

Run with:  uvicorn app.main:app --reload
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.db import init_models
from app.routers import generations, health, presets, prompt


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev convenience: ensure tables exist. Use Alembic migrations in prod.
    if get_settings().is_dev:
        await init_models()
    yield


app = FastAPI(title="Lumina API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated media locally when using the filesystem storage backend.
_settings = get_settings()
if _settings.storage_backend == "local":
    media_dir = Path(_settings.media_dir)
    media_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=str(media_dir)), name="media")

app.include_router(health.router)
app.include_router(presets.router)
app.include_router(generations.router)
app.include_router(prompt.router)

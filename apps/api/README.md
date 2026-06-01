# Lumina API

FastAPI orchestration backend + Arq worker for the AI media platform.

## Run locally

```bash
# 1. start infra (from repo root)
cp .env.example .env
docker compose up -d                 # postgres, redis, minio

# 2. install + run the API
cd apps/api
uv venv && source .venv/bin/activate  # or: python -m venv .venv && source .venv/bin/activate
uv pip install -e ".[dev]"            # or: pip install -e ".[dev]"
uvicorn app.main:app --reload         # -> http://localhost:8000/docs

# 3. run the worker (separate shell, same venv)
arq app.worker.WorkerSettings
```

With no provider keys set, the adapters run in **stub mode**: generations
complete with a placeholder asset so you can exercise the full pipeline without
spending money. The keys that unlock real calls:
- `OPENROUTER_API_KEY` — prompt enhancement (LLM) **and** real text→image
  generation via an image-capable model (`OPENROUTER_IMAGE_MODEL`).
- `FAL_API_KEY`, `REPLICATE_API_TOKEN` — video providers (and image fallback).

### OpenRouter-only test mode (current setup)
With just `OPENROUTER_API_KEY` set you can test the **whole product** end to end —
OpenRouter now serves text, image, AND video:
- **Prompt Director** — real (confirmed working). `OPENROUTER_MODEL`.
- **text→image** presets (Soul Portrait, Cinematic Still) — real images via
  `OPENROUTER_IMAGE_MODEL`.
- **text/image→video** presets (Crash Zoom, Establishing Shot, ...) — real clips
  via OpenRouter's async video API (`OPENROUTER_VIDEO_MODEL`).

fal/Replicate remain wired as **fallbacks** for when you add their keys later.

Quick local checks (save files, no app deps):
```bash
python scripts/smoke_openrouter_image.py "a lonely lighthouse at dusk"   # -> out.png
python scripts/smoke_openrouter_video.py --list                          # show video model slugs
python scripts/smoke_openrouter_video.py "a lonely lighthouse at dusk"   # -> out.mp4
```

## Try it

```bash
# list presets
curl localhost:8000/v1/presets

# enhance a prompt via the LLM layer (OpenRouter)
curl -X POST localhost:8000/v1/prompt/enhance \
  -H 'content-type: application/json' \
  -d '{"prompt":"a fox in a city","capability":"image_to_video"}'

# start a generation (optionally auto-enhance the prompt first)
curl -X POST localhost:8000/v1/generations \
  -H 'content-type: application/json' \
  -d '{"preset_id":"crash_zoom","prompt":"a fox running through neon city","image_url":"https://example.com/fox.jpg","enhance_prompt":true}'

# poll status (use the id from the response)
curl localhost:8000/v1/generations/<job_id>
```

## Layout

```
app/
├── main.py            # FastAPI app + routers
├── config.py          # settings
├── db.py / models.py  # async SQLAlchemy
├── auth.py            # Phase-0 dev-user stub
├── queue.py           # arq enqueue pool
├── worker.py          # arq worker: provider call + storage
├── storage.py         # copy provider outputs into our bucket
├── providers/         # provider adapter layer (base + fal)
├── presets/           # preset engine + YAML effects
└── routers/           # health, presets, generations
```

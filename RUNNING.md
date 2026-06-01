# Running the whole app locally (OpenRouter only, no Docker)

The app defaults to a zero-infra local mode: **SQLite** (file DB), **local file
storage** (served at `/media`), and **inline** job execution (no Redis/worker).
You only need Python 3.11+, Node 18+, and an OpenRouter API key.

## 1. Backend (FastAPI)

```bash
cd apps/api
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -e ".[dev]"
```

Create `apps/api/.env` with your key:
```
OPENROUTER_API_KEY=sk-or-...your-key...
OPENROUTER_MODEL=openai/gpt-4o-mini
OPENROUTER_IMAGE_MODEL=google/gemini-2.5-flash-image-preview
OPENROUTER_VIDEO_MODEL=bytedance/seedance-1-5-pro
```
> `bytedance/seedance-1-5-pro` is confirmed working. See other slugs with
> `python scripts/smoke_openrouter_video.py --list`.

Run it:
```bash
uvicorn app.main:app --reload
```
- API docs: http://localhost:8000/docs
- A `lumina.db` file and a `media/` folder appear automatically. No Docker needed.

## 2. Frontend (Next.js)

In a second terminal:
```bash
cd apps/web
npm install
# point the web app at the API (PowerShell): $env:NEXT_PUBLIC_API_BASE_URL="http://localhost:8000"
# or create apps/web/.env.local with: NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
npm run dev
```
Open http://localhost:3000 → **Open Studio**.

## 3. Generate

In the Studio:
1. Pick a preset (e.g. **Soul Portrait** for image, **Establishing Shot** for video).
2. Type a rough idea — leave the **Prompt Director** toggle on.
3. (Optional) add a style example line.
4. **Generate.** The job runs inline; status polls queued → running → succeeded,
   then the image/video appears.

Costs apply per generation (image cheap, video ~$0.20–0.30/clip). Set a spend
limit at https://openrouter.ai/settings/credits.

## Going to production later
Flip these env vars and bring up `docker compose up -d`:
```
DATABASE_URL=postgresql+asyncpg://...
JOB_RUNNER=arq        # + run: arq app.worker.WorkerSettings
STORAGE_BACKEND=s3
```
Everything else stays the same.

## Troubleshooting
| Symptom | Fix |
|---|---|
| `ModuleNotFoundError` | activate the venv, re-run `pip install -e ".[dev]"` |
| Studio shows nothing after Generate | check the uvicorn console for errors; confirm the key is set |
| Video 402 / fails | add OpenRouter credit, or pick a cheaper `OPENROUTER_VIDEO_MODEL` |
| CORS error in browser | confirm API on :8000 and `NEXT_PUBLIC_API_BASE_URL` matches |

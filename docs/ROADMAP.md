# Build Roadmap

Phased plan to go from empty repo to a working Higgsfield-style MVP and beyond.
Each phase is shippable and de-risks the next. Estimates assume a small team.

## Phase 0 — Foundations (scaffold)  ✅ in progress
- [x] Monorepo: `apps/web` (Next.js + TS), `apps/api` (FastAPI).
- [x] `docker-compose` for Postgres + Redis + object storage (MinIO locally).
- [x] Base schema from Architecture §4 (SQLAlchemy models; dev auto-create).
- [x] Phase-0 dev-user auth stub (real OIDC deferred).
- [ ] Alembic migrations (replace dev auto-create before prod).
- [ ] CI: lint, typecheck, test on push.

## Phase 1 — One real generation, end to end (the critical proof)
- [x] Provider adapter interface + fal.ai adapter (stub mode until key added).
- [x] `POST /v1/generations` → queue (Arq) → worker → provider → store result.
- [x] Async job lifecycle: queued/running/succeeded/failed.
- [x] Minimal Studio UI: preset + prompt → polled status → video player.
- [x] Copy provider outputs into our object storage.
- [ ] Replace polling with SSE/WebSocket push.
- [ ] Implement the real (non-stub) fal HTTP path once a key is available.
- **Exit criterion:** a user can type a prompt and get a video back, reliably.

## Phase 2 — Presets / effects + image-to-video
- [ ] Preset engine (YAML config → NormalizedRequest) + validation.
- [ ] Preset gallery UI; param controls with allowed ranges.
- [ ] Image upload (presigned) + image-to-video capability.
- [ ] Seed a starter set of camera-motion presets.

## Phase 3 — Credits & billing
- [ ] Credit ledger, holds, capture/refund on job settle.
- [ ] Stripe subscriptions + credit packs + webhook reconciliation.
- [ ] Cost-in-credits preview in Studio; balance in account.
- [ ] Per-job provider-cost recording + margin reporting.

## Phase 4 — Moderation & safety (gate before any public feed)
- [ ] Input text + image moderation before provider calls.
- [ ] Output moderation before publish.
- [ ] Identity/likeness consent gating + output provenance/watermark.
- [ ] `moderation_events` audit + appeals path.

## Phase 5 — Social / explore
- [ ] Publish-to-feed, explore gallery, likes, remix.
- [ ] Per-asset preset attribution ("made with Crash Zoom").

## Phase 6 — Scale & multi-provider
- [ ] Second/third adapters (Replicate, Runway/Kling) + router + failover.
- [ ] Per-capability queues/pools, backpressure, reconciliation cron.
- [ ] Cheapest-acceptable-provider routing per preset.
- [ ] Observability: traces, per-provider latency/cost dashboards.

## Phase 7 — Polish
- [ ] Asset library, collections, search.
- [ ] Talking-avatar / lipsync capability.
- [ ] Templates marketplace; referral/credits growth loops.

---

## Sequencing logic
Phase 1 is the make-or-break: prove async generation through a real provider
before building product polish around it. Money (Phase 3) and safety (Phase 4)
must both land before a **public** feed (Phase 5) opens. Multi-provider routing
(Phase 6) is a scale/cost optimization — deliberately deferred until one provider
path is solid.

# Lumina — an AI Media Generation Platform

A Higgsfield-style platform for generating cinematic video and images from text
and images, with camera-motion presets, character consistency, and a social
explore feed. Generation is powered by **hosted model APIs** (fal.ai, Replicate,
Runway, Kling, etc.) behind a provider-agnostic orchestration layer, so the
platform owns the product experience without owning GPUs or model weights.

> **Status:** Architecture & planning phase. No application code yet — this repo
> currently contains the technical design. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
> and [`docs/ROADMAP.md`](docs/ROADMAP.md).

## Stack at a glance

| Layer        | Choice                                             |
|--------------|----------------------------------------------------|
| Frontend     | Next.js (App Router) + React + TypeScript          |
| Backend API  | Python + FastAPI                                    |
| Async jobs   | Celery (or Arq) + Redis                             |
| Database     | PostgreSQL                                          |
| Object store | S3-compatible (AWS S3 or Cloudflare R2) + CDN       |
| AI models    | Hosted provider APIs via an adapter layer           |
| Billing      | Stripe (subscriptions + credit packs)               |

## What this platform is — and isn't

- **Is:** an orchestration + product layer over third-party generative models,
  with credits/billing, async job handling, a preset/"effects" system, asset
  storage, and a gallery.
- **Isn't:** a model trainer or a GPU host. We do not train, fine-tune, or run
  models ourselves in this design — we route to providers that do.

## Key dependencies & constraints

- Generation quality, latency, and cost are bounded by the **upstream providers**.
- Each provider's **Terms of Service and content policy** apply to traffic we
  send them; the platform must enforce input/output **moderation** (see
  Architecture §9).
- Per-generation cost is a real COGS line — **credits and cost tracking are
  first-class**, not afterthoughts.

## Repo layout (target)

```
.
├── apps/
│   ├── web/            # Next.js frontend
│   └── api/            # FastAPI backend + workers
├── packages/
│   └── shared/         # shared TS types / OpenAPI client
├── infra/              # IaC, docker-compose, deployment
└── docs/               # architecture, roadmap, ADRs
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full design.

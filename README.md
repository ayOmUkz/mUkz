# Options Greeks Cockpit

A trader-facing options analytics app that reframes the Greeks (Δ, Γ, Θ, ν) plus Premium Fairness as **forces** rather than static numbers — answering "where does this trade break, where does it explode, what force dominates it."

V1 (Path A) is single-leg only with a 5-axis Greek Radar, score-weighted Position Personality classifier (5 primary × 3 qualifiers), and per-position scenario simulator. Full plan: `~/.claude/plans/you-are-claude-opus-quirky-hare.md`.

## Repo layout

```
apps/
  web/      # Next.js (App Router) frontend — TS, Tailwind, shadcn/ui, D3
  quant/    # Python FastAPI service — classifier, scoring, scenarios, Polygon client
packages/   # shared types (TS↔Python contracts) — to be added
infra/
  supabase/migrations/   # SQL migrations
.github/workflows/       # CI pipelines — to be added
```

## Quick start

### Web (Next.js)

```sh
cd apps/web
pnpm install
cp .env.example .env.local   # fill in Clerk + Supabase keys
pnpm dev                     # http://localhost:3000
```

### Quant service (FastAPI)

```sh
cd apps/quant
uv sync                      # installs deps from pyproject.toml
cp .env.example .env         # fill in Polygon + Redis
uv run uvicorn app.main:app --reload --port 8000
# Health check: curl http://localhost:8000/health
```

### Tests

```sh
# Web
cd apps/web && pnpm test     # vitest + playwright (to be added)

# Quant
cd apps/quant && uv run pytest
```

## Stack

| Layer | Choice |
|---|---|
| Frontend | Next.js (App Router) + TypeScript + Tailwind + shadcn/ui + D3 + Framer Motion |
| Auth | Clerk |
| Database | Supabase (Postgres) — Clerk JWT → Supabase RLS |
| Cache | Upstash Redis |
| Quant service | Python 3.11 + FastAPI + numpy/scipy |
| Data provider | Polygon (Options paid tier, real-time) |
| Hosting | Vercel (web) + Fly.io (quant) |

## Status

Phase 0 (Foundation) — in progress. Next: install deps, wire Clerk + Supabase + Upstash, prove end-to-end "ticker → chain → 5-axis radar render".

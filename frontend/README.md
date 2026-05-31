# CEF Filter Proxy — Frontend

A **Bun + Turborepo + Next.js** dashboard for the CEF Filter Proxy. The Python
`app/` service is **API-only**; this is the decoupled management UI that talks to
it over HTTP + SSE.

**Stack:** Bun · Turborepo · Next.js 16 (App Router, React 19) · TypeScript ·
Tailwind v4 · shadcn/ui (Base UI) · Biome.

## Layout

```
frontend/
  apps/web/             Next.js dashboard (metrics, rules CRUD, dry-run, live SSE events)
  packages/api-client/  typed client + SSE helper for the FastAPI API
  turbo.json            pipeline   ·   biome.json   lint/format   ·   tsconfig.base.json
```

## Prerequisites

- **Bun ≥ 1.1**
- The **backend running** (from the repo root): `make run` → http://localhost:8080

## Quick start

```bash
cd frontend
bun install

# optional: point the UI at a non-default backend
cp apps/web/.env.example apps/web/.env.local   # NEXT_PUBLIC_API_BASE=http://localhost:8080

bun dev          # turbo runs apps/web on http://localhost:3000
```

Open **http://localhost:3000**. The backend's `CORS_ALLOW_ORIGINS` already allows
`http://localhost:3000` by default.

## Commands

| Command | What it does |
|---|---|
| `bun dev` | Run `apps/web` (Next dev, Turbopack) on :3000 |
| `bun run build` | Production build (Turbopack) |
| `bun run start` | Serve the production build |
| `bun run lint` | Biome lint + format check |
| `bun run format` | Biome format (write) |
| `bun run check-types` | `tsc --noEmit` across the workspace |

## Configuration

`apps/web/.env.local`:

- `NEXT_PUBLIC_API_BASE` — backend base URL (default `http://localhost:8080`).

**Auth:** reads are open; mutations require the backend bearer token **when
`API_TOKEN` is set** on the backend. Use the **Set token** button — it is stored
in `localStorage` and sent as `Authorization: Bearer …`. The header shows a
warning banner while the backend is unauthenticated.

## Notes

- shadcn here uses the **`base-nova`** style (Base UI primitives, not Radix) — UI
  components live in `apps/web/components/ui/` and are excluded from Biome.
- The shadcn CLI is run with `npx` (Node), not `bunx` — Bun 1.1.x lacks an
  `events.addAbortListener` export the CLI needs.

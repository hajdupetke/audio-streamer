# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Tech Stack

**Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 async + asyncpg, PostgreSQL 16, Alembic, Pydantic v2, uv
**Frontend:** React 18, TypeScript strict, Vite, TanStack Router (file-based), TanStack Query v5, Tailwind CSS v4, shadcn/ui, Zustand (player only), pnpm
**Auth:** httpOnly secure cookies, JWT (access + refresh), refresh token rotation + reuse detection
**Deploy:** Docker Compose (backend, postgres, frontend/nginx), targeted for Coolify

## Commands

### Backend (run from `backend/`)
```
uv sync                                                   # install/sync deps
uv run uvicorn app.main:app --reload                      # dev server on :8000
uv run alembic upgrade head                               # apply migrations
uv run alembic revision --autogenerate -m "description"   # generate new migration
uv run alembic downgrade -1                               # rollback one step
```

### Frontend (run from `frontend/`)
```
pnpm install
pnpm dev        # dev server on :5173
pnpm build      # production build
pnpm lint
```

## Project Structure

```
audio-streamer/
├── backend/
│   ├── pyproject.toml        # uv project + all deps
│   ├── alembic.ini
│   ├── alembic/
│   │   └── versions/         # migration files
│   ├── addons/               # Addon implementations (scanned on startup)
│   │   ├── librivox/
│   │   └── local_files/
│   └── app/
│       ├── main.py           # FastAPI app, CORS, lifespan
│       ├── config.py         # Pydantic Settings (loaded from .env)
│       ├── database.py       # async engine, session factory, get_db() dep
│       ├── models/           # SQLAlchemy 2.0 ORM models
│       ├── routers/          # FastAPI route handlers
│       ├── services/         # Business logic
│       ├── schemas/          # Pydantic v2 request/response schemas
│       └── addons/           # Addon framework: ABCs, manifest, registry, loader
├── frontend/
│   └── src/
│       ├── routes/           # TanStack Router file-based routes
│       ├── components/       # Reusable UI components
│       └── stores/           # Zustand stores (player only)
├── docker-compose.yml
└── .env.example
```

## Architecture

### Addon System

The app's defining architectural concept. `app/addons/` is the framework; `backend/addons/` are the plugin implementations.

`app/addons/` contains:
- `base.py` — `ContentSource` and `StreamResolver` ABCs
- `manifest.py` — `AddonManifest` with id, name, capabilities, `settings_schema`
- `registry.py` — `AddonRegistry` singleton; scans `backend/addons/*/` on startup

Each addon in `backend/addons/{name}/` must provide:
- `manifest.py` — exports an `AddonManifest` instance
- `addon.py` — class implementing `ContentSource` and/or `StreamResolver`

`settings_schema` in the manifest (list of field descriptors with key/type/label) drives the frontend's dynamic addon config form. Per-user settings are stored Fernet-encrypted as JSON in `user_addon_settings`.

### Auth Flow

1. Login → set `access_token` (15 min) + `refresh_token` (30 days) as httpOnly Secure cookies
2. Frontend sends cookies automatically (`credentials: "include"` on all requests)
3. Refresh endpoint rotates token; old token stored with `replaced_by` ref for audit
4. Reuse detection: using a revoked token revokes the entire chain for that user
5. Stream endpoint accepts `?token=` query param as fallback (HTML `<audio src>` can't set cookies)

### Database Models

- `users`, `refresh_tokens` — authentication
- `user_addon_settings` — Fernet-encrypted JSON per (user, addon); unique on (user_id, addon_id)
- `library_items` — saved audiobooks; unique on (user_id, addon_id, external_id)
- `playback_progress` — position/duration; unique on (user_id, library_item_id, file_id)

### Stream Endpoint

`GET /api/stream/{addon_id}/{item_id}/{file_id}` — the addon's `StreamResolver.resolve()` returns either a direct URL (backend redirects) or proxy info (backend proxies with Range request passthrough). LibriVox uses direct redirect; Local Files proxies from disk with Range support.

## Environment Variables

See `.env.example`. Critical:
- `DATABASE_URL` — `postgresql+asyncpg://user:pass@host:port/db`
- `SECRET_KEY` — `openssl rand -hex 32`
- `FERNET_KEY` — `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
- `LOCAL_FILES_LIBRARY_PATH` — server-side path for the Local Files addon

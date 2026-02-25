# Audio Streamer

A self-hostable audiobook streaming app with a plugin-based addon system. Stream from LibriVox or your own local library through a clean dark-themed web UI with a persistent audio player.

## Features

- **Addon system** — pluggable content sources and stream resolvers; ships with LibriVox and Local Files addons
- **Search** — search across all enabled addons simultaneously, or filter by one
- **Library** — save books to your personal library with per-book metadata
- **Playback progress** — position auto-saved every 5 seconds per chapter, restored on next play
- **Auth** — email/password with httpOnly JWT cookies, refresh token rotation, and reuse detection
- **Per-user addon settings** — encrypted at rest (Fernet AES-128); configured via the in-app UI
- **Docker Compose** — single `docker compose up` deploys everything behind nginx

## Tech Stack

| Layer | Stack |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 async, asyncpg, PostgreSQL 16, Alembic, uv |
| Frontend | React 18, TypeScript strict, Vite, TanStack Router, TanStack Query v5, Tailwind CSS v4, shadcn/ui, Zustand |
| Auth | httpOnly secure cookies, JWT (access 15 min + opaque refresh 30 days), rotation + reuse detection |
| Deploy | Docker Compose (backend, postgres, frontend/nginx) |

## Quick Start (Docker)

### 1. Clone and configure

```bash
git clone <repo-url>
cd audio-streamer
cp .env.example .env
```

Edit `.env` and set:

```bash
# Generate with: openssl rand -hex 32
SECRET_KEY=your-secret-key

# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
FERNET_KEY=your-fernet-key

# Path to your audiobook folder on the host (Local Files addon)
LOCAL_FILES_LIBRARY_PATH=/path/to/your/audiobooks
```

### 2. Start

```bash
docker compose up --build
```

The app will be available at **http://localhost**. The backend runs migrations automatically on startup.

### 3. Register and configure

1. Open http://localhost and register an account
2. Go to **Addons** to configure the Local Files path (if using local files) or enable/disable LibriVox
3. Go to **Search** and start listening

## Local Development

### Prerequisites

- Python 3.12+, [uv](https://github.com/astral-sh/uv)
- Node 20+, [pnpm](https://pnpm.io)
- PostgreSQL 16 running locally

### Backend

```bash
cd backend
cp ../.env.example ../.env   # edit DATABASE_URL to point to your local postgres
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
# → http://localhost:8000
```

### Frontend

```bash
cd frontend
pnpm install
pnpm dev
# → http://localhost:5173 (proxies /api to localhost:8000)
```

## Project Structure

```
audio-streamer/
├── backend/
│   ├── pyproject.toml        # dependencies (managed by uv)
│   ├── alembic/versions/     # database migrations
│   ├── addons/               # addon plugin implementations
│   │   ├── librivox/         # LibriVox public domain audiobooks
│   │   └── local_files/      # local filesystem audiobooks
│   └── app/
│       ├── main.py           # FastAPI app, CORS, lifespan
│       ├── config.py         # settings (loaded from .env)
│       ├── routers/          # HTTP route handlers
│       ├── services/         # business logic
│       ├── models/           # SQLAlchemy ORM models
│       ├── schemas/          # Pydantic v2 request/response schemas
│       └── addons/           # addon framework (ABCs, registry, loader, seeder)
├── frontend/
│   └── src/
│       ├── routes/           # TanStack Router file-based routes
│       ├── components/       # shared UI components (Navbar, PlayerBar, BookCard, …)
│       ├── hooks/            # TanStack Query hooks
│       ├── stores/           # Zustand player store
│       └── lib/api.ts        # typed fetch client
├── docker-compose.yml
└── .env.example
```

## Addon System

Addons provide content search and/or stream resolution. The framework (`app/addons/`) scans `backend/addons/*/` on startup and seeds each addon into every user's account.

Each addon implements:
- `ContentSource` — `search(q)` and `get_details(item_id)`
- `StreamResolver` — `resolve(item_id, file_id)` returning a local path, proxy URL, or redirect URL

Per-user settings (API keys, library paths, etc.) are stored encrypted and surfaced through a dynamic settings form driven by the addon's `settings_schema`. See `backend/ADDONS.md` for the full addon development guide.

## Environment Variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string (`postgresql+asyncpg://...`) |
| `POSTGRES_USER/PASSWORD/DB` | Used by docker-compose to initialise the postgres container |
| `SECRET_KEY` | JWT signing key — `openssl rand -hex 32` |
| `FERNET_KEY` | Addon settings encryption key — see `.env.example` |
| `ALGORITHM` | JWT algorithm (default: `HS256`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime (default: `15`) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime (default: `30`) |
| `CORS_ORIGINS` | JSON array of allowed origins, e.g. `["http://localhost:5173"]` |
| `ENVIRONMENT` | `development` disables secure cookie flag |
| `LOCAL_FILES_LIBRARY_PATH` | Server-side root path for the Local Files addon |

## API

The backend exposes a REST API at `/api`. Interactive docs are available at **http://localhost:8000/docs** when the backend is running.

| Group | Endpoints |
|---|---|
| Auth | `POST /api/auth/register`, `login`, `logout`, `refresh`, `GET /api/auth/me`, `token` |
| Search | `GET /api/search`, `GET /api/addons/{addon_id}/items/{item_id}` |
| Library | `GET/POST /api/library`, `DELETE /api/library/{id}` |
| Progress | `GET/POST /api/progress/{library_item_id}` |
| Addons | `GET/PATCH /api/addons/{id}`, `GET/PUT /api/addons/{id}/settings` |
| Stream | `GET /api/stream/{addon_id}/{item_id}/{file_id}` |

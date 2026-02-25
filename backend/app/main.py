from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.addons.loader import load_bundled_addons
from app.addons.seeder import seed_addons_for_all_users
from app.config import get_settings
from app.database import AsyncSessionLocal
from app.routers import addons, auth, library, progress, search, stream

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Scan backend/addons/*/ and register bundled addon implementations
    load_bundled_addons()

    # 2. Ensure every existing user has an installation row for every bundled addon
    async with AsyncSessionLocal() as db:
        await seed_addons_for_all_users(db)

    yield
    # Shutdown (nothing to clean up for now)


app = FastAPI(
    title="Audio Streamer",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(addons.router)
app.include_router(library.router)
app.include_router(progress.router)
app.include_router(search.router)
app.include_router(stream.router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}

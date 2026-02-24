from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: addon registry will be initialized here in Step 3
    yield
    # Shutdown


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


@app.get("/health")
async def health_check():
    return {"status": "ok"}

"""FastAPI application entry point.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT

FIX: CORS origins are now read from the AGENTABILITY_CORS_ORIGINS environment
     variable (comma-separated) so the platform works in production/OCI without
     code changes.  Falls back to localhost:3000 + localhost:5173 for local dev.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from .dependencies import get_store
from .routers import agents, alerts, conflicts, decisions, health, metrics


def _cors_origins() -> list[str]:
    """
    Read allowed CORS origins from env.  Supports comma-separated list:
        AGENTABILITY_CORS_ORIGINS=http://myserver.com:3000,http://myserver.com:8100
    Falls back to localhost defaults for development.
    """
    raw = os.getenv("AGENTABILITY_CORS_ORIGINS", "")
    if raw.strip():
        return [o.strip() for o in raw.split(",") if o.strip()]
    return [
        "http://localhost:3000",
        "http://localhost:5173",
        # Allow any port on localhost for flexible dev setups
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialise and teardown the shared SQLiteStore."""
    store = get_store()
    app.state.store = store
    yield
    store.close()


app = FastAPI(
    title="Agentability API",
    description="Agent Operating Intelligence Layer — REST API",
    version="0.3.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(decisions.router)
app.include_router(agents.router)
app.include_router(metrics.router)
app.include_router(conflicts.router)
app.include_router(alerts.router)


@app.get("/")
async def root() -> dict:
    return {"service": "agentability-api", "version": "0.2.0a1", "docs": "/docs"}


if __name__ == "__main__":
    uvicorn.run("platform.api.main:app", host="0.0.0.0", port=8000, reload=True)

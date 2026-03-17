"""FastAPI application entry point.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from .dependencies import get_store
from .routers import agents, conflicts, decisions, health, metrics


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
    version="0.2.0a1",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(decisions.router)
app.include_router(agents.router)
app.include_router(metrics.router)
app.include_router(conflicts.router)


@app.get("/")
async def root() -> dict:
    return {"service": "agentability-api", "version": "0.2.0a1", "docs": "/docs"}


if __name__ == "__main__":
    uvicorn.run("platform.api.main:app", host="0.0.0.0", port=8000, reload=True)

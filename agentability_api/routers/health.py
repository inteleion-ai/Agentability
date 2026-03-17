"""Health and Prometheus metrics router.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import time
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from agentability.storage.sqlite_store import SQLiteStore

from ..dependencies import get_store
from ..schemas import HealthOut

router = APIRouter(tags=["health"])

_start_time = time.time()
Store = Annotated[SQLiteStore, Depends(get_store)]


@router.get("/health", response_model=HealthOut)
async def health(store: Store) -> HealthOut:
    """Liveness + readiness check."""
    cur = store.conn.cursor()
    cur.execute("SELECT COUNT(*) as cnt FROM decisions")
    d_count = cur.fetchone()["cnt"]
    cur.execute("SELECT COUNT(*) as cnt FROM conflicts")
    c_count = cur.fetchone()["cnt"]

    return HealthOut(
        status="healthy",
        version="0.2.0a1",
        db_path=str(store.database_path),
        total_decisions=d_count,
        total_conflicts=c_count,
        uptime_seconds=time.time() - _start_time,
    )


@router.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics(store: Store) -> str:
    """Prometheus-compatible scrape endpoint for Grafana integration."""
    cur = store.conn.cursor()
    cur.execute("SELECT COUNT(*) as cnt FROM decisions")
    d_count = cur.fetchone()["cnt"]
    cur.execute("SELECT COUNT(*) as cnt FROM conflicts")
    c_count = cur.fetchone()["cnt"]
    cur.execute("SELECT AVG(confidence) as avg FROM decisions WHERE confidence IS NOT NULL")
    avg_conf = cur.fetchone()["avg"] or 0.0
    cur.execute("SELECT AVG(latency_ms) as avg FROM decisions WHERE latency_ms IS NOT NULL")
    avg_lat = cur.fetchone()["avg"] or 0.0
    cur.execute("SELECT SUM(cost_usd) as total FROM llm_metrics")
    total_cost = cur.fetchone()["total"] or 0.0

    return "\n".join([
        "# HELP agentability_decisions_total Total decisions recorded",
        "# TYPE agentability_decisions_total counter",
        f"agentability_decisions_total {d_count}",
        "# HELP agentability_conflicts_total Total conflicts recorded",
        "# TYPE agentability_conflicts_total counter",
        f"agentability_conflicts_total {c_count}",
        "# HELP agentability_avg_confidence Average decision confidence",
        "# TYPE agentability_avg_confidence gauge",
        f"agentability_avg_confidence {avg_conf:.4f}",
        "# HELP agentability_avg_latency_ms Average decision latency",
        "# TYPE agentability_avg_latency_ms gauge",
        f"agentability_avg_latency_ms {avg_lat:.2f}",
        "# HELP agentability_total_cost_usd Total LLM spend in USD",
        "# TYPE agentability_total_cost_usd counter",
        f"agentability_total_cost_usd {total_cost:.6f}",
        "",
    ])

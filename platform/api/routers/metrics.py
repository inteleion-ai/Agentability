"""Metrics router — LLM cost, latency, and token analytics.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import sqlite3
import statistics
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from agentability.storage.sqlite_store import SQLiteStore

from ..dependencies import get_store
from ..schemas import CostSummaryOut

router = APIRouter(prefix="/api/metrics", tags=["metrics"])

Store = Annotated[SQLiteStore, Depends(get_store)]


@router.get("/cost", response_model=CostSummaryOut)
async def get_cost_summary(
    store: Store,
    hours: int = Query(24, ge=1, le=720),
) -> CostSummaryOut:
    """Return LLM cost breakdown by model and provider."""
    since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

    cur = store.conn.cursor()
    cur.execute(
        "SELECT model, provider, cost_usd, total_tokens "
        "FROM llm_metrics WHERE timestamp >= ? ORDER BY timestamp DESC",
        (since,),
    )
    rows = cur.fetchall()

    total_cost = 0.0
    total_tokens = 0
    by_model: dict[str, float] = {}
    by_provider: dict[str, float] = {}

    for row in rows:
        model, provider, cost, tokens = row["model"], row["provider"], float(row["cost_usd"]), int(row["total_tokens"])
        total_cost += cost
        total_tokens += tokens
        by_model[model] = by_model.get(model, 0.0) + cost
        by_provider[provider] = by_provider.get(provider, 0.0) + cost

    # Decisions count for cost-per-decision
    cur.execute("SELECT COUNT(*) as cnt FROM decisions WHERE timestamp >= ?", (since,))
    decision_count = cur.fetchone()["cnt"] or 1

    return CostSummaryOut(
        total_cost_usd=total_cost,
        total_tokens=total_tokens,
        total_calls=len(rows),
        by_model=by_model,
        by_provider=by_provider,
        cost_per_decision=total_cost / decision_count,
    )


@router.get("/cost/timeline")
async def get_cost_timeline(
    store: Store,
    hours: int = Query(24, ge=1, le=720),
    bucket_minutes: int = Query(60, ge=5, le=1440),
) -> list[dict]:
    """Return cost bucketed over time."""
    since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    cur = store.conn.cursor()
    cur.execute(
        "SELECT timestamp, cost_usd, model FROM llm_metrics WHERE timestamp >= ?",
        (since,),
    )
    rows = cur.fetchall()

    bucket_secs = bucket_minutes * 60
    buckets: dict[int, dict] = {}
    for row in rows:
        ts = datetime.fromisoformat(row["timestamp"]).timestamp()
        key = int(ts // bucket_secs) * bucket_secs
        b = buckets.setdefault(key, {"cost": 0.0, "calls": 0})
        b["cost"] += float(row["cost_usd"])
        b["calls"] += 1

    return [
        {
            "timestamp": datetime.utcfromtimestamp(k).isoformat(),
            "cost_usd": v["cost"],
            "calls": v["calls"],
        }
        for k, v in sorted(buckets.items())
    ]


@router.get("/latency")
async def get_latency_stats(
    store: Store,
    agent_id: str | None = Query(None),
    hours: int = Query(24, ge=1, le=720),
) -> dict:
    """Return p50/p95/p99 latency for decisions."""
    since = datetime.utcnow() - timedelta(hours=hours)
    decisions = store.query_decisions(agent_id=agent_id, start_time=since, limit=10000)
    lats = sorted(d.latency_ms for d in decisions if d.latency_ms is not None)
    if not lats:
        return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "avg": 0.0, "count": 0}
    n = len(lats)
    return {
        "p50": lats[int(n * 0.50)],
        "p95": lats[min(int(n * 0.95), n - 1)],
        "p99": lats[min(int(n * 0.99), n - 1)],
        "avg": statistics.mean(lats),
        "count": n,
    }


@router.get("/latency/timeline")
async def get_latency_timeline(
    store: Store,
    agent_id: str | None = Query(None),
    hours: int = Query(24, ge=1, le=720),
    bucket_minutes: int = Query(60, ge=5, le=1440),
) -> list[dict]:
    """Return average latency bucketed over time."""
    since = datetime.utcnow() - timedelta(hours=hours)
    decisions = store.query_decisions(agent_id=agent_id, start_time=since, limit=10000)

    bucket_secs = bucket_minutes * 60
    buckets: dict[int, list[float]] = {}
    for d in decisions:
        if d.latency_ms is None:
            continue
        key = int(d.timestamp.timestamp() // bucket_secs) * bucket_secs
        buckets.setdefault(key, []).append(d.latency_ms)

    return [
        {
            "timestamp": datetime.utcfromtimestamp(k).isoformat(),
            "avg_latency_ms": statistics.mean(vals),
            "p95_latency_ms": sorted(vals)[min(int(len(vals) * 0.95), len(vals) - 1)],
            "count": len(vals),
        }
        for k, vals in sorted(buckets.items())
    ]


@router.get("/summary")
async def get_overview_summary(
    store: Store,
    hours: int = Query(24, ge=1, le=720),
) -> dict:
    """Single endpoint for the dashboard overview cards."""
    since = datetime.utcnow() - timedelta(hours=hours)
    decisions = store.query_decisions(start_time=since, limit=10000)

    confs = [d.confidence for d in decisions if d.confidence is not None]
    lats = [d.latency_ms for d in decisions if d.latency_ms is not None]
    agents = {d.agent_id for d in decisions}

    # Violations rate
    violated = sum(1 for d in decisions if d.constraints_violated)
    violation_rate = violated / len(decisions) if decisions else 0.0

    return {
        "total_decisions": len(decisions),
        "unique_agents": len(agents),
        "avg_confidence": statistics.mean(confs) if confs else None,
        "avg_latency_ms": statistics.mean(lats) if lats else None,
        "violation_rate": violation_rate,
        "total_cost_usd": sum(d.total_cost_usd for d in decisions),
        "total_tokens": sum(d.total_tokens for d in decisions),
        "window_hours": hours,
    }

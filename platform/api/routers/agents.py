"""Agents router — metrics, drift, and per-agent analytics.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import statistics
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from agentability.analyzers.drift_detector import DriftDetector
from agentability.storage.sqlite_store import SQLiteStore

from ..dependencies import get_store
from ..schemas import AgentSummaryOut, DriftResultOut

router = APIRouter(prefix="/api/agents", tags=["agents"])

Store = Annotated[SQLiteStore, Depends(get_store)]


@router.get("", response_model=list[AgentSummaryOut])
async def list_agents(
    store: Store,
    limit: int = Query(50, ge=1, le=200),
) -> list[AgentSummaryOut]:
    """Return all unique agents with aggregate metrics."""
    decisions = store.query_decisions(limit=5000)

    # Group by agent
    by_agent: dict[str, list] = {}
    for d in decisions:
        by_agent.setdefault(d.agent_id, []).append(d)

    summaries: list[AgentSummaryOut] = []
    for agent_id, ds in list(by_agent.items())[:limit]:
        confs = [d.confidence for d in ds if d.confidence is not None]
        lats = [d.latency_ms for d in ds if d.latency_ms is not None]
        summaries.append(
            AgentSummaryOut(
                agent_id=agent_id,
                total_decisions=len(ds),
                avg_confidence=statistics.mean(confs) if confs else None,
                avg_latency_ms=statistics.mean(lats) if lats else None,
                success_rate=None,
                total_cost_usd=sum(d.total_cost_usd for d in ds),
                total_tokens=sum(d.total_tokens for d in ds),
                total_llm_calls=sum(d.llm_calls for d in ds),
            )
        )
    summaries.sort(key=lambda s: s.total_decisions, reverse=True)
    return summaries


@router.get("/{agent_id}/summary", response_model=AgentSummaryOut)
async def get_agent_summary(
    agent_id: str,
    store: Store,
    hours: int = Query(24, ge=1, le=720),
) -> AgentSummaryOut:
    """Return aggregate metrics for one agent over a time window."""
    start = datetime.utcnow() - timedelta(hours=hours)
    decisions = store.query_decisions(agent_id=agent_id, start_time=start, limit=5000)
    if not decisions:
        raise HTTPException(status_code=404, detail="Agent not found or no data")

    confs = [d.confidence for d in decisions if d.confidence is not None]
    lats = [d.latency_ms for d in decisions if d.latency_ms is not None]
    return AgentSummaryOut(
        agent_id=agent_id,
        total_decisions=len(decisions),
        avg_confidence=statistics.mean(confs) if confs else None,
        avg_latency_ms=statistics.mean(lats) if lats else None,
        success_rate=None,
        total_cost_usd=sum(d.total_cost_usd for d in decisions),
        total_tokens=sum(d.total_tokens for d in decisions),
        total_llm_calls=sum(d.llm_calls for d in decisions),
    )


@router.get("/{agent_id}/drift", response_model=DriftResultOut)
async def get_drift(
    agent_id: str,
    store: Store,
    window_hours: int = Query(24, ge=1, le=168),
    baseline_days: int = Query(7, ge=1, le=30),
    threshold: float = Query(0.10, ge=0.01, le=0.50),
) -> DriftResultOut:
    """Run confidence drift detection for an agent."""
    decisions = store.query_decisions(agent_id=agent_id, limit=10000)
    if not decisions:
        raise HTTPException(status_code=404, detail="No data for agent")

    detector = DriftDetector(
        baseline_window_days=baseline_days,
        detection_window_hours=window_hours,
        drift_threshold=threshold,
    )
    for d in decisions:
        if d.confidence is not None:
            detector.record_confidence(
                agent_id=agent_id,
                confidence=d.confidence,
                timestamp=d.timestamp,
            )

    result = detector.detect_drift(agent_id=agent_id, window_hours=window_hours)
    return DriftResultOut(**result)


@router.get("/{agent_id}/confidence-timeline")
async def get_confidence_timeline(
    agent_id: str,
    store: Store,
    hours: int = Query(24, ge=1, le=720),
    bucket_minutes: int = Query(60, ge=5, le=1440),
) -> list[dict]:
    """Return confidence bucketed over time for sparkline/chart rendering."""
    start = datetime.utcnow() - timedelta(hours=hours)
    decisions = store.query_decisions(agent_id=agent_id, start_time=start, limit=10000)

    if not decisions:
        return []

    # Build time buckets
    bucket_secs = bucket_minutes * 60
    buckets: dict[int, list[float]] = {}
    for d in decisions:
        if d.confidence is None:
            continue
        bucket_key = int(d.timestamp.timestamp() // bucket_secs) * bucket_secs
        buckets.setdefault(bucket_key, []).append(d.confidence)

    return [
        {
            "timestamp": datetime.utcfromtimestamp(ts).isoformat(),
            "avg_confidence": statistics.mean(vals),
            "min_confidence": min(vals),
            "max_confidence": max(vals),
            "sample_count": len(vals),
        }
        for ts, vals in sorted(buckets.items())
    ]

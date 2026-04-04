"""Conflicts router — multi-agent conflict analytics.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import sqlite3
import statistics
from collections import Counter
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from agentability.storage.sqlite_store import SQLiteStore
from agentability.utils.serialization import deserialize_data

from ..dependencies import get_store
from ..schemas import ConflictHotspotOut, ConflictOut

router = APIRouter(prefix="/api/conflicts", tags=["conflicts"])

Store = Annotated[SQLiteStore, Depends(get_store)]


def _row_to_conflict(row: sqlite3.Row) -> ConflictOut:
    from uuid import UUID
    return ConflictOut(
        conflict_id=UUID(row["conflict_id"]),
        session_id=row["session_id"],
        timestamp=datetime.fromisoformat(row["timestamp"]),
        conflict_type=row["conflict_type"],
        involved_agents=deserialize_data(row["involved_agents"]) if row["involved_agents"] else [],
        severity=float(row["severity"]),
        resolved=bool(row["resolved"]),
        resolution_strategy=row["resolution_strategy"],
        resolution_outcome=row["resolution_outcome"],
        resolution_time_ms=row["resolution_time_ms"],
    )


@router.get("", response_model=list[ConflictOut])
async def list_conflicts(
    store: Store,
    session_id: str | None = Query(None),
    hours: int = Query(24, ge=1, le=720),
    min_severity: float = Query(0.0, ge=0.0, le=1.0),
    limit: int = Query(100, ge=1, le=500),
) -> list[ConflictOut]:
    """List recent conflicts with optional filters."""
    since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    sql = "SELECT * FROM conflicts WHERE timestamp >= ? AND severity >= ?"
    params: list = [since, min_severity]
    if session_id:
        sql += " AND session_id = ?"
        params.append(session_id)
    sql += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    cur = store.conn.cursor()
    cur.execute(sql, params)
    return [_row_to_conflict(r) for r in cur.fetchall()]


@router.get("/hotspots", response_model=list[ConflictHotspotOut])
async def get_hotspots(
    store: Store,
    hours: int = Query(168, ge=1, le=720),
    top_n: int = Query(10, ge=1, le=50),
) -> list[ConflictHotspotOut]:
    """Return agent pairs with the most conflicts (conflict hotspot map)."""
    since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    cur = store.conn.cursor()
    cur.execute(
        "SELECT involved_agents, severity FROM conflicts WHERE timestamp >= ?",
        (since,),
    )
    rows = cur.fetchall()

    pair_counts: Counter = Counter()
    pair_severity: dict[tuple, list[float]] = {}

    for row in rows:
        agents = deserialize_data(row["involved_agents"]) if row["involved_agents"] else []
        agents_sorted = sorted(agents)
        if len(agents_sorted) < 2:
            continue
        pair = (agents_sorted[0], agents_sorted[1])
        pair_counts[pair] += 1
        pair_severity.setdefault(pair, []).append(float(row["severity"]))

    hotspots: list[ConflictHotspotOut] = []
    for pair, count in pair_counts.most_common(top_n):
        sevs = pair_severity[pair]
        hotspots.append(
            ConflictHotspotOut(
                agents=list(pair),
                conflict_count=count,
                avg_severity=statistics.mean(sevs),
                win_rates={},
            )
        )
    return hotspots


@router.get("/timeline")
async def get_conflict_timeline(
    store: Store,
    hours: int = Query(24, ge=1, le=720),
    bucket_minutes: int = Query(60, ge=5, le=1440),
) -> list[dict]:
    """Return conflict counts bucketed over time."""
    since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    cur = store.conn.cursor()
    cur.execute(
        "SELECT timestamp, severity FROM conflicts WHERE timestamp >= ?",
        (since,),
    )
    rows = cur.fetchall()

    bucket_secs = bucket_minutes * 60
    buckets: dict[int, dict] = {}
    for row in rows:
        ts = datetime.fromisoformat(row["timestamp"]).timestamp()
        key = int(ts // bucket_secs) * bucket_secs
        b = buckets.setdefault(key, {"count": 0, "severities": []})
        b["count"] += 1
        b["severities"].append(float(row["severity"]))

    return [
        {
            "timestamp": datetime.utcfromtimestamp(k).isoformat(),
            "count": v["count"],
            "avg_severity": statistics.mean(v["severities"]),
        }
        for k, v in sorted(buckets.items())
    ]


@router.get("/summary")
async def get_conflict_summary(
    store: Store,
    hours: int = Query(24, ge=1, le=720),
) -> dict:
    """Overview stats for the conflicts page header cards."""
    since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    cur = store.conn.cursor()
    cur.execute(
        "SELECT severity, resolved, conflict_type FROM conflicts WHERE timestamp >= ?",
        (since,),
    )
    rows = cur.fetchall()
    if not rows:
        return {"total": 0, "resolved": 0, "unresolved": 0, "avg_severity": 0.0, "by_type": {}}

    sevs = [float(r["severity"]) for r in rows]
    by_type: Counter = Counter(r["conflict_type"] for r in rows)
    resolved = sum(1 for r in rows if r["resolved"])

    return {
        "total": len(rows),
        "resolved": resolved,
        "unresolved": len(rows) - resolved,
        "avg_severity": statistics.mean(sevs),
        "by_type": dict(by_type),
    }

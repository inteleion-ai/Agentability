"""Alerts router — active drift and policy violation alerts.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from agentability.analyzers.drift_detector import DriftDetector, DriftSeverity
from agentability.storage.sqlite_store import SQLiteStore

from ..dependencies import get_store

router = APIRouter(prefix="/api/alerts", tags=["alerts"])
Store = Annotated[SQLiteStore, Depends(get_store)]


@router.get("")
async def list_alerts(
    store: Store,
    hours: int = Query(24, ge=1, le=720),
    severity: str = Query("low", description="Minimum severity: low|medium|high|critical"),
    limit: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    """Return active drift and constraint-violation alerts.

    Builds a DriftDetector from recent decisions and returns alerts
    for all agents that exceed the severity threshold.
    """
    severity_map = {
        "low": DriftSeverity.LOW,
        "medium": DriftSeverity.MEDIUM,
        "high": DriftSeverity.HIGH,
        "critical": DriftSeverity.CRITICAL,
    }
    min_severity = severity_map.get(severity.lower(), DriftSeverity.LOW)

    # Pull recent decisions and feed into DriftDetector
    decisions = store.query_decisions(limit=2000)

    # Build agent-keyed confidence history
    detector = DriftDetector(
        baseline_window_days=7,
        detection_window_hours=hours,
        drift_threshold=0.05,
    )

    for d in decisions:
        if d.confidence is not None:
            detector.record_confidence(
                agent_id=d.agent_id,
                confidence=d.confidence,
                timestamp=d.timestamp,
            )

    # Detect drift per agent
    agent_ids = {d.agent_id for d in decisions}
    drift_alerts = []
    for agent_id in agent_ids:
        result = detector.detect_drift(agent_id)
        if result.get("drift_detected") and result.get("severity", "none") != "none":
            severity_val = result.get("severity", "low")
            severity_enum = severity_map.get(severity_val, DriftSeverity.LOW)
            severity_order = {
                DriftSeverity.LOW: 1, DriftSeverity.MEDIUM: 2,
                DriftSeverity.HIGH: 3, DriftSeverity.CRITICAL: 4,
            }
            if severity_order.get(severity_enum, 0) >= severity_order.get(min_severity, 1):
                drift_alerts.append({
                    "type": "confidence_drift",
                    "agent_id": agent_id,
                    "severity": severity_val,
                    "current_confidence": result.get("current_confidence"),
                    "baseline_confidence": result.get("baseline_confidence"),
                    "drift_magnitude": result.get("drift_magnitude"),
                    "recommendation": result.get("recommendation"),
                    "detected_at": datetime.utcnow().isoformat(),
                })

    # Constraint violation alerts from recent decisions
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    violation_alerts = []
    for d in decisions:
        if d.timestamp >= cutoff and d.constraints_violated:
            violation_alerts.append({
                "type": "constraint_violation",
                "agent_id": d.agent_id,
                "decision_id": str(d.decision_id),
                "severity": "high" if len(d.constraints_violated) >= 2 else "medium",
                "violations": d.constraints_violated,
                "confidence": d.confidence,
                "timestamp": d.timestamp.isoformat(),
            })

    all_alerts = sorted(
        drift_alerts + violation_alerts[:limit],
        key=lambda a: a.get("detected_at", a.get("timestamp", "")),
        reverse=True,
    )[:limit]

    return {
        "total": len(all_alerts),
        "drift_alerts": len(drift_alerts),
        "violation_alerts": len(violation_alerts),
        "items": all_alerts,
        "window_hours": hours,
        "generated_at": datetime.utcnow().isoformat(),
    }

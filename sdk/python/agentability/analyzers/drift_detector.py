"""Confidence drift detector - catches regressions BEFORE they become incidents.

This is THE critical monitoring feature that makes AGENTABILITY non-optional
for production teams. Detects when agent performance degrades after deployments,
prompt changes, or model updates.

Copyright (c) 2026 Agentability
Licensed under MIT License
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


class DriftSeverity(Enum):
    """Severity levels for confidence drift."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DriftAlert:
    """Alert for detected confidence drift.

    Attributes:
        alert_id: Unique identifier.
        agent_id: Affected agent.
        severity: How serious the drift is.
        current_confidence: Recent average confidence.
        baseline_confidence: Historical baseline.
        drift_magnitude: Percentage drop (negative) or increase (positive).
        detection_time: When drift was detected.
        affected_decisions: Number of decisions analyzed.
        recommendation: What to do about it.
        metadata: Additional context.
    """

    alert_id: str
    agent_id: str
    severity: DriftSeverity
    current_confidence: float
    baseline_confidence: float
    drift_magnitude: float
    detection_time: datetime
    affected_decisions: int
    recommendation: str
    metadata: dict[str, Any] = field(default_factory=dict)


class DriftDetector:
    """Detects confidence drift in agent decisions over time.

    Detection Methods:
        - Moving average comparison (simple, fast)
        - Z-score anomaly detection (statistical)
        - Sequential change detection (CUSUM)
        - Threshold violation tracking

    Example Usage:
        >>> detector = DriftDetector()
        >>> for decision in recent_decisions:
        ...     detector.record_confidence(
        ...         agent_id=decision.agent_id,
        ...         confidence=decision.confidence,
        ...         timestamp=decision.timestamp,
        ...         version=decision.version
        ...     )
        >>> drift = detector.detect_drift(agent_id="risk_agent", window_hours=24)
        >>> if drift["drift_detected"]:
        ...     print(f"Severity: {drift['severity']}")
    """

    def __init__(
        self,
        baseline_window_days: int = 7,
        detection_window_hours: int = 24,
        drift_threshold: float = 0.10,
    ):
        """Initialize the drift detector.

        Args:
            baseline_window_days: Days of history for baseline.
            detection_window_hours: Recent window to check for drift.
            drift_threshold: Minimum change to trigger alert (0.10 = 10%).
        """
        self.baseline_window_days = baseline_window_days
        self.detection_window_hours = detection_window_hours
        self.drift_threshold = drift_threshold

        # Storage: agent_id -> list of (timestamp, confidence, version, metadata)
        self.confidence_history: dict[str, list[tuple]] = {}
        self.alerts: list[DriftAlert] = []

    def record_confidence(
        self,
        agent_id: str,
        confidence: float,
        timestamp: datetime | None = None,
        version: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record a confidence score for drift tracking.

        Args:
            agent_id: Agent identifier.
            confidence: Confidence score (0-1).
            timestamp: When this decision was made.
            version: Agent/model version.
            metadata: Additional context (deployment, prompt_hash, etc).
        """
        if agent_id not in self.confidence_history:
            self.confidence_history[agent_id] = []

        self.confidence_history[agent_id].append(
            (timestamp or datetime.now(), confidence, version, metadata or {})
        )

    def detect_drift(
        self,
        agent_id: str,
        window_hours: int | None = None,
    ) -> dict[str, Any]:
        """Detect if agent confidence has drifted.

        Args:
            agent_id: Agent to check.
            window_hours: Recent window to analyze (uses default if None).

        Returns:
            Dictionary containing drift_detected, severity, magnitudes, etc.
        """
        if agent_id not in self.confidence_history:
            return {"drift_detected": False, "error": "No data for agent"}

        history = self.confidence_history[agent_id]
        if len(history) < 10:
            return {"drift_detected": False, "error": "Insufficient data"}

        window_hours = window_hours or self.detection_window_hours
        now = datetime.now()

        baseline_cutoff = now - timedelta(days=self.baseline_window_days)
        recent_cutoff = now - timedelta(hours=window_hours)

        baseline_scores = [
            conf
            for ts, conf, _, _ in history
            if baseline_cutoff <= ts < recent_cutoff
        ]
        recent_scores = [
            conf for ts, conf, _, _ in history if ts >= recent_cutoff
        ]

        if not baseline_scores or not recent_scores:
            return {
                "drift_detected": False,
                "error": "Insufficient data in windows",
            }

        baseline_avg = statistics.mean(baseline_scores)
        recent_avg = statistics.mean(recent_scores)
        drift_magnitude = (recent_avg - baseline_avg) / baseline_avg

        drift_detected = abs(drift_magnitude) >= self.drift_threshold
        severity = self._calculate_severity(drift_magnitude)
        recommendation = self._generate_recommendation(
            drift_magnitude, severity, agent_id, history
        )
        timeline = self._build_timeline(history, recent_cutoff)

        result: dict[str, Any] = {
            "drift_detected": drift_detected,
            "severity": severity.value,
            "agent_id": agent_id,
            "current_confidence": recent_avg,
            "baseline_confidence": baseline_avg,
            "drift_magnitude": drift_magnitude,
            "current_stddev": (
                statistics.stdev(recent_scores) if len(recent_scores) > 1 else 0
            ),
            "baseline_stddev": (
                statistics.stdev(baseline_scores)
                if len(baseline_scores) > 1
                else 0
            ),
            "recent_samples": len(recent_scores),
            "baseline_samples": len(baseline_scores),
            "recommendation": recommendation,
            "timeline": timeline,
        }

        if drift_detected:
            alert = DriftAlert(
                alert_id=f"drift_{agent_id}_{now.isoformat()}",
                agent_id=agent_id,
                severity=severity,
                current_confidence=recent_avg,
                baseline_confidence=baseline_avg,
                drift_magnitude=drift_magnitude,
                detection_time=now,
                affected_decisions=len(recent_scores),
                recommendation=recommendation,
            )
            self.alerts.append(alert)

        return result

    def detect_version_impact(
        self,
        agent_id: str,
        version: str,
    ) -> dict[str, Any]:
        """Detect if a specific version caused performance change.

        Args:
            agent_id: Agent to analyze.
            version: Version identifier to check.
        """
        if agent_id not in self.confidence_history:
            return {"error": "No data for agent"}

        history = self.confidence_history[agent_id]

        with_version = [conf for _, conf, v, _ in history if v == version]
        without_version = [
            conf for _, conf, v, _ in history if v != version and v is not None
        ]

        if not with_version or not without_version:
            return {"error": "Insufficient data for comparison"}

        version_avg = statistics.mean(with_version)
        other_avg = statistics.mean(without_version)
        impact = (version_avg - other_avg) / other_avg

        return {
            "version": version,
            "version_confidence": version_avg,
            "other_versions_confidence": other_avg,
            "impact": impact,
            "impact_percentage": impact * 100,
            "samples_with_version": len(with_version),
            "samples_without_version": len(without_version),
            "regression": impact < -0.05,
            "improvement": impact > 0.05,
        }

    def get_trend(
        self,
        agent_id: str,
        days: int = 7,
    ) -> dict[str, Any]:
        """Get confidence trend over time.

        Args:
            agent_id: Agent to analyze.
            days: Number of days to analyze.
        """
        if agent_id not in self.confidence_history:
            return {"error": "No data for agent"}

        history = self.confidence_history[agent_id]
        cutoff = datetime.now() - timedelta(days=days)
        recent_history = [
            (ts, conf) for ts, conf, _, _ in history if ts >= cutoff
        ]

        if len(recent_history) < 5:
            return {"error": "Insufficient data for trend"}

        confidences = [conf for _, conf in recent_history]
        trend_direction = "stable"

        if len(confidences) >= 10:
            mid = len(confidences) // 2
            first_half = statistics.mean(confidences[:mid])
            second_half = statistics.mean(confidences[mid:])
            change = (second_half - first_half) / first_half

            if change < -0.05:
                trend_direction = "declining"
            elif change > 0.05:
                trend_direction = "improving"

        return {
            "trend_direction": trend_direction,
            "current_confidence": confidences[-1] if confidences else None,
            "average_confidence": statistics.mean(confidences),
            "min_confidence": min(confidences),
            "max_confidence": max(confidences),
            "volatility": (
                statistics.stdev(confidences) if len(confidences) > 1 else 0
            ),
            "data_points": len(confidences),
        }

    def get_active_alerts(
        self,
        severity_threshold: DriftSeverity | None = None,
    ) -> list[DriftAlert]:
        """Get all active drift alerts.

        Args:
            severity_threshold: Minimum severity to include.
        """
        if severity_threshold is None:
            return self.alerts

        severity_order: dict[DriftSeverity, int] = {
            DriftSeverity.NONE: 0,
            DriftSeverity.LOW: 1,
            DriftSeverity.MEDIUM: 2,
            DriftSeverity.HIGH: 3,
            DriftSeverity.CRITICAL: 4,
        }
        min_level = severity_order[severity_threshold]
        return [
            alert
            for alert in self.alerts
            if severity_order[alert.severity] >= min_level
        ]

    def _calculate_severity(self, drift_magnitude: float) -> DriftSeverity:
        abs_drift = abs(drift_magnitude)
        if abs_drift >= 0.20:
            return DriftSeverity.CRITICAL
        elif abs_drift >= 0.15:
            return DriftSeverity.HIGH
        elif abs_drift >= 0.10:
            return DriftSeverity.MEDIUM
        elif abs_drift >= 0.05:
            return DriftSeverity.LOW
        else:
            return DriftSeverity.NONE

    def _generate_recommendation(
        self,
        drift_magnitude: float,
        severity: DriftSeverity,
        agent_id: str,
        history: list[tuple],
    ) -> str:
        if severity == DriftSeverity.NONE:
            return "No action needed - performance is stable"

        recent = sorted(history, key=lambda x: x[0], reverse=True)[:10]
        versions = {v for _, _, v, _ in recent if v is not None}

        if drift_magnitude < 0:
            if len(versions) > 1:
                return (
                    f"CRITICAL: Confidence dropped {abs(drift_magnitude):.1%}. "
                    "Review recent deployment/version change. "
                    "Consider rollback to previous version."
                )
            return (
                f"Confidence dropped {abs(drift_magnitude):.1%}. "
                "Investigate: (1) Data quality, (2) Prompt changes, "
                "(3) Model behavior. Check recent decisions for patterns."
            )
        return (
            f"Confidence improved by {drift_magnitude:.1%}. "
            "Monitor to ensure improvement is stable, not a data anomaly."
        )

    def detect_drift_cusum(
        self,
        agent_id: str,
        target: float | None = None,
        slack: float = 0.5,
        threshold: float = 5.0,
    ) -> dict[str, Any]:
        """CUSUM (Cumulative Sum) sequential change-point detection.

        CUSUM is more sensitive than moving-average comparison for detecting
        *gradual* drift — it accumulates small deviations over time and fires
        when the cumulative sum exceeds a threshold.

        Args:
            agent_id: Agent to monitor.
            target: Expected mean confidence. Defaults to the overall mean
                of the agent's full history (auto-calibrating baseline).
            slack: Allowable deviation from target before accumulating
                (typically 0.5 * expected_std_dev).
            threshold: Decision boundary — alert fires when CUSUM exceeds
                this value. Higher = fewer false positives.

        Returns:
            dict with keys:
                change_detected (bool), change_point_index (int|None),
                cusum_values (list[float]), severity (str),
                direction (str: 'downward'|'upward'|'none'),
                recommendation (str).

        References:
            E.S. Page (1954). "Continuous inspection schemes."
            Biometrika, 41(1-2), 100-115.
        """
        if agent_id not in self.confidence_history:
            return {"change_detected": False, "error": "No data for agent"}

        history = self.confidence_history[agent_id]
        if len(history) < 15:
            return {
                "change_detected": False,
                "error": "Insufficient data — need at least 15 observations",
            }

        scores = [conf for _, conf, _, _ in sorted(history, key=lambda x: x[0])]
        mu = target if target is not None else sum(scores) / len(scores)

        # Two-sided CUSUM: S_high detects upward shifts, S_low detects downward
        s_high: list[float] = [0.0]
        s_low: list[float] = [0.0]
        cusum_combined: list[float] = [0.0]
        change_point: int | None = None
        direction = "none"

        for i, x in enumerate(scores[1:], start=1):
            s_h = max(0.0, s_high[-1] + (x - mu) - slack)
            s_l = max(0.0, s_low[-1] + (mu - x) - slack)
            s_high.append(s_h)
            s_low.append(s_l)
            cusum_combined.append(max(s_h, s_l))

            # First crossing of threshold marks the change point
            if change_point is None:
                if s_l > threshold:
                    change_point = i
                    direction = "downward"
                elif s_h > threshold:
                    change_point = i
                    direction = "upward"

        change_detected = change_point is not None
        max_cusum = max(cusum_combined)
        severity = (
            "critical" if max_cusum > threshold * 2
            else "high" if max_cusum > threshold * 1.5
            else "medium" if max_cusum > threshold
            else "low" if max_cusum > threshold * 0.7
            else "none"
        )

        if change_detected and direction == "downward":
            recommendation = (
                f"CUSUM detected a sustained downward confidence shift starting "
                f"at observation {change_point}. "
                "Review: (1) recent prompt or model changes, "
                "(2) data quality degradation, (3) concept drift in inputs."
            )
        elif change_detected and direction == "upward":
            recommendation = (
                f"CUSUM detected a sustained upward confidence shift at "
                f"observation {change_point}. Verify improvement is genuine "
                "and not a calibration artifact."
            )
        else:
            recommendation = "No sustained change detected — performance is stable."

        return {
            "change_detected": change_detected,
            "change_point_index": change_point,
            "direction": direction,
            "severity": severity,
            "cusum_high": s_high,
            "cusum_low": s_low,
            "cusum_values": cusum_combined,
            "max_cusum": max_cusum,
            "threshold": threshold,
            "target_mean": mu,
            "observations": len(scores),
            "recommendation": recommendation,
        }

    def _build_timeline(
        self,
        history: list[tuple],
        cutoff: datetime,
    ) -> list[dict[str, Any]]:
        relevant = [
            (ts, conf)
            for ts, conf, _, _ in history
            if ts >= cutoff - timedelta(hours=24)
        ]
        relevant.sort(key=lambda x: x[0])
        return [
            {
                "timestamp": ts.isoformat(),
                "confidence": conf,
                "is_recent": ts >= cutoff,
            }
            for ts, conf in relevant
        ]

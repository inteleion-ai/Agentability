"""Decision quality metrics tracking.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class DecisionType(Enum):
    CLASSIFICATION = "classification"
    RANKING = "ranking"
    GENERATION = "generation"
    EXTRACTION = "extraction"
    PLANNING = "planning"
    TOOL_SELECTION = "tool_selection"
    ROUTING = "routing"
    VALIDATION = "validation"


@dataclass
class DecisionMetric:
    """Lightweight record of a single tracked decision."""

    decision_id: str
    agent_id: str
    decision_type: DecisionType
    timestamp: datetime
    latency_ms: float
    confidence: float
    success: bool | None = None
    reasoning_steps: int = 0
    tool_calls: int = 0
    tokens_used: int = 0
    cost_usd: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class DecisionMetricsCollector:
    """Collects and aggregates decision metrics for a single agent.

    Example:
        >>> collector = DecisionMetricsCollector(agent_id="risk_agent")
        >>> with collector.track_decision("classification") as ctx:
        ...     ctx.set_confidence(0.85)
        ...     ctx.set_success(True)
    """

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id
        self._decisions: list[DecisionMetric] = []

    @property
    def decisions(self) -> list[DecisionMetric]:
        return list(self._decisions)

    def track_decision(
        self,
        decision_type: str,
        decision_id: str | None = None,
    ) -> DecisionContext:
        """Return a context manager for one decision."""
        if decision_id is None:
            decision_id = f"{self.agent_id}_{int(time.time() * 1000)}"
        return DecisionContext(
            collector=self,
            decision_id=decision_id,
            decision_type=DecisionType(decision_type),
        )

    def record_decision(self, metric: DecisionMetric) -> None:
        self._decisions.append(metric)

    def get_success_rate(
        self,
        decision_type: DecisionType | None = None,
        time_window_hours: int | None = None,
    ) -> float:
        decisions = self._filter(decision_type, time_window_hours)
        with_outcome = [d for d in decisions if d.success is not None]
        if not with_outcome:
            return 0.0
        return sum(1 for d in with_outcome if d.success) / len(with_outcome)

    def get_avg_confidence(
        self,
        decision_type: DecisionType | None = None,
        time_window_hours: int | None = None,
    ) -> float:
        decisions = self._filter(decision_type, time_window_hours)
        if not decisions:
            return 0.0
        return statistics.mean(d.confidence for d in decisions)

    def get_latency_percentiles(
        self,
        decision_type: DecisionType | None = None,
        time_window_hours: int | None = None,
    ) -> dict[str, float]:
        decisions = self._filter(decision_type, time_window_hours)
        if not decisions:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0}
        latencies = sorted(d.latency_ms for d in decisions)
        n = len(latencies)
        return {
            "p50": latencies[int(n * 0.50)],
            "p95": latencies[min(int(n * 0.95), n - 1)],
            "p99": latencies[min(int(n * 0.99), n - 1)],
        }

    def get_cost_analysis(
        self,
        decision_type: DecisionType | None = None,
        time_window_hours: int | None = None,
    ) -> dict[str, Any]:
        decisions = self._filter(decision_type, time_window_hours)
        if not decisions:
            return {
                "total_cost_usd": 0.0,
                "avg_cost_per_decision": 0.0,
                "total_tokens": 0,
                "avg_tokens_per_decision": 0.0,
                "decisions_count": 0,
            }
        total_cost = sum(d.cost_usd for d in decisions)
        total_tokens = sum(d.tokens_used for d in decisions)
        return {
            "total_cost_usd": total_cost,
            "avg_cost_per_decision": total_cost / len(decisions),
            "total_tokens": total_tokens,
            "avg_tokens_per_decision": total_tokens / len(decisions),
            "decisions_count": len(decisions),
        }

    def _filter(
        self,
        decision_type: DecisionType | None,
        time_window_hours: int | None,
    ) -> list[DecisionMetric]:
        result = self._decisions
        if decision_type:
            result = [d for d in result if d.decision_type == decision_type]
        if time_window_hours:
            cutoff = datetime.now().timestamp() - time_window_hours * 3600
            result = [d for d in result if d.timestamp.timestamp() > cutoff]
        return result


class DecisionContext:
    """Context manager that measures one decision and records it."""

    def __init__(
        self,
        collector: DecisionMetricsCollector,
        decision_id: str,
        decision_type: DecisionType,
    ) -> None:
        self._collector = collector
        self.decision_id = decision_id
        self.decision_type = decision_type
        self._start: float | None = None
        self.confidence: float = 0.0
        self.success: bool | None = None
        self.reasoning_steps: int = 0
        self.tool_calls: int = 0
        self.tokens_used: int = 0
        self.cost_usd: float = 0.0
        self.metadata: dict[str, Any] = {}

    def __enter__(self) -> DecisionContext:
        self._start = time.time()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        latency_ms = (time.time() - (self._start or time.time())) * 1000
        self._collector.record_decision(
            DecisionMetric(
                decision_id=self.decision_id,
                agent_id=self._collector.agent_id,
                decision_type=self.decision_type,
                timestamp=datetime.now(),
                latency_ms=latency_ms,
                confidence=self.confidence,
                success=self.success,
                reasoning_steps=self.reasoning_steps,
                tool_calls=self.tool_calls,
                tokens_used=self.tokens_used,
                cost_usd=self.cost_usd,
                metadata=self.metadata,
            )
        )

    def set_confidence(self, confidence: float) -> None:
        self.confidence = max(0.0, min(1.0, confidence))

    def set_success(self, success: bool) -> None:
        self.success = success

    def add_reasoning_step(self) -> None:
        self.reasoning_steps += 1

    def add_tool_call(self) -> None:
        self.tool_calls += 1

    def add_tokens(self, count: int) -> None:
        self.tokens_used += count

    def add_cost(self, cost: float) -> None:
        self.cost_usd += cost

    def set_metadata(self, key: str, value: Any) -> None:
        self.metadata[key] = value

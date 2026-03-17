"""Working memory tracking for current context.

Tracks active context, attention mechanisms, and context window management.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any


@dataclass
class WorkingMemoryMetric:
    """Metrics for working memory state.

    Attributes:
        metric_id: Unique identifier.
        agent_id: Agent ID.
        timestamp: When measured.
        active_items_count: Number of items in working memory.
        total_tokens: Total tokens in context.
        max_tokens: Maximum context capacity.
        utilization: Percentage of capacity used.
        attention_distribution: Distribution of attention weights.
        items_added: Items added this update.
        items_removed: Items removed this update.
        metadata: Additional metadata.
    """

    metric_id: str
    agent_id: str
    timestamp: datetime
    active_items_count: int
    total_tokens: int
    max_tokens: int
    utilization: float
    attention_distribution: dict[str, float] = field(default_factory=dict)
    items_added: int = 0
    items_removed: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class WorkingMemoryTracker:
    """Tracks working memory performance and utilization."""

    def __init__(self, agent_id: str, max_tokens: int = 4096):
        self.agent_id = agent_id
        self.max_tokens = max_tokens
        self.metrics: list[WorkingMemoryMetric] = []

    def record_state(
        self,
        active_items: int,
        total_tokens: int,
        attention_dist: dict[str, float] | None = None,
        items_added: int = 0,
        items_removed: int = 0,
    ) -> None:
        """Record current working memory state."""
        metric = WorkingMemoryMetric(
            metric_id=f"{self.agent_id}_wm_{len(self.metrics)}",
            agent_id=self.agent_id,
            timestamp=datetime.now(),
            active_items_count=active_items,
            total_tokens=total_tokens,
            max_tokens=self.max_tokens,
            utilization=(
                total_tokens / self.max_tokens if self.max_tokens > 0 else 0.0
            ),
            attention_distribution=attention_dist or {},
            items_added=items_added,
            items_removed=items_removed,
        )
        self.metrics.append(metric)

    def get_avg_utilization(
        self, time_window_hours: int | None = None
    ) -> float:
        """Get average context utilization."""
        metrics = self._filter_metrics(time_window_hours)
        if not metrics:
            return 0.0
        return statistics.mean(m.utilization for m in metrics)

    def get_peak_utilization(
        self, time_window_hours: int | None = None
    ) -> float:
        """Get peak context utilization."""
        metrics = self._filter_metrics(time_window_hours)
        if not metrics:
            return 0.0
        return max(m.utilization for m in metrics)

    def _filter_metrics(
        self, time_window_hours: int | None
    ) -> list[WorkingMemoryMetric]:
        if not time_window_hours:
            return self.metrics
        cutoff = datetime.now() - timedelta(hours=time_window_hours)
        return [m for m in self.metrics if m.timestamp > cutoff]

"""Episodic memory tracking for sequential experiences.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any


@dataclass
class EpisodicRetrievalMetric:
    """Metrics for one episodic memory retrieval."""

    operation_id: str
    agent_id: str
    timestamp: datetime
    latency_ms: float
    time_range_start: datetime | None = None
    time_range_end: datetime | None = None
    episodes_retrieved: int = 0
    temporal_coherence: float = 1.0
    context_tokens_used: int = 0
    context_tokens_limit: int = 4096
    context_utilization: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class EpisodicMemoryTracker:
    """Track episodic memory performance for one agent."""

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id
        self.operations: list[EpisodicRetrievalMetric] = []

    def track_retrieval(self) -> EpisodicRetrievalContext:
        """Return a context manager for one episodic retrieval."""
        operation_id = f"{self.agent_id}_ep_{len(self.operations)}"
        return EpisodicRetrievalContext(self, operation_id)

    def record_operation(self, metric: EpisodicRetrievalMetric) -> None:
        """Persist a completed metric."""
        self.operations.append(metric)

    def get_avg_context_utilization(
        self, time_window_hours: int | None = None
    ) -> float:
        """Return mean context-window utilisation."""
        ops = self._filter(time_window_hours)
        if not ops:
            return 0.0
        return statistics.mean(op.context_utilization for op in ops)

    def _filter(
        self, time_window_hours: int | None
    ) -> list[EpisodicRetrievalMetric]:
        if not time_window_hours:
            return self.operations
        cutoff = datetime.now() - timedelta(hours=time_window_hours)
        return [op for op in self.operations if op.timestamp > cutoff]


class EpisodicRetrievalContext:
    """Context manager for timing one episodic retrieval."""

    def __init__(
        self, tracker: EpisodicMemoryTracker, operation_id: str
    ) -> None:
        self._tracker = tracker
        self._operation_id = operation_id
        self._start: float | None = None
        self._episodes: list[Any] = []
        self.context_tokens_used: int = 0
        self.context_tokens_limit: int = 4096

    def __enter__(self) -> EpisodicRetrievalContext:
        self._start = time.time()
        return self

    def __exit__(
        self,
        exc_type: Any,
        exc_val: Any,
        exc_tb: Any,
    ) -> None:
        latency_ms = (time.time() - (self._start or time.time())) * 1000
        metric = EpisodicRetrievalMetric(
            operation_id=self._operation_id,
            agent_id=self._tracker.agent_id,
            timestamp=datetime.now(),
            latency_ms=latency_ms,
            episodes_retrieved=len(self._episodes),
            context_tokens_used=self.context_tokens_used,
            context_tokens_limit=self.context_tokens_limit,
            context_utilization=(
                self.context_tokens_used / self.context_tokens_limit
                if self.context_tokens_limit > 0
                else 0.0
            ),
        )
        self._tracker.record_operation(metric)

    def record_episodes(self, episodes: list[Any], tokens_used: int) -> None:
        """Record retrieved episodes and token count."""
        self._episodes = episodes
        self.context_tokens_used = tokens_used

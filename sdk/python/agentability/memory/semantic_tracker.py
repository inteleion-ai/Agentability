"""Semantic memory tracking for knowledge graphs.

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
class SemanticRetrievalMetric:
    """Metrics for one semantic (knowledge-graph) query."""

    operation_id: str
    agent_id: str
    timestamp: datetime
    latency_ms: float
    knowledge_graph_nodes: int
    relationships_traversed: int
    max_hop_distance: int
    graph_density: float
    query_complexity: int
    results_returned: int
    metadata: dict[str, Any] = field(default_factory=dict)


class SemanticMemoryTracker:
    """Track semantic memory performance for one agent."""

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id
        self.operations: list[SemanticRetrievalMetric] = []

    def track_query(self) -> SemanticQueryContext:
        """Return a context manager for one knowledge-graph query."""
        operation_id = f"{self.agent_id}_sem_{len(self.operations)}"
        return SemanticQueryContext(self, operation_id)

    def record_operation(self, metric: SemanticRetrievalMetric) -> None:
        """Persist a completed metric."""
        self.operations.append(metric)

    def get_avg_query_complexity(
        self, time_window_hours: int | None = None
    ) -> float:
        """Return mean query complexity."""
        ops = self._filter(time_window_hours)
        if not ops:
            return 0.0
        return statistics.mean(op.query_complexity for op in ops)

    def _filter(
        self, time_window_hours: int | None
    ) -> list[SemanticRetrievalMetric]:
        if not time_window_hours:
            return self.operations
        cutoff = datetime.now() - timedelta(hours=time_window_hours)
        return [op for op in self.operations if op.timestamp > cutoff]


class SemanticQueryContext:
    """Context manager for timing one knowledge-graph query."""

    def __init__(
        self, tracker: SemanticMemoryTracker, operation_id: str
    ) -> None:
        self._tracker = tracker
        self._operation_id = operation_id
        self._start: float | None = None
        self._nodes: int = 0
        self._relationships: int = 0
        self._max_hops: int = 0
        self._density: float = 0.0
        self._complexity: int = 1
        self._results: list[Any] = []

    def __enter__(self) -> SemanticQueryContext:
        self._start = time.time()
        return self

    def __exit__(
        self,
        exc_type: Any,
        exc_val: Any,
        exc_tb: Any,
    ) -> None:
        latency_ms = (time.time() - (self._start or time.time())) * 1000
        metric = SemanticRetrievalMetric(
            operation_id=self._operation_id,
            agent_id=self._tracker.agent_id,
            timestamp=datetime.now(),
            latency_ms=latency_ms,
            knowledge_graph_nodes=self._nodes,
            relationships_traversed=self._relationships,
            max_hop_distance=self._max_hops,
            graph_density=self._density,
            query_complexity=self._complexity,
            results_returned=len(self._results),
        )
        self._tracker.record_operation(metric)

    def record_query(
        self,
        nodes: int,
        relationships: int,
        max_hops: int,
        results: list[Any],
        complexity: int = 1,
    ) -> None:
        """Record query details."""
        self._nodes = nodes
        self._relationships = relationships
        self._max_hops = max_hops
        self._complexity = complexity
        self._results = results
        if nodes > 1:
            self._density = relationships / (nodes * (nodes - 1))
        else:
            self._density = 0.0

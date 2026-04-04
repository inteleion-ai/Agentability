"""Memory subsystem metrics collection.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import time
from typing import Any

from agentability.models import MemoryMetrics, MemoryOperation, MemoryType
from agentability.utils.logger import get_logger

logger = get_logger(__name__)


class MemoryMetricsCollector:
    """Factory for :class:`MemoryOperationTracker` instances.

    Example:
        >>> collector = MemoryMetricsCollector(agent_id="rag_agent")
        >>> tracker = collector.start_operation(MemoryType.VECTOR, MemoryOperation.RETRIEVE)
        >>> results = vector_db.search(query, top_k=10)
        >>> metrics = tracker.complete(items_processed=len(results), avg_similarity=0.82)
    """

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id

    def start_operation(
        self,
        memory_type: MemoryType,
        operation: MemoryOperation,
    ) -> MemoryOperationTracker:
        """Begin timing a memory operation."""
        return MemoryOperationTracker(
            agent_id=self.agent_id,
            memory_type=memory_type,
            operation=operation,
        )


class MemoryOperationTracker:
    """Times a single memory operation and produces a :class:`~agentability.models.MemoryMetrics`."""

    def __init__(
        self,
        agent_id: str,
        memory_type: MemoryType,
        operation: MemoryOperation,
    ) -> None:
        self.agent_id = agent_id
        self.memory_type = memory_type
        self.operation = operation
        self._start_time: float = time.time()

    def complete(
        self,
        items_processed: int,
        bytes_processed: int | None = None,
        **kwargs: Any,
    ) -> MemoryMetrics:
        """Stop timing and return a :class:`~agentability.models.MemoryMetrics`."""
        latency_ms = (time.time() - self._start_time) * 1000
        return MemoryMetrics(
            agent_id=self.agent_id,
            memory_type=self.memory_type,
            operation=self.operation,
            latency_ms=latency_ms,
            items_processed=items_processed,
            bytes_processed=bytes_processed,
            **kwargs,
        )


# ---------------------------------------------------------------------------
# Standalone helper functions
# ---------------------------------------------------------------------------


def calculate_retrieval_precision(
    retrieved_items: list[Any],
    relevant_items: list[Any],
) -> float:
    """Compute retrieval precision = |relevant ∩ retrieved| / |retrieved|."""
    if not retrieved_items:
        return 0.0
    overlap = len(set(retrieved_items) & set(relevant_items))
    return overlap / len(retrieved_items)


def calculate_retrieval_recall(
    retrieved_items: list[Any],
    relevant_items: list[Any],
) -> float:
    """Compute retrieval recall = |relevant ∩ retrieved| / |relevant|."""
    if not relevant_items:
        return 0.0
    overlap = len(set(retrieved_items) & set(relevant_items))
    return overlap / len(relevant_items)


def calculate_similarity_stats(similarities: list[float]) -> dict[str, float]:
    """Compute basic statistics for a list of similarity scores."""
    if not similarities:
        return {"avg_similarity": 0.0, "min_similarity": 0.0, "max_similarity": 0.0}
    return {
        "avg_similarity": sum(similarities) / len(similarities),
        "min_similarity": min(similarities),
        "max_similarity": max(similarities),
    }

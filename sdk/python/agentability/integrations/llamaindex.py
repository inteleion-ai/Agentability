"""LlamaIndex auto-instrumentation for Agentability.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import time
from typing import Any

from agentability.models import DecisionType, MemoryOperation, MemoryType
from agentability.tracer import Tracer
from agentability.utils.logger import get_logger

logger = get_logger(__name__)


class LlamaIndexInstrumentation:
    """Instrument LlamaIndex QueryEngine and VectorIndexRetriever.

    Example:
        >>> tracer = Tracer(offline_mode=True)
        >>> instr = LlamaIndexInstrumentation(tracer)
        >>> query_engine = instr.instrument_query_engine(index.as_query_engine())

    Args:
        tracer: Initialised :class:`~agentability.tracer.Tracer`.
        agent_id: Telemetry identifier.
    """

    def __init__(
        self, tracer: Tracer, agent_id: str = "llamaindex_agent"
    ) -> None:
        self.tracer = tracer
        self.agent_id = agent_id

    def instrument_query_engine(self, query_engine: Any) -> Any:
        """Wrap a LlamaIndex QueryEngine."""
        original_query = getattr(query_engine, "query", None)
        if original_query is None:
            logger.warning("Query engine has no 'query' method — skipping.")
            return query_engine

        tracer = self.tracer
        agent_id = self.agent_id

        def _instrumented_query(query_str: str, **kwargs: Any) -> Any:
            start = time.time()
            response = original_query(query_str, **kwargs)
            latency_ms = (time.time() - start) * 1000

            source_nodes: list[Any] = getattr(response, "source_nodes", [])
            raw_scores: list[float] = [
                float(getattr(n, "score", 0.0))
                for n in source_nodes
                if getattr(n, "score", None) is not None
            ]
            avg_similarity: float | None = (
                sum(raw_scores) / len(raw_scores) if raw_scores else None
            )

            # top_k=0 is invalid (MemoryMetrics requires ge=1); pass None when
            # no source nodes are present (e.g. non-RAG query engines).
            top_k: int | None = len(source_nodes) if source_nodes else None

            tracer.record_memory_operation(
                agent_id=agent_id,
                memory_type=MemoryType.VECTOR,
                operation=MemoryOperation.RETRIEVE,
                latency_ms=latency_ms,
                items_processed=len(source_nodes),
                avg_similarity=avg_similarity,
                top_k=top_k,
            )

            with tracer.trace_decision(
                agent_id=agent_id,
                decision_type=DecisionType.RETRIEVAL,
                input_data={"query": query_str[:300]},
            ):
                tracer.record_decision(
                    output={"response": str(response)[:500]},
                    reasoning=["LlamaIndex query engine returned response"],
                    data_sources=["vector_store"],
                )

            return response

        query_engine.query = _instrumented_query
        return query_engine

    def instrument_retriever(self, retriever: Any) -> Any:
        """Wrap a LlamaIndex VectorIndexRetriever."""
        original_retrieve = getattr(retriever, "retrieve", None)
        if original_retrieve is None:
            logger.warning("Retriever has no 'retrieve' method — skipping.")
            return retriever

        tracer = self.tracer
        agent_id = self.agent_id

        def _instrumented_retrieve(query_str: str, **kwargs: Any) -> Any:
            start = time.time()
            nodes = original_retrieve(query_str, **kwargs)
            latency_ms = (time.time() - start) * 1000

            raw_scores: list[float] = [
                float(getattr(n, "score", 0.0))
                for n in (nodes or [])
                if getattr(n, "score", None) is not None
            ]
            avg_similarity: float | None = (
                sum(raw_scores) / len(raw_scores) if raw_scores else None
            )

            tracer.record_memory_operation(
                agent_id=agent_id,
                memory_type=MemoryType.VECTOR,
                operation=MemoryOperation.RETRIEVE,
                latency_ms=latency_ms,
                items_processed=len(nodes or []),
                avg_similarity=avg_similarity,
            )
            return nodes

        retriever.retrieve = _instrumented_retrieve
        return retriever

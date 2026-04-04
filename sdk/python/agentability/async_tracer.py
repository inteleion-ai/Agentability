"""Async-safe tracer for asyncio-based agent systems.

Agentability v0.3.0 — AsyncTracer

The synchronous Tracer uses threading.local() which silently loses context
across await boundaries when multiple coroutines share the same event loop.
AsyncTracer replaces this with contextvars.ContextVar which is await-safe
by design: Python's asyncio runtime copies the context per Task, so each
coroutine gets its own isolated decision state.

Usage::

    from agentability.async_tracer import AsyncTracer
    from agentability.models import DecisionType

    tracer = AsyncTracer(offline_mode=True)

    async def my_agent():
        async with tracer.trace_decision(
            agent_id="rag_agent",
            decision_type=DecisionType.RETRIEVAL,
        ) as ctx:
            result = await fetch_documents(query)
            ctx.set_confidence(0.87)
            tracer.record_decision(output=result)

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import contextlib
import time
from collections.abc import AsyncIterator
from contextvars import ContextVar
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from agentability.models import (
    AgentConflict,
    ConflictType,
    Decision,
    DecisionType,
    LLMMetrics,
    MemoryMetrics,
    MemoryOperation,
    MemoryType,
)
from agentability.storage.sqlite_store import SQLiteStore
from agentability.tracer import TracingContext
from agentability.utils.logger import get_logger

logger = get_logger(__name__)

# ContextVar is the asyncio-safe replacement for threading.local().
# Python copies the current context per asyncio Task, so each coroutine
# automatically gets its own isolated slot — no cross-contamination possible.
_current_decision: ContextVar[dict[str, Any] | None] = ContextVar(
    "agentability_current_decision", default=None
)


class AsyncTracer:
    """Async-safe tracer using contextvars.ContextVar.

    Drop-in replacement for :class:`~agentability.tracer.Tracer` for
    asyncio-based applications. All methods that were synchronous on
    ``Tracer`` remain synchronous here (record_decision, record_llm_call,
    record_memory_operation) — only the ``trace_decision`` context manager
    is async.

    Args:
        offline_mode: Store decisions locally (SQLite). Default True.
        database_path: Path to the SQLite file. Default ``agentability.db``.

    Example::

        import asyncio
        from agentability.async_tracer import AsyncTracer
        from agentability.models import DecisionType

        tracer = AsyncTracer(offline_mode=True)

        async def agent_task(query: str) -> str:
            async with tracer.trace_decision(
                agent_id="my_agent",
                decision_type=DecisionType.GENERATION,
                input_data={"query": query},
            ) as ctx:
                ctx.set_confidence(0.88)
                result = await some_llm_call(query)
                tracer.record_decision(output={"answer": result})
                return result

        async def main():
            # Both tasks run concurrently — context is isolated per task
            results = await asyncio.gather(
                agent_task("query A"),
                agent_task("query B"),
            )

        asyncio.run(main())
    """

    def __init__(
        self,
        offline_mode: bool = True,
        database_path: str = "agentability.db",
        api_endpoint: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.offline_mode = offline_mode
        self.api_endpoint = api_endpoint
        self.api_key = api_key

        if offline_mode:
            self.store: SQLiteStore = SQLiteStore(database_path)
        else:
            raise NotImplementedError(
                "Non-offline mode is not yet available. "
                "Use offline_mode=True with SQLite."
            )
        logger.info(
            "AsyncTracer initialised: offline_mode=%s, db=%s",
            offline_mode,
            database_path,
        )

    @contextlib.asynccontextmanager
    async def trace_decision(
        self,
        agent_id: str,
        decision_type: DecisionType,
        session_id: str | None = None,
        input_data: dict[str, Any] | None = None,
        parent_decision_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AsyncIterator[TracingContext]:
        """Async context manager that traces a single agent decision.

        Safe across ``await`` boundaries. Multiple concurrent coroutines
        can be inside their own ``trace_decision`` blocks simultaneously
        without any state leaking between them.

        Args:
            agent_id: Unique identifier for the agent making the decision.
            decision_type: Category of decision (see DecisionType enum).
            session_id: Optional session grouping identifier.
            input_data: Structured input that led to this decision.
            parent_decision_id: UUID of parent for hierarchical decisions.
            tags: Arbitrary string tags for filtering.
            metadata: Extra key-value pairs persisted alongside the decision.

        Yields:
            TracingContext: Mutable context to set confidence, add reasoning,
                accumulate tokens/costs.
        """
        decision_id = uuid4()
        start_time = time.time()

        state: dict[str, Any] = {
            "decision_id": decision_id,
            "agent_id": agent_id,
            "session_id": session_id,
            "decision_type": decision_type,
            "input_data": input_data or {},
            "parent_decision_id": parent_decision_id,
            "tags": tags or [],
            "metadata": metadata or {},
            "memory_operations": [],
            "llm_calls": 0,
            "total_tokens": 0,
            "total_cost_usd": 0.0,
        }

        # Store current state into the ContextVar and save the token so we
        # can restore the previous value (supports nested decisions).
        token = _current_decision.set(state)
        ctx = TracingContext(decision_id=decision_id, state=state)

        try:
            yield ctx
        finally:
            state["latency_ms"] = (time.time() - start_time) * 1000
            if "output_data" not in state:
                logger.warning(
                    "AsyncTracer: decision %s exited without record_decision().",
                    decision_id,
                )
                state["output_data"] = {}

            decision = Decision(**state)
            # SQLiteStore.save_decision is thread-safe via its internal lock.
            # For full async-native non-blocking IO, use aiosqlite in a
            # future release. This call is fast (<1 ms for typical payloads).
            self.store.save_decision(decision)

            # Restore previous ContextVar state (supports nested trace blocks)
            _current_decision.reset(token)

    def record_decision(
        self,
        output: Any,
        confidence: float | None = None,
        reasoning: list[str] | None = None,
        uncertainties: list[str] | None = None,
        assumptions: list[str] | None = None,
        constraints_checked: list[str] | None = None,
        constraints_violated: list[str] | None = None,
        quality_score: float | None = None,
        data_sources: list[str] | None = None,
    ) -> None:
        """Record the output and provenance of the current decision.

        Must be called inside an active ``async with tracer.trace_decision()``
        block.
        """
        state = _current_decision.get()
        if state is None:
            raise RuntimeError(
                "record_decision() must be called inside a trace_decision() block."
            )
        state["output_data"] = (
            output if isinstance(output, dict) else {"result": output}
        )
        if confidence is not None:
            state["confidence"] = confidence
        if reasoning:
            existing = state.get("reasoning") or []
            state["reasoning"] = existing + reasoning
        elif "reasoning" not in state:
            state["reasoning"] = []
        state["uncertainties"] = uncertainties or []
        state["assumptions"] = assumptions or []
        state["constraints_checked"] = constraints_checked or []
        state["constraints_violated"] = constraints_violated or []
        state["quality_score"] = quality_score
        state["data_sources"] = data_sources or []

    def record_llm_call(
        self,
        agent_id: str,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
        cost_usd: float,
        finish_reason: str | None = None,
        is_streaming: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> UUID:
        """Record an LLM API call linked to the current decision."""
        state = _current_decision.get()
        decision_id = state["decision_id"] if state is not None else None

        metrics = LLMMetrics(
            agent_id=agent_id,
            decision_id=decision_id,
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            finish_reason=finish_reason,
            is_streaming=is_streaming,
            chunks_received=None,
            temperature=temperature,
            max_tokens=max_tokens,
            metadata=dict(kwargs),
        )
        call_id = self.store.save_llm_metrics(metrics)

        if state is not None:
            state["llm_calls"] = state.get("llm_calls", 0) + 1
            state["total_tokens"] = (
                state.get("total_tokens", 0) + metrics.total_tokens
            )
            state["total_cost_usd"] = (
                state.get("total_cost_usd", 0.0) + cost_usd
            )
        return call_id

    def record_memory_operation(
        self,
        agent_id: str,
        memory_type: MemoryType,
        operation: MemoryOperation,
        latency_ms: float,
        items_processed: int,
        **kwargs: Any,
    ) -> UUID:
        """Record a memory subsystem operation."""
        metrics = MemoryMetrics(
            agent_id=agent_id,
            memory_type=memory_type,
            operation=operation,
            latency_ms=latency_ms,
            items_processed=items_processed,
            **kwargs,
        )
        op_id = self.store.save_memory_metrics(metrics)
        state = _current_decision.get()
        if state is not None:
            state.setdefault("memory_operations", []).append(op_id)
        return op_id

    def record_conflict(
        self,
        session_id: str,
        conflict_type: ConflictType,
        involved_agents: list[str],
        agent_positions: dict[str, dict[str, Any]],
        severity: float,
        **kwargs: Any,
    ) -> UUID:
        """Record a multi-agent conflict."""
        conflict = AgentConflict(
            session_id=session_id,
            conflict_type=conflict_type,
            involved_agents=involved_agents,
            agent_positions=agent_positions,
            severity=severity,
            **kwargs,
        )
        return self.store.save_conflict(conflict)

    def query_decisions(
        self,
        agent_id: str | None = None,
        session_id: str | None = None,
        limit: int = 100,
    ) -> list[Decision]:
        """Query persisted decisions with optional filters."""
        return self.store.query_decisions(
            agent_id=agent_id,
            session_id=session_id,
            limit=limit,
        )

    def close(self) -> None:
        """Close the storage connection."""
        if hasattr(self, "store"):
            self.store.close()
        logger.info("AsyncTracer closed.")

    async def __aenter__(self) -> AsyncTracer:
        return self

    async def __aexit__(self, *_: Any) -> None:
        self.close()

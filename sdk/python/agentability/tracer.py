"""Core tracer for instrumenting AI agents.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import contextlib
import threading
import time
from collections.abc import Iterator
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
from agentability.utils.logger import get_logger

logger = get_logger(__name__)
_local = threading.local()


class TracingContext:
    """Mutable context object yielded by :meth:`Tracer.trace_decision`.

    Attributes:
        decision_id: UUID assigned to the active decision.
    """

    def __init__(self, decision_id: UUID, state: dict[str, Any]) -> None:
        self.decision_id: UUID = decision_id
        self._state = state

    def set_confidence(self, confidence: float) -> None:
        """Set confidence, clamped to [0, 1]."""
        self._state["confidence"] = max(0.0, min(1.0, float(confidence)))

    def add_tokens(self, count: int) -> None:
        """Accumulate token usage."""
        self._state["total_tokens"] = self._state.get("total_tokens", 0) + count

    def add_cost(self, cost_usd: float) -> None:
        """Accumulate cost in USD."""
        self._state["total_cost_usd"] = (
            self._state.get("total_cost_usd", 0.0) + cost_usd
        )

    def add_reasoning_step(self, step: str) -> None:
        """Append a reasoning step."""
        self._state.setdefault("reasoning", []).append(step)

    def set_metadata(self, key: str, value: Any) -> None:
        """Store a metadata key-value pair."""
        self._state.setdefault("metadata", {})[key] = value


class Tracer:
    """Primary instrumentation class for tracking agent behaviour.

    Example:
        >>> tracer = Tracer(offline_mode=True)
        >>> with tracer.trace_decision(
        ...     agent_id="risk_agent",
        ...     decision_type=DecisionType.CLASSIFICATION,
        ... ) as ctx:
        ...     result = agent.predict(input_data)
        ...     tracer.record_decision(output=result, confidence=0.92)
    """

    def __init__(
        self,
        offline_mode: bool = True,
        storage_backend: str = "sqlite",
        database_path: str | None = None,
        api_endpoint: str | None = None,
        api_key: str | None = None,
        auto_flush: bool = True,
        flush_interval_seconds: int = 10,
    ) -> None:
        self.offline_mode = offline_mode
        self.storage_backend = storage_backend
        self.api_endpoint = api_endpoint
        self.api_key = api_key

        if offline_mode or storage_backend == "sqlite":
            self.store = SQLiteStore(database_path or "agentability.db")
        else:
            raise NotImplementedError(
                f"Storage backend '{storage_backend}' is not yet implemented."
            )
        logger.info(
            "Tracer initialised: offline_mode=%s, storage_backend=%s",
            offline_mode,
            storage_backend,
        )

    @contextlib.contextmanager
    def trace_decision(
        self,
        agent_id: str,
        decision_type: DecisionType,
        session_id: str | None = None,
        input_data: dict[str, Any] | None = None,
        parent_decision_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Iterator[TracingContext]:
        """Context manager wrapping a single agent decision."""
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

        previous = getattr(_local, "current_decision", None)
        _local.current_decision = state
        ctx = TracingContext(decision_id=decision_id, state=state)

        try:
            yield ctx
        finally:
            state["latency_ms"] = (time.time() - start_time) * 1000
            if "output_data" not in state:
                logger.warning(
                    "Decision %s exited without record_decision().", decision_id
                )
                state["output_data"] = {}
            decision = Decision(**state)
            self.store.save_decision(decision)
            _local.current_decision = previous

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
        """Record the output and provenance of the active decision."""
        state = getattr(_local, "current_decision", None)
        if state is None:
            raise RuntimeError(
                "record_decision() must be called inside a trace_decision() block."
            )
        state["output_data"] = (
            output if isinstance(output, dict) else {"result": output}
        )
        # Only overwrite confidence if explicitly provided — ctx.set_confidence()
        # may have already written a value into state.
        if confidence is not None:
            state["confidence"] = confidence
        # Merge explicit reasoning list on top of any steps added via
        # ctx.add_reasoning_step(); don't clobber an already-populated list.
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
        operation_id = self.store.save_memory_metrics(metrics)
        state = getattr(_local, "current_decision", None)
        if state is not None:
            state["memory_operations"].append(operation_id)
        return operation_id

    def record_llm_call(
        self,
        agent_id: str,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
        cost_usd: float,
        time_to_first_token_ms: float | None = None,
        finish_reason: str | None = None,
        is_streaming: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> UUID:
        """Record an LLM API call."""
        state = getattr(_local, "current_decision", None)
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
            time_to_first_token_ms=time_to_first_token_ms,
            finish_reason=finish_reason,
            is_streaming=is_streaming,
            chunks_received=None,
            temperature=temperature,
            max_tokens=max_tokens,
            metadata=dict(kwargs),
        )
        call_id = self.store.save_llm_metrics(metrics)

        if state is not None:
            state["llm_calls"] += 1
            state["total_tokens"] += metrics.total_tokens
            state["total_cost_usd"] += cost_usd

        return call_id

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

    def get_decision(self, decision_id: UUID) -> Decision | None:
        """Retrieve a decision by ID."""
        return self.store.get_decision(decision_id)

    def query_decisions(
        self,
        agent_id: str | None = None,
        session_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        decision_type: DecisionType | None = None,
        limit: int = 100,
    ) -> list[Decision]:
        """Query stored decisions with optional filters."""
        return self.store.query_decisions(
            agent_id=agent_id,
            session_id=session_id,
            start_time=start_time,
            end_time=end_time,
            decision_type=decision_type,
            limit=limit,
        )

    def close(self) -> None:
        """Close storage connection."""
        if hasattr(self.store, "close"):
            self.store.close()
        logger.info("Tracer closed.")

    def __enter__(self) -> Tracer:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

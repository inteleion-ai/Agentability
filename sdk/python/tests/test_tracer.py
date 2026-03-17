"""Tests for the core Tracer class.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import threading
from collections.abc import Generator
from pathlib import Path
from uuid import UUID

import pytest

from agentability import Tracer, TracingContext
from agentability.models import (
    ConflictType,
    DecisionType,
    MemoryOperation,
    MemoryType,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tracer(tmp_path: Path) -> Generator[Tracer, None, None]:
    """Return an offline Tracer backed by a temporary SQLite database."""
    t = Tracer(offline_mode=True, database_path=str(tmp_path / "test.db"))
    yield t
    t.close()


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------


class TestTracerInit:
    def test_default_offline_mode(self, tmp_path: Path) -> None:
        t = Tracer(offline_mode=True, database_path=str(tmp_path / "a.db"))
        assert t.offline_mode is True
        t.close()

    def test_unsupported_backend_raises(self) -> None:
        with pytest.raises(NotImplementedError, match="timescaledb"):
            Tracer(offline_mode=False, storage_backend="timescaledb")

    def test_context_manager_closes_cleanly(self, tmp_path: Path) -> None:
        with Tracer(offline_mode=True, database_path=str(tmp_path / "b.db")) as t:
            assert t is not None


# ---------------------------------------------------------------------------
# trace_decision context manager
# ---------------------------------------------------------------------------


class TestTraceDecision:
    def test_yields_tracing_context(self, tracer: Tracer) -> None:
        with tracer.trace_decision(
            agent_id="agent_1", decision_type=DecisionType.CLASSIFICATION
        ) as ctx:
            assert isinstance(ctx, TracingContext)

    def test_decision_id_is_uuid(self, tracer: Tracer) -> None:
        with tracer.trace_decision(
            agent_id="agent_1", decision_type=DecisionType.CLASSIFICATION
        ) as ctx:
            assert isinstance(ctx.decision_id, UUID)

    def test_decision_persisted_after_context_exit(self, tracer: Tracer) -> None:
        with tracer.trace_decision(
            agent_id="persist_agent", decision_type=DecisionType.GENERATION
        ):
            tracer.record_decision(output="hello", confidence=0.9)
        assert len(tracer.query_decisions(agent_id="persist_agent")) == 1

    def test_decision_without_record_decision(self, tracer: Tracer) -> None:
        with tracer.trace_decision(
            agent_id="no_record", decision_type=DecisionType.PLANNING
        ):
            pass
        assert len(tracer.query_decisions(agent_id="no_record")) == 1

    def test_exception_inside_context_still_persists(self, tracer: Tracer) -> None:
        with pytest.raises(ValueError), tracer.trace_decision(
            agent_id="exc_agent", decision_type=DecisionType.CLASSIFICATION
        ):
            raise ValueError("deliberate test error")
        assert len(tracer.query_decisions(agent_id="exc_agent")) == 1

    def test_session_id_stored(self, tracer: Tracer) -> None:
        with tracer.trace_decision(
            agent_id="session_agent",
            decision_type=DecisionType.CLASSIFICATION,
            session_id="sess_abc",
        ):
            tracer.record_decision(output="ok")
        results = tracer.query_decisions(session_id="sess_abc")
        assert len(results) == 1
        assert results[0].session_id == "sess_abc"

    def test_tags_stored(self, tracer: Tracer) -> None:
        with tracer.trace_decision(
            agent_id="tag_agent",
            decision_type=DecisionType.CLASSIFICATION,
            tags=["production", "loan"],
        ):
            tracer.record_decision(output="approve")
        decision = tracer.query_decisions(agent_id="tag_agent")[0]
        assert "production" in decision.tags


# ---------------------------------------------------------------------------
# record_decision
# ---------------------------------------------------------------------------


class TestRecordDecision:
    def test_confidence_stored(self, tracer: Tracer) -> None:
        with tracer.trace_decision(
            agent_id="conf_agent", decision_type=DecisionType.CLASSIFICATION
        ):
            tracer.record_decision(output="approve", confidence=0.74)
        d = tracer.query_decisions(agent_id="conf_agent")[0]
        assert d.confidence == pytest.approx(0.74)

    def test_reasoning_stored(self, tracer: Tracer) -> None:
        steps = ["Score above threshold", "Income verified", "No adverse events"]
        with tracer.trace_decision(
            agent_id="reason_agent", decision_type=DecisionType.CLASSIFICATION
        ):
            tracer.record_decision(output="approve", reasoning=steps)
        d = tracer.query_decisions(agent_id="reason_agent")[0]
        assert d.reasoning == steps

    def test_uncertainties_stored(self, tracer: Tracer) -> None:
        with tracer.trace_decision(
            agent_id="unc_agent", decision_type=DecisionType.CLASSIFICATION
        ):
            tracer.record_decision(
                output="deny", uncertainties=["Employment data missing"]
            )
        d = tracer.query_decisions(agent_id="unc_agent")[0]
        assert "Employment data missing" in d.uncertainties

    def test_constraints_violated_stored(self, tracer: Tracer) -> None:
        with tracer.trace_decision(
            agent_id="constraint_agent",
            decision_type=DecisionType.CLASSIFICATION,
        ):
            tracer.record_decision(
                output="deny",
                constraints_checked=["min_score >= 650"],
                constraints_violated=["income_age_days <= 30"],
            )
        d = tracer.query_decisions(agent_id="constraint_agent")[0]
        assert "income_age_days <= 30" in d.constraints_violated
        assert "min_score >= 650" in d.constraints_checked

    def test_non_dict_output_wrapped(self, tracer: Tracer) -> None:
        with tracer.trace_decision(
            agent_id="wrap_agent", decision_type=DecisionType.GENERATION
        ):
            tracer.record_decision(output="plain string")
        d = tracer.query_decisions(agent_id="wrap_agent")[0]
        assert d.output_data == {"result": "plain string"}

    def test_raises_outside_context(self, tracer: Tracer) -> None:
        with pytest.raises(RuntimeError, match="trace_decision"):
            tracer.record_decision(output="orphan")

    def test_data_sources_stored(self, tracer: Tracer) -> None:
        with tracer.trace_decision(
            agent_id="src_agent", decision_type=DecisionType.RETRIEVAL
        ):
            tracer.record_decision(
                output="result",
                data_sources=["credit_bureau", "income_api"],
            )
        d = tracer.query_decisions(agent_id="src_agent")[0]
        assert "credit_bureau" in d.data_sources


# ---------------------------------------------------------------------------
# TracingContext helpers
# ---------------------------------------------------------------------------


class TestTracingContext:
    def test_set_confidence(self, tracer: Tracer) -> None:
        with tracer.trace_decision(
            agent_id="ctx_agent", decision_type=DecisionType.CLASSIFICATION
        ) as ctx:
            ctx.set_confidence(0.55)
            tracer.record_decision(output="ok")
        d = tracer.query_decisions(agent_id="ctx_agent")[0]
        assert d.confidence == pytest.approx(0.55)

    def test_set_confidence_clamps_above_one(self, tracer: Tracer) -> None:
        with tracer.trace_decision(
            agent_id="clamp_agent", decision_type=DecisionType.CLASSIFICATION
        ) as ctx:
            ctx.set_confidence(1.5)
            tracer.record_decision(output="ok")
        d = tracer.query_decisions(agent_id="clamp_agent")[0]
        assert d.confidence == pytest.approx(1.0)

    def test_add_tokens(self, tracer: Tracer) -> None:
        with tracer.trace_decision(
            agent_id="token_agent", decision_type=DecisionType.GENERATION
        ) as ctx:
            ctx.add_tokens(500)
            ctx.add_tokens(300)
            tracer.record_decision(output="text")
        d = tracer.query_decisions(agent_id="token_agent")[0]
        assert d.total_tokens == 800

    def test_add_cost(self, tracer: Tracer) -> None:
        with tracer.trace_decision(
            agent_id="cost_agent", decision_type=DecisionType.GENERATION
        ) as ctx:
            ctx.add_cost(0.01)
            ctx.add_cost(0.005)
            tracer.record_decision(output="text")
        d = tracer.query_decisions(agent_id="cost_agent")[0]
        assert d.total_cost_usd == pytest.approx(0.015)

    def test_add_reasoning_step(self, tracer: Tracer) -> None:
        with tracer.trace_decision(
            agent_id="step_agent", decision_type=DecisionType.PLANNING
        ) as ctx:
            ctx.add_reasoning_step("Fetched context from memory")
            ctx.add_reasoning_step("Evaluated constraints")
            tracer.record_decision(output="plan")
        d = tracer.query_decisions(agent_id="step_agent")[0]
        assert "Fetched context from memory" in d.reasoning
        assert len(d.reasoning) == 2

    def test_set_metadata(self, tracer: Tracer) -> None:
        with tracer.trace_decision(
            agent_id="meta_agent", decision_type=DecisionType.CLASSIFICATION
        ) as ctx:
            ctx.set_metadata("chain_name", "LoanChain")
            tracer.record_decision(output="ok")
        d = tracer.query_decisions(agent_id="meta_agent")[0]
        assert d.metadata.get("chain_name") == "LoanChain"


# ---------------------------------------------------------------------------
# record_memory_operation
# ---------------------------------------------------------------------------


class TestRecordMemoryOperation:
    def test_returns_uuid(self, tracer: Tracer) -> None:
        op_id = tracer.record_memory_operation(
            agent_id="mem_agent",
            memory_type=MemoryType.VECTOR,
            operation=MemoryOperation.RETRIEVE,
            latency_ms=25.0,
            items_processed=10,
        )
        assert isinstance(op_id, UUID)

    def test_vector_metrics_stored(self, tracer: Tracer) -> None:
        tracer.record_memory_operation(
            agent_id="rag_agent",
            memory_type=MemoryType.VECTOR,
            operation=MemoryOperation.RETRIEVE,
            latency_ms=38.5,
            items_processed=10,
            avg_similarity=0.82,
            retrieval_precision=0.85,
        )

    def test_linked_to_active_decision(self, tracer: Tracer) -> None:
        with tracer.trace_decision(
            agent_id="linked_agent", decision_type=DecisionType.RETRIEVAL
        ):
            op_id = tracer.record_memory_operation(
                agent_id="linked_agent",
                memory_type=MemoryType.EPISODIC,
                operation=MemoryOperation.RETRIEVE,
                latency_ms=12.0,
                items_processed=5,
            )
            tracer.record_decision(output="result")
        d = tracer.query_decisions(agent_id="linked_agent")[0]
        assert op_id in d.memory_operations


# ---------------------------------------------------------------------------
# record_llm_call
# ---------------------------------------------------------------------------


class TestRecordLlmCall:
    def test_returns_uuid(self, tracer: Tracer) -> None:
        call_id = tracer.record_llm_call(
            agent_id="llm_agent",
            provider="anthropic",
            model="claude-sonnet-4",
            prompt_tokens=500,
            completion_tokens=200,
            latency_ms=800.0,
            cost_usd=0.005,
        )
        assert isinstance(call_id, UUID)

    def test_llm_call_increments_decision_counters(self, tracer: Tracer) -> None:
        with tracer.trace_decision(
            agent_id="llm_inc_agent", decision_type=DecisionType.GENERATION
        ):
            tracer.record_llm_call(
                agent_id="llm_inc_agent",
                provider="openai",
                model="gpt-4",
                prompt_tokens=1000,
                completion_tokens=400,
                latency_ms=1200.0,
                cost_usd=0.06,
            )
            tracer.record_decision(output="summary")
        d = tracer.query_decisions(agent_id="llm_inc_agent")[0]
        assert d.llm_calls == 1
        assert d.total_tokens == 1400
        assert d.total_cost_usd == pytest.approx(0.06)


# ---------------------------------------------------------------------------
# record_conflict
# ---------------------------------------------------------------------------


class TestRecordConflict:
    def test_returns_uuid(self, tracer: Tracer) -> None:
        conflict_id = tracer.record_conflict(
            session_id="sess_1",
            conflict_type=ConflictType.GOAL_CONFLICT,
            involved_agents=["risk", "sales"],
            agent_positions={
                "risk": {"decision": "deny"},
                "sales": {"decision": "approve"},
            },
            severity=0.6,
        )
        assert isinstance(conflict_id, UUID)


# ---------------------------------------------------------------------------
# query_decisions filters
# ---------------------------------------------------------------------------


class TestQueryDecisions:
    def _make(
        self,
        tracer: Tracer,
        agent_id: str,
        decision_type: DecisionType = DecisionType.CLASSIFICATION,
        session_id: str | None = None,
    ) -> None:
        with tracer.trace_decision(
            agent_id=agent_id,
            decision_type=decision_type,
            session_id=session_id,
        ):
            tracer.record_decision(output="ok")

    def test_filter_by_agent_id(self, tracer: Tracer) -> None:
        self._make(tracer, "agent_a")
        self._make(tracer, "agent_b")
        self._make(tracer, "agent_a")
        results = tracer.query_decisions(agent_id="agent_a")
        assert len(results) == 2
        assert all(d.agent_id == "agent_a" for d in results)

    def test_filter_by_session_id(self, tracer: Tracer) -> None:
        self._make(tracer, "agent_x", session_id="sess_1")
        self._make(tracer, "agent_x", session_id="sess_2")
        assert len(tracer.query_decisions(session_id="sess_1")) == 1

    def test_limit_respected(self, tracer: Tracer) -> None:
        for _ in range(10):
            self._make(tracer, "bulk_agent")
        assert len(tracer.query_decisions(agent_id="bulk_agent", limit=3)) == 3

    def test_filter_by_decision_type(self, tracer: Tracer) -> None:
        self._make(tracer, "type_agent", decision_type=DecisionType.PLANNING)
        self._make(tracer, "type_agent", decision_type=DecisionType.GENERATION)
        results = tracer.query_decisions(
            agent_id="type_agent", decision_type=DecisionType.PLANNING
        )
        assert len(results) == 1
        assert results[0].decision_type == DecisionType.PLANNING


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------


class TestThreadSafety:
    def test_concurrent_decisions_do_not_cross_contaminate(
        self, tracer: Tracer
    ) -> None:
        def run_thread(agent_id: str, confidence: float) -> None:
            import time

            with tracer.trace_decision(
                agent_id=agent_id,
                decision_type=DecisionType.CLASSIFICATION,
            ) as ctx:
                ctx.set_confidence(confidence)
                time.sleep(0.02)
                tracer.record_decision(output="done")

        t1 = threading.Thread(target=run_thread, args=("thread_a", 0.1))
        t2 = threading.Thread(target=run_thread, args=("thread_b", 0.9))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        a = tracer.query_decisions(agent_id="thread_a")[0]
        b = tracer.query_decisions(agent_id="thread_b")[0]
        assert a.confidence == pytest.approx(0.1), "Thread A confidence corrupted"
        assert b.confidence == pytest.approx(0.9), "Thread B confidence corrupted"

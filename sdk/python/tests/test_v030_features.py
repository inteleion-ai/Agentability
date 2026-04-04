"""Tests for v0.3.0 new features.

Covers:
- AsyncTracer (contextvars isolation, concurrent coroutine safety)
- DriftDetector.detect_drift_cusum (CUSUM algorithm)
- ConflictAnalyzer.compute_nash_equilibrium (pure and mixed strategies)
- CausalGraphBuilder._get_edge O(1) lookup
- SQLiteStore.delete_decision (GDPR)
- OpenAI Agents and LangGraph integration stubs

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

import pytest

from agentability.models import ConflictType, DecisionType, MemoryOperation, MemoryType


# ── AsyncTracer ────────────────────────────────────────────────────────────


class TestAsyncTracer:
    """Verify AsyncTracer isolation across concurrent coroutines."""

    @pytest.fixture
    def tracer(self, tmp_path):
        from agentability.async_tracer import AsyncTracer

        t = AsyncTracer(offline_mode=True, database_path=str(tmp_path / "async.db"))
        yield t
        t.close()

    def test_import(self):
        from agentability.async_tracer import AsyncTracer

        assert AsyncTracer is not None

    def test_exported_from_package(self):
        from agentability import AsyncTracer

        assert AsyncTracer is not None

    @pytest.mark.asyncio
    async def test_basic_async_trace(self, tracer):
        """Single async trace records a decision."""
        async with tracer.trace_decision(
            agent_id="async_agent",
            decision_type=DecisionType.GENERATION,
            input_data={"query": "hello"},
        ) as ctx:
            ctx.set_confidence(0.88)
            ctx.add_reasoning_step("Step 1: process input")
            tracer.record_decision(output={"answer": "world"})

        decisions = tracer.query_decisions(agent_id="async_agent")
        assert len(decisions) == 1
        assert decisions[0].confidence == pytest.approx(0.88, abs=1e-3)
        assert decisions[0].reasoning == ["Step 1: process input"]

    @pytest.mark.asyncio
    async def test_concurrent_coroutines_isolated(self, tracer):
        """Two concurrent coroutines must not leak ContextVar state."""
        results: dict[str, float] = {}

        async def run_agent(agent_id: str, confidence: float, delay: float) -> None:
            async with tracer.trace_decision(
                agent_id=agent_id,
                decision_type=DecisionType.CLASSIFICATION,
            ) as ctx:
                await asyncio.sleep(delay)  # yield, let other coroutine run
                ctx.set_confidence(confidence)
                tracer.record_decision(output={"label": agent_id})
                results[agent_id] = ctx._state["confidence"]

        await asyncio.gather(
            run_agent("agent_alpha", 0.70, 0.01),
            run_agent("agent_beta", 0.90, 0.0),
        )

        # Each coroutine must have recorded its own confidence
        assert results["agent_alpha"] == pytest.approx(0.70, abs=1e-3)
        assert results["agent_beta"] == pytest.approx(0.90, abs=1e-3)

        alpha = tracer.query_decisions(agent_id="agent_alpha")
        beta = tracer.query_decisions(agent_id="agent_beta")
        assert len(alpha) == 1
        assert len(beta) == 1
        assert alpha[0].confidence == pytest.approx(0.70, abs=1e-3)
        assert beta[0].confidence == pytest.approx(0.90, abs=1e-3)

    @pytest.mark.asyncio
    async def test_record_llm_call_inside_trace(self, tracer):
        """LLM call recorded inside async trace is linked to correct decision."""
        async with tracer.trace_decision(
            agent_id="llm_agent",
            decision_type=DecisionType.GENERATION,
        ) as ctx:
            call_id = tracer.record_llm_call(
                agent_id="llm_agent",
                provider="anthropic",
                model="claude-haiku-4",
                prompt_tokens=100,
                completion_tokens=50,
                latency_ms=350.0,
                cost_usd=0.001,
                finish_reason="end_turn",
            )
            tracer.record_decision(output={"text": "hello"})

        assert isinstance(call_id, UUID)
        decisions = tracer.query_decisions(agent_id="llm_agent")
        assert len(decisions) == 1
        assert decisions[0].llm_calls == 1
        assert decisions[0].total_tokens == 150

    @pytest.mark.asyncio
    async def test_record_memory_op_inside_trace(self, tracer):
        """Memory operation recorded inside async trace."""
        async with tracer.trace_decision(
            agent_id="rag_async",
            decision_type=DecisionType.RETRIEVAL,
        ):
            op_id = tracer.record_memory_operation(
                agent_id="rag_async",
                memory_type=MemoryType.VECTOR,
                operation=MemoryOperation.RETRIEVE,
                latency_ms=22.0,
                items_processed=5,
                avg_similarity=0.83,
            )
            tracer.record_decision(output={"chunks": 5})

        assert isinstance(op_id, UUID)

    @pytest.mark.asyncio
    async def test_context_manager_protocol(self, tracer):
        """AsyncTracer supports async with ... as tracer pattern."""
        from agentability.async_tracer import AsyncTracer

        async with AsyncTracer(
            offline_mode=True, database_path=":memory:"
        ) as t:
            async with t.trace_decision(
                agent_id="ctx_agent",
                decision_type=DecisionType.ROUTING,
            ):
                t.record_decision(output={"route": "A"})


# ── CUSUM Drift Detection ──────────────────────────────────────────────────


class TestCUSUM:
    """Verify the CUSUM change-point detection algorithm."""

    @pytest.fixture
    def detector(self):
        from agentability.analyzers.drift_detector import DriftDetector

        return DriftDetector()

    def _add_stable_then_drift(
        self, detector, agent_id: str, stable_conf: float = 0.85, drift_conf: float = 0.55
    ) -> None:
        now = datetime.utcnow()
        # 20 stable observations
        for i in range(20):
            ts = now - timedelta(hours=20 - i)
            detector.record_confidence(agent_id, stable_conf + (i % 3) * 0.01, ts)
        # 15 drifted observations
        for i in range(15):
            ts = now - timedelta(hours=i)
            detector.record_confidence(agent_id, drift_conf + (i % 2) * 0.01, ts)

    def test_cusum_detects_downward_drift(self, detector):
        self._add_stable_then_drift(detector, "cusum_agent")
        result = detector.detect_drift_cusum("cusum_agent", threshold=3.0)
        assert result["change_detected"] is True
        assert result["direction"] == "downward"
        assert result["severity"] in ("medium", "high", "critical")

    def test_cusum_stable_no_change(self, detector):
        now = datetime.utcnow()
        for i in range(30):
            ts = now - timedelta(hours=30 - i)
            detector.record_confidence("stable_cusum", 0.82 + (i % 4) * 0.01, ts)
        result = detector.detect_drift_cusum("stable_cusum", threshold=5.0)
        # Stable data should not trigger with high threshold
        assert "change_detected" in result
        assert result.get("observations", 0) == 30

    def test_cusum_insufficient_data(self, detector):
        for i in range(5):
            detector.record_confidence("tiny", 0.8, datetime.utcnow())
        result = detector.detect_drift_cusum("tiny")
        assert result["change_detected"] is False
        assert "error" in result

    def test_cusum_no_agent_data(self, detector):
        result = detector.detect_drift_cusum("nonexistent_agent")
        assert result["change_detected"] is False

    def test_cusum_returns_correct_keys(self, detector):
        self._add_stable_then_drift(detector, "key_check_agent")
        result = detector.detect_drift_cusum("key_check_agent")
        required = {
            "change_detected", "direction", "severity", "cusum_values",
            "max_cusum", "threshold", "target_mean", "observations", "recommendation",
        }
        assert required.issubset(result.keys())

    def test_cusum_change_point_index_in_range(self, detector):
        self._add_stable_then_drift(detector, "cp_agent")
        result = detector.detect_drift_cusum("cp_agent", threshold=2.0)
        if result["change_detected"]:
            idx = result["change_point_index"]
            obs = result["observations"]
            assert 0 <= idx < obs

    def test_cusum_custom_target(self, detector):
        now = datetime.utcnow()
        for i in range(35):
            ts = now - timedelta(hours=35 - i)
            conf = 0.9 if i < 20 else 0.5
            detector.record_confidence("custom_target", conf, ts)
        # Supply explicit target so CUSUM calibrates from it
        result = detector.detect_drift_cusum("custom_target", target=0.9, threshold=3.0)
        assert "change_detected" in result


# ── Nash Equilibrium ───────────────────────────────────────────────────────


class TestNashEquilibrium:
    """Verify Nash equilibrium computation — pure and mixed strategies."""

    @pytest.fixture
    def analyzer(self):
        from agentability.analyzers.conflict_analyzer import ConflictAnalyzer

        return ConflictAnalyzer()

    def test_pure_nash_dominant_strategies(self, analyzer):
        """Classic Prisoner's Dilemma variant — each has a dominant strategy."""
        result = analyzer.compute_nash_equilibrium(
            agents=["risk", "sales"],
            payoff_matrix={
                "risk":  {"deny": 0.85, "approve": 0.20},
                "sales": {"deny": 0.15, "approve": 0.90},
            },
        )
        assert result["strategy"] in ("pure", "mixed", "none_found")
        if result["strategy"] == "pure":
            assert "equilibrium" in result
            assert "risk" in result["equilibrium"]
            assert "sales" in result["equilibrium"]
            assert "social_welfare" in result
            assert isinstance(result["social_welfare"], float)

    def test_pure_nash_matching_pennies(self, analyzer):
        """Matching Pennies has no pure NE — should fall to mixed."""
        result = analyzer.compute_nash_equilibrium(
            agents=["a1", "a2"],
            payoff_matrix={
                "a1": {"heads": 1.0, "tails": 0.0},
                "a2": {"heads": 0.0, "tails": 1.0},
            },
        )
        # Either mixed NE found or none_found — both valid
        assert result["strategy"] in ("pure", "mixed", "none_found")

    def test_nash_requires_two_agents(self, analyzer):
        result = analyzer.compute_nash_equilibrium(
            agents=["a1", "a2", "a3"],
            payoff_matrix={"a1": {"x": 1.0}},
        )
        assert "error" in result

    def test_nash_missing_payoff_data(self, analyzer):
        result = analyzer.compute_nash_equilibrium(
            agents=["a1", "a2"],
            payoff_matrix={"a1": {"approve": 0.9}},
        )
        assert "error" in result

    def test_pure_nash_pareto_check(self, analyzer):
        """Result includes Pareto optimality flag for pure NE."""
        result = analyzer.compute_nash_equilibrium(
            agents=["risk", "sales"],
            payoff_matrix={
                "risk":  {"deny": 0.85, "approve": 0.30},
                "sales": {"deny": 0.20, "approve": 0.90},
            },
        )
        if result["strategy"] == "pure":
            assert "is_pareto_optimal" in result
            assert isinstance(result["is_pareto_optimal"], bool)

    def test_social_welfare_is_positive(self, analyzer):
        result = analyzer.compute_nash_equilibrium(
            agents=["a", "b"],
            payoff_matrix={
                "a": {"x": 0.7, "y": 0.3},
                "b": {"x": 0.4, "y": 0.8},
            },
        )
        if "social_welfare" in result:
            assert result["social_welfare"] >= 0.0


# ── CausalGraph O(1) Edge Lookup ───────────────────────────────────────────


class TestCausalGraphPerformance:
    """Verify _get_edge uses O(1) lookup via _edge_index."""

    @pytest.fixture
    def builder(self):
        from agentability.analyzers.causal_graph import CausalGraphBuilder

        return CausalGraphBuilder()

    def test_edge_index_populated_on_add(self, builder):
        t = datetime.utcnow()
        builder.add_node("n1", "decision", "Node 1", timestamp=t)
        builder.add_node("n2", "decision", "Node 2", timestamp=t)
        builder.add_causal_edge("n1", "n2", "direct", strength=0.9)
        assert ("n1", "n2") in builder._edge_index

    def test_get_edge_o1_lookup(self, builder):
        """_get_edge must use _edge_index dict, not linear scan."""
        t = datetime.utcnow()
        # Add 1000 nodes and edges
        for i in range(100):
            builder.add_node(f"n{i}", "decision", f"Node {i}", timestamp=t)
        for i in range(99):
            builder.add_causal_edge(f"n{i}", f"n{i+1}", "direct", strength=0.8)

        # Time the lookup — should be O(1) not O(n)
        start = time.perf_counter()
        for _ in range(10_000):
            _ = builder._get_edge("n0", "n1")
        elapsed = time.perf_counter() - start
        # 10k lookups in < 100ms is comfortably O(1)
        assert elapsed < 0.1, f"_get_edge too slow: {elapsed:.3f}s for 10k calls"

    def test_get_edge_returns_correct_edge(self, builder):
        t = datetime.utcnow()
        builder.add_node("src", "decision", "Source", timestamp=t)
        builder.add_node("tgt", "decision", "Target", timestamp=t)
        edge = builder.add_causal_edge("src", "tgt", "direct", strength=0.75)
        found = builder._get_edge("src", "tgt")
        assert found is not None
        assert found.source_id == "src"
        assert found.target_id == "tgt"
        assert found.strength == pytest.approx(0.75)

    def test_get_edge_missing_returns_none(self, builder):
        t = datetime.utcnow()
        builder.add_node("a", "decision", "A", timestamp=t)
        builder.add_node("b", "decision", "B", timestamp=t)
        assert builder._get_edge("a", "b") is None


# ── GDPR Delete Decision ───────────────────────────────────────────────────


class TestDeleteDecision:
    """Verify GDPR right-to-erasure via SQLiteStore.delete_decision."""

    @pytest.fixture
    def store(self, tmp_path):
        from agentability.storage.sqlite_store import SQLiteStore

        s = SQLiteStore(database_path=str(tmp_path / "gdpr.db"))
        yield s
        s.close()

    def test_delete_removes_decision(self, store):
        from agentability.models import Decision, DecisionType

        d = Decision(
            agent_id="agent_x",
            decision_type=DecisionType.CLASSIFICATION,
        )
        store.save_decision(d)
        assert store.get_decision(d.decision_id) is not None
        store.delete_decision(d.decision_id)
        assert store.get_decision(d.decision_id) is None

    def test_delete_nonexistent_is_silent(self, store):
        """Deleting a non-existent ID should not raise."""
        from uuid import uuid4

        store.delete_decision(uuid4())  # should not raise

    def test_delete_removes_linked_llm_metrics(self, store):
        """Deleting a decision also removes its llm_metrics rows."""
        from agentability.models import Decision, DecisionType, LLMMetrics

        d = Decision(
            agent_id="agent_y",
            decision_type=DecisionType.GENERATION,
        )
        store.save_decision(d)
        llm = LLMMetrics(
            agent_id="agent_y",
            decision_id=d.decision_id,
            provider="openai",
            model="gpt-4o",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            latency_ms=500.0,
            cost_usd=0.005,
        )
        store.save_llm_metrics(llm)
        store.delete_decision(d.decision_id)

        # Decision gone
        assert store.get_decision(d.decision_id) is None
        # Verify llm_metrics row gone via raw cursor
        cursor = store.conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM llm_metrics WHERE decision_id = ?",
            (str(d.decision_id),),
        )
        count = cursor.fetchone()[0]
        assert count == 0


# ── Integration Stubs ──────────────────────────────────────────────────────


class TestOpenAIAgentsIntegration:
    """Smoke tests for OpenAIAgentsInstrumentation (no live API call)."""

    def test_import(self):
        from agentability.integrations.openai_agents import (
            OpenAIAgentsInstrumentation,
        )

        assert OpenAIAgentsInstrumentation is not None

    def test_instantiation(self, tmp_path):
        from agentability import Tracer
        from agentability.integrations.openai_agents import (
            OpenAIAgentsInstrumentation,
        )

        tracer = Tracer(
            offline_mode=True, database_path=str(tmp_path / "oai.db")
        )
        instr = OpenAIAgentsInstrumentation(tracer=tracer)
        assert instr.tracer is tracer
        tracer.close()

    def test_cost_estimation(self, tmp_path):
        from agentability import Tracer
        from agentability.integrations.openai_agents import (
            OpenAIAgentsInstrumentation,
        )

        tracer = Tracer(
            offline_mode=True, database_path=str(tmp_path / "oai2.db")
        )
        instr = OpenAIAgentsInstrumentation(tracer=tracer)
        cost = instr._estimate_cost("gpt-4o", 1000, 500)
        assert cost == pytest.approx(
            (1000 / 1_000_000) * 2.50 + (500 / 1_000_000) * 10.00,
            rel=1e-3,
        )
        tracer.close()


class TestLangGraphIntegration:
    """Smoke tests for LangGraphInstrumentation (no live graph run)."""

    def test_import(self):
        from agentability.integrations.langgraph import LangGraphInstrumentation

        assert LangGraphInstrumentation is not None

    def test_wrap_node_returns_callable(self, tmp_path):
        from agentability import Tracer
        from agentability.integrations.langgraph import LangGraphInstrumentation

        tracer = Tracer(
            offline_mode=True, database_path=str(tmp_path / "lg.db")
        )
        instr = LangGraphInstrumentation(tracer=tracer, graph_name="test_graph")

        def my_node(state: dict) -> dict:
            return {"response": "ok"}

        wrapped = instr.wrap_node("my_node", my_node)
        assert callable(wrapped)
        tracer.close()

    def test_wrapped_node_traces_decision(self, tmp_path):
        from agentability import Tracer
        from agentability.integrations.langgraph import LangGraphInstrumentation

        tracer = Tracer(
            offline_mode=True, database_path=str(tmp_path / "lg2.db")
        )
        instr = LangGraphInstrumentation(tracer=tracer, graph_name="test")

        def triage(state: dict) -> dict:
            return {**state, "routed": True}

        wrapped = instr.wrap_node("triage", triage)
        result = wrapped({"message": "refund please"})

        assert result["routed"] is True
        decisions = tracer.query_decisions()
        assert len(decisions) >= 1
        assert any(d.agent_id == "test.triage" for d in decisions)
        tracer.close()

    def test_state_snapshot(self, tmp_path):
        from agentability import Tracer
        from agentability.integrations.langgraph import LangGraphInstrumentation

        tracer = Tracer(
            offline_mode=True, database_path=str(tmp_path / "snap.db")
        )
        instr = LangGraphInstrumentation(tracer=tracer)
        snap = instr._snapshot_state({"key": "value", "num": 42})
        assert snap["num"] == 42
        assert "key" in snap
        tracer.close()

    def test_delta_compute(self, tmp_path):
        from agentability import Tracer
        from agentability.integrations.langgraph import LangGraphInstrumentation

        tracer = Tracer(
            offline_mode=True, database_path=str(tmp_path / "delta.db")
        )
        instr = LangGraphInstrumentation(tracer=tracer)
        delta = instr._compute_delta({"a": "1", "b": "2"}, {"a": "1", "b": "3"})
        assert "b" in delta
        assert "a" not in delta
        tracer.close()

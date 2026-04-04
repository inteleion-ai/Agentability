"""Tests for all metrics collectors.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import time

import pytest

from agentability.metrics.conflict_metrics import (
    AgentPosition,
    ConflictMetricsCollector,
    ConflictType,
    ResolutionStrategy,
)
from agentability.metrics.decision_metrics import (
    DecisionMetricsCollector,
    DecisionType,
)
from agentability.metrics.llm_metrics import LLMCallTracker, LLMMetricsCollector
from agentability.metrics.memory_metrics import (
    MemoryMetricsCollector,
    calculate_retrieval_precision,
    calculate_retrieval_recall,
    calculate_similarity_stats,
)
from agentability.models import MemoryOperation, MemoryType


# ===========================================================================
# DecisionMetricsCollector
# ===========================================================================


class TestDecisionMetricsCollector:
    @pytest.fixture()
    def collector(self) -> DecisionMetricsCollector:
        return DecisionMetricsCollector(agent_id="risk_agent")

    def test_initial_decisions_empty(
        self, collector: DecisionMetricsCollector
    ) -> None:
        assert collector.decisions == []

    def test_track_decision_context_records_metric(
        self, collector: DecisionMetricsCollector
    ) -> None:
        with collector.track_decision("classification"):
            pass
        assert len(collector.decisions) == 1

    def test_confidence_stored(self, collector: DecisionMetricsCollector) -> None:
        with collector.track_decision("classification") as ctx:
            ctx.set_confidence(0.88)
        assert collector.decisions[0].confidence == pytest.approx(0.88)

    def test_confidence_clamped_above_one(
        self, collector: DecisionMetricsCollector
    ) -> None:
        with collector.track_decision("classification") as ctx:
            ctx.set_confidence(1.5)
        assert collector.decisions[0].confidence == pytest.approx(1.0)

    def test_confidence_clamped_below_zero(
        self, collector: DecisionMetricsCollector
    ) -> None:
        with collector.track_decision("classification") as ctx:
            ctx.set_confidence(-0.1)
        assert collector.decisions[0].confidence == pytest.approx(0.0)

    def test_success_stored(self, collector: DecisionMetricsCollector) -> None:
        with collector.track_decision("classification") as ctx:
            ctx.set_success(True)
        assert collector.decisions[0].success is True

    def test_reasoning_steps_incremented(
        self, collector: DecisionMetricsCollector
    ) -> None:
        with collector.track_decision("planning") as ctx:
            ctx.add_reasoning_step()
            ctx.add_reasoning_step()
        assert collector.decisions[0].reasoning_steps == 2

    def test_tool_calls_incremented(
        self, collector: DecisionMetricsCollector
    ) -> None:
        with collector.track_decision("tool_selection") as ctx:
            ctx.add_tool_call()
        assert collector.decisions[0].tool_calls == 1

    def test_tokens_accumulated(self, collector: DecisionMetricsCollector) -> None:
        with collector.track_decision("generation") as ctx:
            ctx.add_tokens(500)
            ctx.add_tokens(300)
        assert collector.decisions[0].tokens_used == 800

    def test_cost_accumulated(self, collector: DecisionMetricsCollector) -> None:
        with collector.track_decision("generation") as ctx:
            ctx.add_cost(0.01)
            ctx.add_cost(0.005)
        assert collector.decisions[0].cost_usd == pytest.approx(0.015)

    def test_metadata_stored(self, collector: DecisionMetricsCollector) -> None:
        with collector.track_decision("classification") as ctx:
            ctx.set_metadata("model", "claude-sonnet-4")
        assert collector.decisions[0].metadata["model"] == "claude-sonnet-4"

    def test_latency_positive(self, collector: DecisionMetricsCollector) -> None:
        with collector.track_decision("classification"):
            time.sleep(0.005)
        assert collector.decisions[0].latency_ms > 0

    def test_get_success_rate_no_outcome(
        self, collector: DecisionMetricsCollector
    ) -> None:
        with collector.track_decision("classification"):
            pass
        assert collector.get_success_rate() == 0.0

    def test_get_success_rate_all_true(
        self, collector: DecisionMetricsCollector
    ) -> None:
        for _ in range(4):
            with collector.track_decision("classification") as ctx:
                ctx.set_success(True)
        assert collector.get_success_rate() == pytest.approx(1.0)

    def test_get_success_rate_mixed(
        self, collector: DecisionMetricsCollector
    ) -> None:
        for success in (True, True, False, False):
            with collector.track_decision("classification") as ctx:
                ctx.set_success(success)
        assert collector.get_success_rate() == pytest.approx(0.5)

    def test_get_avg_confidence_empty(
        self, collector: DecisionMetricsCollector
    ) -> None:
        assert collector.get_avg_confidence() == 0.0

    def test_get_avg_confidence_with_data(
        self, collector: DecisionMetricsCollector
    ) -> None:
        for conf in (0.8, 0.9):
            with collector.track_decision("classification") as ctx:
                ctx.set_confidence(conf)
        assert collector.get_avg_confidence() == pytest.approx(0.85)

    def test_get_latency_percentiles_empty(
        self, collector: DecisionMetricsCollector
    ) -> None:
        p = collector.get_latency_percentiles()
        assert p == {"p50": 0.0, "p95": 0.0, "p99": 0.0}

    def test_get_latency_percentiles_with_data(
        self, collector: DecisionMetricsCollector
    ) -> None:
        for _ in range(10):
            with collector.track_decision("classification"):
                pass
        p = collector.get_latency_percentiles()
        assert "p50" in p and "p95" in p and "p99" in p

    def test_get_cost_analysis_empty(
        self, collector: DecisionMetricsCollector
    ) -> None:
        result = collector.get_cost_analysis()
        assert result["total_cost_usd"] == 0.0
        assert result["decisions_count"] == 0

    def test_get_cost_analysis_with_data(
        self, collector: DecisionMetricsCollector
    ) -> None:
        for cost in (0.01, 0.02):
            with collector.track_decision("generation") as ctx:
                ctx.add_cost(cost)
                ctx.add_tokens(100)
        result = collector.get_cost_analysis()
        assert result["total_cost_usd"] == pytest.approx(0.03)
        assert result["decisions_count"] == 2

    def test_filter_by_decision_type(
        self, collector: DecisionMetricsCollector
    ) -> None:
        with collector.track_decision("classification") as ctx:
            ctx.set_success(True)
        with collector.track_decision("generation") as ctx:
            ctx.set_success(False)
        rate = collector.get_success_rate(decision_type=DecisionType.CLASSIFICATION)
        assert rate == pytest.approx(1.0)

    def test_custom_decision_id(
        self, collector: DecisionMetricsCollector
    ) -> None:
        with collector.track_decision("classification", decision_id="my_id"):
            pass
        assert collector.decisions[0].decision_id == "my_id"


# ===========================================================================
# LLMMetricsCollector / LLMCallTracker
# ===========================================================================


class TestLLMMetricsCollector:
    @pytest.fixture()
    def collector(self) -> LLMMetricsCollector:
        return LLMMetricsCollector(agent_id="llm_agent")

    def test_start_call_returns_tracker(
        self, collector: LLMMetricsCollector
    ) -> None:
        tracker = collector.start_call(provider="anthropic", model="claude-sonnet-4")
        assert isinstance(tracker, LLMCallTracker)

    def test_calculate_cost_known_model(self) -> None:
        cost = LLMMetricsCollector.calculate_cost("claude-sonnet-4", 1000, 500)
        assert cost > 0.0

    def test_calculate_cost_unknown_model_uses_default(self) -> None:
        cost = LLMMetricsCollector.calculate_cost("unknown-model-xyz", 1000, 500)
        assert cost > 0.0

    def test_calculate_cost_gpt4(self) -> None:
        cost_gpt4 = LLMMetricsCollector.calculate_cost("gpt-4", 1000, 500)
        cost_sonnet = LLMMetricsCollector.calculate_cost("claude-sonnet-4", 1000, 500)
        assert cost_gpt4 > cost_sonnet  # gpt-4 is more expensive

    def test_calculate_cost_zero_tokens(self) -> None:
        assert LLMMetricsCollector.calculate_cost("gpt-4", 0, 0) == 0.0

    def test_decision_id_passed_to_tracker(self) -> None:
        from uuid import uuid4

        dec_id = uuid4()
        collector = LLMMetricsCollector(agent_id="a", decision_id=dec_id)
        tracker = collector.start_call(provider="openai", model="gpt-4")
        assert tracker.decision_id == dec_id


class TestLLMCallTracker:
    @pytest.fixture()
    def tracker(self) -> LLMCallTracker:
        return LLMCallTracker(
            agent_id="agent",
            provider="anthropic",
            model="claude-sonnet-4",
            temperature=0.7,
            max_tokens=1024,
        )

    def test_complete_returns_llm_metrics(
        self, tracker: LLMCallTracker
    ) -> None:
        from agentability.models import LLMMetrics

        metrics = tracker.complete(
            prompt_tokens=500, completion_tokens=200, finish_reason="end_turn"
        )
        assert isinstance(metrics, LLMMetrics)
        assert metrics.total_tokens == 700

    def test_cost_calculated_on_complete(
        self, tracker: LLMCallTracker
    ) -> None:
        metrics = tracker.complete(prompt_tokens=1_000_000, completion_tokens=0)
        assert metrics.cost_usd == pytest.approx(3.0)  # claude-sonnet-4 input: $3/M

    def test_latency_positive(self, tracker: LLMCallTracker) -> None:
        time.sleep(0.005)
        metrics = tracker.complete(prompt_tokens=10, completion_tokens=5)
        assert metrics.latency_ms > 0

    def test_record_first_token(self, tracker: LLMCallTracker) -> None:
        tracker.record_first_token()
        metrics = tracker.complete(prompt_tokens=10, completion_tokens=5)
        assert metrics.time_to_first_token_ms is not None
        assert metrics.time_to_first_token_ms >= 0

    def test_record_first_token_only_once(
        self, tracker: LLMCallTracker
    ) -> None:
        tracker.record_first_token()
        t1 = tracker._first_token_time
        time.sleep(0.005)
        tracker.record_first_token()  # should be ignored
        assert tracker._first_token_time == t1

    def test_record_chunk_increments(self, tracker: LLMCallTracker) -> None:
        tracker.record_chunk()
        tracker.record_chunk()
        assert tracker.chunks_received == 2

    def test_record_retry_increments(self, tracker: LLMCallTracker) -> None:
        tracker.record_retry()
        assert tracker.retry_count == 1

    def test_record_rate_limit(self, tracker: LLMCallTracker) -> None:
        tracker.record_rate_limit()
        assert tracker.rate_limited is True

    def test_streaming_fields_stored(self, tracker: LLMCallTracker) -> None:
        st = LLMCallTracker(
            agent_id="a",
            provider="anthropic",
            model="claude-haiku-4",
            is_streaming=True,
        )
        st.record_first_token()
        st.record_chunk()
        st.record_chunk()
        metrics = st.complete(prompt_tokens=100, completion_tokens=50)
        assert metrics.is_streaming is True
        assert metrics.chunks_received == 2
        assert metrics.time_to_first_token_ms is not None

    def test_no_first_token_gives_none_ttft(
        self, tracker: LLMCallTracker
    ) -> None:
        metrics = tracker.complete(prompt_tokens=10, completion_tokens=5)
        assert metrics.time_to_first_token_ms is None

    def test_metadata_passed_to_metrics(
        self, tracker: LLMCallTracker
    ) -> None:
        metrics = tracker.complete(
            prompt_tokens=10, completion_tokens=5, custom_key="custom_val"
        )
        assert metrics.metadata.get("custom_key") == "custom_val"


# ===========================================================================
# MemoryMetricsCollector / helpers
# ===========================================================================


class TestMemoryMetricsCollector:
    def test_start_operation_returns_tracker(self) -> None:
        collector = MemoryMetricsCollector(agent_id="rag")
        tracker = collector.start_operation(
            MemoryType.VECTOR, MemoryOperation.RETRIEVE
        )
        from agentability.metrics.memory_metrics import MemoryOperationTracker

        assert isinstance(tracker, MemoryOperationTracker)

    def test_complete_returns_memory_metrics(self) -> None:
        from agentability.models import MemoryMetrics

        collector = MemoryMetricsCollector(agent_id="rag")
        tracker = collector.start_operation(
            MemoryType.VECTOR, MemoryOperation.RETRIEVE
        )
        metrics = tracker.complete(items_processed=10, avg_similarity=0.82)
        assert isinstance(metrics, MemoryMetrics)
        assert metrics.items_processed == 10

    def test_latency_positive(self) -> None:
        collector = MemoryMetricsCollector(agent_id="rag")
        tracker = collector.start_operation(
            MemoryType.VECTOR, MemoryOperation.RETRIEVE
        )
        time.sleep(0.005)
        metrics = tracker.complete(items_processed=5)
        assert metrics.latency_ms > 0

    def test_bytes_processed_passed_through(self) -> None:
        collector = MemoryMetricsCollector(agent_id="rag")
        tracker = collector.start_operation(
            MemoryType.EPISODIC, MemoryOperation.STORE
        )
        metrics = tracker.complete(items_processed=1, bytes_processed=1024)
        assert metrics.bytes_processed == 1024


class TestRetrievalHelpers:
    def test_precision_all_relevant(self) -> None:
        assert calculate_retrieval_precision([1, 2, 3], [1, 2, 3]) == pytest.approx(
            1.0
        )

    def test_precision_none_relevant(self) -> None:
        assert calculate_retrieval_precision([1, 2, 3], [4, 5, 6]) == pytest.approx(
            0.0
        )

    def test_precision_empty_retrieved(self) -> None:
        assert calculate_retrieval_precision([], [1, 2]) == 0.0

    def test_precision_partial(self) -> None:
        assert calculate_retrieval_precision([1, 2, 3, 4], [1, 2]) == pytest.approx(
            0.5
        )

    def test_recall_all_retrieved(self) -> None:
        assert calculate_retrieval_recall([1, 2, 3], [1, 2, 3]) == pytest.approx(1.0)

    def test_recall_empty_relevant(self) -> None:
        assert calculate_retrieval_recall([1, 2], []) == 0.0

    def test_recall_partial(self) -> None:
        assert calculate_retrieval_recall([1, 2], [1, 2, 3, 4]) == pytest.approx(0.5)

    def test_similarity_stats_empty(self) -> None:
        result = calculate_similarity_stats([])
        assert result["avg_similarity"] == 0.0

    def test_similarity_stats_values(self) -> None:
        result = calculate_similarity_stats([0.8, 0.9, 0.7])
        assert result["avg_similarity"] == pytest.approx(0.8)
        assert result["min_similarity"] == pytest.approx(0.7)
        assert result["max_similarity"] == pytest.approx(0.9)


# ===========================================================================
# ConflictMetricsCollector
# ===========================================================================


class TestConflictMetricsCollector:
    @pytest.fixture()
    def collector(self) -> ConflictMetricsCollector:
        return ConflictMetricsCollector()

    def _make_positions(
        self, agents: list[str], confidences: list[float]
    ) -> list[AgentPosition]:
        return [
            AgentPosition(
                agent_id=a, position=f"pos_{a}", confidence=c
            )
            for a, c in zip(agents, confidences)
        ]

    def test_record_conflict_returns_id(
        self, collector: ConflictMetricsCollector
    ) -> None:
        positions = self._make_positions(["risk", "sales"], [0.85, 0.90])
        conflict_id = collector.record_conflict(
            conflict_type="decision_disagreement",
            agents=["risk", "sales"],
            positions=positions,
        )
        assert isinstance(conflict_id, str)

    def test_conflict_stored(self, collector: ConflictMetricsCollector) -> None:
        positions = self._make_positions(["a", "b"], [0.7, 0.8])
        collector.record_conflict(
            "decision_disagreement", ["a", "b"], positions
        )
        assert len(collector.conflicts) == 1

    def test_custom_conflict_id(self, collector: ConflictMetricsCollector) -> None:
        positions = self._make_positions(["a", "b"], [0.7, 0.8])
        cid = collector.record_conflict(
            "decision_disagreement", ["a", "b"], positions,
            conflict_id="my_conflict"
        )
        assert cid == "my_conflict"

    def test_resolve_conflict(self, collector: ConflictMetricsCollector) -> None:
        positions = self._make_positions(["a", "b"], [0.7, 0.9])
        cid = collector.record_conflict("decision_disagreement", ["a", "b"], positions)
        collector.resolve_conflict(
            cid, "confidence_based", "approve", 50.0, consensus_reached=True
        )
        conflict = collector.conflicts[0]
        assert conflict.consensus_reached is True
        assert conflict.resolution_strategy == ResolutionStrategy.CONFIDENCE_BASED

    def test_get_conflict_rate_empty(
        self, collector: ConflictMetricsCollector
    ) -> None:
        assert collector.get_conflict_rate() == 0.0

    def test_get_conflict_rate_with_data(
        self, collector: ConflictMetricsCollector
    ) -> None:
        for _ in range(5):
            positions = self._make_positions(["a", "b"], [0.6, 0.7])
            collector.record_conflict("decision_disagreement", ["a", "b"], positions)
        rate = collector.get_conflict_rate(time_window_hours=24)
        assert rate > 0.0

    def test_get_conflict_matrix(self, collector: ConflictMetricsCollector) -> None:
        positions = self._make_positions(["a", "b"], [0.7, 0.8])
        collector.record_conflict("decision_disagreement", ["a", "b"], positions)
        matrix = collector.get_agent_conflict_matrix()
        assert len(matrix) == 1

    def test_get_most_conflicting_pairs(
        self, collector: ConflictMetricsCollector
    ) -> None:
        for _ in range(3):
            positions = self._make_positions(["a", "b"], [0.7, 0.8])
            collector.record_conflict("decision_disagreement", ["a", "b"], positions)
        pairs = collector.get_most_conflicting_pairs(top_n=1)
        assert len(pairs) == 1
        assert pairs[0][1] == 3

    def test_get_resolution_effectiveness_empty_strategy(
        self, collector: ConflictMetricsCollector
    ) -> None:
        result = collector.get_resolution_effectiveness()
        assert "voting" in result
        assert result["voting"]["total_uses"] == 0

    def test_get_resolution_effectiveness_specific(
        self, collector: ConflictMetricsCollector
    ) -> None:
        positions = self._make_positions(["a", "b"], [0.7, 0.9])
        cid = collector.record_conflict("decision_disagreement", ["a", "b"], positions)
        collector.resolve_conflict(cid, "voting", "yes", 30.0, consensus_reached=True)
        result = collector.get_resolution_effectiveness(strategy="voting")
        assert result["voting"]["total_uses"] == 1
        assert result["voting"]["consensus_rate"] == pytest.approx(1.0)

    def test_get_conflict_by_type(
        self, collector: ConflictMetricsCollector
    ) -> None:
        for conflict_type in ("decision_disagreement", "resource_contention"):
            positions = self._make_positions(["a", "b"], [0.7, 0.8])
            collector.record_conflict(conflict_type, ["a", "b"], positions)
        counts = collector.get_conflict_by_type()
        assert counts["decision_disagreement"] == 1
        assert counts["resource_contention"] == 1

    def test_get_avg_severity_empty(
        self, collector: ConflictMetricsCollector
    ) -> None:
        assert collector.get_avg_severity() == 0.0

    def test_analyze_agent_behavior_no_conflicts(
        self, collector: ConflictMetricsCollector
    ) -> None:
        result = collector.analyze_agent_behavior("ghost_agent")
        assert result["total_conflicts"] == 0

    def test_analyze_agent_behavior_with_data(
        self, collector: ConflictMetricsCollector
    ) -> None:
        for _ in range(3):
            positions = self._make_positions(["risk", "sales"], [0.8, 0.7])
            collector.record_conflict("decision_disagreement", ["risk", "sales"], positions)
        result = collector.analyze_agent_behavior("risk")
        assert result["total_conflicts"] == 3
        assert result["most_common_conflict_type"] == "decision_disagreement"

    def test_game_theoretic_analysis_not_found(
        self, collector: ConflictMetricsCollector
    ) -> None:
        result = collector.get_game_theoretic_analysis("nonexistent")
        assert result == {}

    def test_game_theoretic_analysis_with_dominant(
        self, collector: ConflictMetricsCollector
    ) -> None:
        positions = [
            AgentPosition(agent_id="strong", position="yes", confidence=0.95),
            AgentPosition(agent_id="weak", position="no", confidence=0.3),
        ]
        cid = collector.record_conflict(
            "resource_contention", ["strong", "weak"], positions
        )
        result = collector.get_game_theoretic_analysis(cid)
        assert result["dominant_strategy_agent"] == "strong"
        assert result["is_zero_sum"] is True

    def test_single_agent_position_severity_zero(
        self, collector: ConflictMetricsCollector
    ) -> None:
        positions = [AgentPosition(agent_id="a", position="x", confidence=0.9)]
        collector.record_conflict("decision_disagreement", ["a"], positions)
        assert collector.conflicts[0].conflict_severity == 0.0

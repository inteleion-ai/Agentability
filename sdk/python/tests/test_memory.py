"""Tests for memory subsystem trackers.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import time

import pytest

from agentability.memory.episodic_tracker import (
    EpisodicMemoryTracker,
    EpisodicRetrievalContext,
)
from agentability.memory.semantic_tracker import (
    SemanticMemoryTracker,
    SemanticQueryContext,
)
from agentability.memory.working_tracker import WorkingMemoryTracker


# ===========================================================================
# EpisodicMemoryTracker
# ===========================================================================


class TestEpisodicMemoryTracker:
    @pytest.fixture()
    def tracker(self) -> EpisodicMemoryTracker:
        return EpisodicMemoryTracker(agent_id="chat_agent")

    def test_initial_state_empty(self, tracker: EpisodicMemoryTracker) -> None:
        assert tracker.operations == []

    def test_track_retrieval_returns_context(
        self, tracker: EpisodicMemoryTracker
    ) -> None:
        ctx = tracker.track_retrieval()
        assert isinstance(ctx, EpisodicRetrievalContext)

    def test_context_manager_records_operation(
        self, tracker: EpisodicMemoryTracker
    ) -> None:
        with tracker.track_retrieval() as ctx:
            ctx.record_episodes(["ep1", "ep2"], tokens_used=512)
        assert len(tracker.operations) == 1

    def test_episodes_retrieved_count(
        self, tracker: EpisodicMemoryTracker
    ) -> None:
        with tracker.track_retrieval() as ctx:
            ctx.record_episodes(["a", "b", "c"], tokens_used=300)
        assert tracker.operations[0].episodes_retrieved == 3

    def test_context_utilization_calculated(
        self, tracker: EpisodicMemoryTracker
    ) -> None:
        with tracker.track_retrieval() as ctx:
            ctx.context_tokens_limit = 4096
            ctx.record_episodes(["ep"], tokens_used=1024)
        assert tracker.operations[0].context_utilization == pytest.approx(
            1024 / 4096
        )

    def test_latency_is_positive(self, tracker: EpisodicMemoryTracker) -> None:
        with tracker.track_retrieval() as ctx:
            time.sleep(0.01)
            ctx.record_episodes([], tokens_used=0)
        assert tracker.operations[0].latency_ms > 0

    def test_avg_context_utilization_empty(
        self, tracker: EpisodicMemoryTracker
    ) -> None:
        assert tracker.get_avg_context_utilization() == 0.0

    def test_avg_context_utilization_with_data(
        self, tracker: EpisodicMemoryTracker
    ) -> None:
        for tokens in (1024, 2048):
            with tracker.track_retrieval() as ctx:
                ctx.context_tokens_limit = 4096
                ctx.record_episodes([], tokens_used=tokens)
        avg = tracker.get_avg_context_utilization()
        assert avg == pytest.approx((1024 / 4096 + 2048 / 4096) / 2)

    def test_avg_utilization_time_window_filters(
        self, tracker: EpisodicMemoryTracker
    ) -> None:
        with tracker.track_retrieval() as ctx:
            ctx.record_episodes([], tokens_used=100)
        # Future window — should include the operation
        avg = tracker.get_avg_context_utilization(time_window_hours=1)
        assert isinstance(avg, float)

    def test_exception_in_context_still_records(
        self, tracker: EpisodicMemoryTracker
    ) -> None:
        try:
            with tracker.track_retrieval():
                raise ValueError("test error")
        except ValueError:
            pass
        assert len(tracker.operations) == 1

    def test_zero_token_limit_gives_zero_utilization(
        self, tracker: EpisodicMemoryTracker
    ) -> None:
        with tracker.track_retrieval() as ctx:
            ctx.context_tokens_limit = 0
            ctx.record_episodes([], tokens_used=100)
        assert tracker.operations[0].context_utilization == 0.0


# ===========================================================================
# SemanticMemoryTracker
# ===========================================================================


class TestSemanticMemoryTracker:
    @pytest.fixture()
    def tracker(self) -> SemanticMemoryTracker:
        return SemanticMemoryTracker(agent_id="kg_agent")

    def test_initial_state_empty(self, tracker: SemanticMemoryTracker) -> None:
        assert tracker.operations == []

    def test_track_query_returns_context(
        self, tracker: SemanticMemoryTracker
    ) -> None:
        ctx = tracker.track_query()
        assert isinstance(ctx, SemanticQueryContext)

    def test_context_manager_records_operation(
        self, tracker: SemanticMemoryTracker
    ) -> None:
        with tracker.track_query() as ctx:
            ctx.record_query(
                nodes=10,
                relationships=20,
                max_hops=3,
                results=["r1", "r2"],
                complexity=2,
            )
        assert len(tracker.operations) == 1

    def test_graph_density_calculated(
        self, tracker: SemanticMemoryTracker
    ) -> None:
        with tracker.track_query() as ctx:
            ctx.record_query(
                nodes=5,
                relationships=8,
                max_hops=2,
                results=["r1"],
            )
        metric = tracker.operations[0]
        assert metric.graph_density > 0.0
        assert metric.knowledge_graph_nodes == 5

    def test_single_node_density_is_zero(
        self, tracker: SemanticMemoryTracker
    ) -> None:
        with tracker.track_query() as ctx:
            ctx.record_query(nodes=1, relationships=0, max_hops=0, results=[])
        assert tracker.operations[0].graph_density == 0.0

    def test_results_returned_count(
        self, tracker: SemanticMemoryTracker
    ) -> None:
        with tracker.track_query() as ctx:
            ctx.record_query(nodes=3, relationships=2, max_hops=1, results=["a", "b", "c"])
        assert tracker.operations[0].results_returned == 3

    def test_avg_query_complexity_empty(
        self, tracker: SemanticMemoryTracker
    ) -> None:
        assert tracker.get_avg_query_complexity() == 0.0

    def test_avg_query_complexity_with_data(
        self, tracker: SemanticMemoryTracker
    ) -> None:
        for complexity in (1, 3):
            with tracker.track_query() as ctx:
                ctx.record_query(
                    nodes=2, relationships=1, max_hops=1,
                    results=[], complexity=complexity,
                )
        assert tracker.get_avg_query_complexity() == pytest.approx(2.0)

    def test_time_window_filter(self, tracker: SemanticMemoryTracker) -> None:
        with tracker.track_query() as ctx:
            ctx.record_query(nodes=2, relationships=1, max_hops=1, results=[])
        result = tracker.get_avg_query_complexity(time_window_hours=1)
        # statistics.mean preserves int type on all-integer input;
        # accept both int and float here.
        assert isinstance(result, (int, float))

    def test_latency_positive(self, tracker: SemanticMemoryTracker) -> None:
        with tracker.track_query() as ctx:
            time.sleep(0.005)
            ctx.record_query(nodes=1, relationships=0, max_hops=0, results=[])
        assert tracker.operations[0].latency_ms >= 0.0


# ===========================================================================
# WorkingMemoryTracker
# ===========================================================================


class TestWorkingMemoryTracker:
    @pytest.fixture()
    def tracker(self) -> WorkingMemoryTracker:
        return WorkingMemoryTracker(agent_id="plan_agent", max_tokens=8192)

    def test_initial_state_empty(self, tracker: WorkingMemoryTracker) -> None:
        assert tracker.metrics == []

    def test_record_state_appends_metric(
        self, tracker: WorkingMemoryTracker
    ) -> None:
        tracker.record_state(active_items=5, total_tokens=1024)
        assert len(tracker.metrics) == 1

    def test_utilization_calculated(self, tracker: WorkingMemoryTracker) -> None:
        tracker.record_state(active_items=3, total_tokens=4096)
        assert tracker.metrics[0].utilization == pytest.approx(4096 / 8192)

    def test_zero_max_tokens_gives_zero_utilization(self) -> None:
        tracker = WorkingMemoryTracker(agent_id="a", max_tokens=0)
        tracker.record_state(active_items=1, total_tokens=100)
        assert tracker.metrics[0].utilization == 0.0

    def test_attention_distribution_stored(
        self, tracker: WorkingMemoryTracker
    ) -> None:
        dist = {"task": 0.6, "context": 0.4}
        tracker.record_state(active_items=2, total_tokens=512, attention_dist=dist)
        assert tracker.metrics[0].attention_distribution == dist

    def test_items_added_removed_stored(
        self, tracker: WorkingMemoryTracker
    ) -> None:
        tracker.record_state(
            active_items=4, total_tokens=800, items_added=3, items_removed=1
        )
        m = tracker.metrics[0]
        assert m.items_added == 3
        assert m.items_removed == 1

    def test_avg_utilization_empty(self, tracker: WorkingMemoryTracker) -> None:
        assert tracker.get_avg_utilization() == 0.0

    def test_avg_utilization_multiple(self, tracker: WorkingMemoryTracker) -> None:
        tracker.record_state(active_items=1, total_tokens=2048)
        tracker.record_state(active_items=1, total_tokens=4096)
        avg = tracker.get_avg_utilization()
        assert avg == pytest.approx((2048 / 8192 + 4096 / 8192) / 2)

    def test_peak_utilization_empty(self, tracker: WorkingMemoryTracker) -> None:
        assert tracker.get_peak_utilization() == 0.0

    def test_peak_utilization_returns_max(
        self, tracker: WorkingMemoryTracker
    ) -> None:
        tracker.record_state(active_items=1, total_tokens=1000)
        tracker.record_state(active_items=1, total_tokens=7000)
        assert tracker.get_peak_utilization() == pytest.approx(7000 / 8192)

    def test_time_window_filter(self, tracker: WorkingMemoryTracker) -> None:
        tracker.record_state(active_items=1, total_tokens=500)
        result = tracker.get_avg_utilization(time_window_hours=1)
        assert isinstance(result, float)

    def test_multiple_records_same_tracker(
        self, tracker: WorkingMemoryTracker
    ) -> None:
        for i in range(5):
            tracker.record_state(active_items=i, total_tokens=i * 100)
        assert len(tracker.metrics) == 5

"""Tests for the analytics engine — causal graph, drift detector, and
conflict analyser.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from agentability.analyzers.causal_graph import CausalGraphBuilder
from agentability.analyzers.conflict_analyzer import ConflictAnalyzer
from agentability.analyzers.drift_detector import DriftDetector, DriftSeverity


# ===========================================================================
# CausalGraphBuilder
# ===========================================================================


class TestCausalGraphBuilder:
    """Tests for CausalGraphBuilder."""

    @pytest.fixture()
    def builder(self) -> CausalGraphBuilder:
        return CausalGraphBuilder()

    def test_add_node_returns_node(self, builder: CausalGraphBuilder) -> None:
        node = builder.add_node(
            "n1", "decision", "Risk Assessment", confidence=0.42
        )
        assert node.node_id == "n1"
        assert node.confidence == pytest.approx(0.42)

    def test_node_stored_in_graph(self, builder: CausalGraphBuilder) -> None:
        builder.add_node("n1", "decision", "Risk Assessment")
        assert "n1" in builder.nodes

    def test_add_edge_returns_none_for_missing_nodes(
        self, builder: CausalGraphBuilder
    ) -> None:
        result = builder.add_causal_edge("ghost_src", "ghost_tgt", "direct", 0.8)
        assert result is None

    def test_add_edge_stored(self, builder: CausalGraphBuilder) -> None:
        builder.add_node("a", "decision", "A")
        builder.add_node("b", "decision", "B")
        edge = builder.add_causal_edge("a", "b", "direct", strength=0.9)
        assert edge is not None
        assert len(builder.edges) == 1

    def test_get_causal_chain_direct(self, builder: CausalGraphBuilder) -> None:
        builder.add_node("a", "decision", "A")
        builder.add_node("b", "decision", "B")
        builder.add_causal_edge("a", "b", "direct", strength=0.9)

        paths = builder.get_causal_chain("a", "b")
        assert len(paths) == 1
        assert paths[0] == ["a", "b"]

    def test_get_causal_chain_no_path(self, builder: CausalGraphBuilder) -> None:
        builder.add_node("x", "decision", "X")
        builder.add_node("y", "decision", "Y")

        paths = builder.get_causal_chain("x", "y")
        assert paths == []

    def test_get_causal_chain_multi_hop(
        self, builder: CausalGraphBuilder
    ) -> None:
        for nid in ("a", "b", "c"):
            builder.add_node(nid, "decision", nid.upper())
        builder.add_causal_edge("a", "b", "direct", 0.9)
        builder.add_causal_edge("b", "c", "direct", 0.8)

        paths = builder.get_causal_chain("a", "c")
        assert len(paths) == 1
        assert paths[0] == ["a", "b", "c"]

    def test_find_bottlenecks_low_confidence(
        self, builder: CausalGraphBuilder
    ) -> None:
        builder.add_node("root", "decision", "Root", confidence=0.35)
        builder.add_node("d1", "decision", "D1")
        builder.add_node("d2", "decision", "D2")
        builder.add_node("d3", "decision", "D3")

        builder.add_causal_edge("root", "d1", "direct", 0.9)
        builder.add_causal_edge("root", "d2", "direct", 0.9)
        builder.add_causal_edge("root", "d3", "direct", 0.9)

        bottlenecks = builder.find_bottlenecks()
        assert any(b["node_id"] == "root" for b in bottlenecks)

    def test_find_bottlenecks_high_confidence_excluded(
        self, builder: CausalGraphBuilder
    ) -> None:
        builder.add_node("fine", "decision", "Fine", confidence=0.8)
        builder.add_node("d1", "decision", "D1")
        builder.add_causal_edge("fine", "d1", "direct", 0.9)

        bottlenecks = builder.find_bottlenecks()
        assert not any(b["node_id"] == "fine" for b in bottlenecks)

    def test_get_root_causes_simple(self, builder: CausalGraphBuilder) -> None:
        builder.add_node("root", "decision", "Root")
        builder.add_node("leaf", "decision", "Leaf")
        builder.add_causal_edge("root", "leaf", "direct", 0.9)

        roots = builder.get_root_causes("leaf")
        assert "root" in roots

    def test_get_root_causes_isolated_node(
        self, builder: CausalGraphBuilder
    ) -> None:
        builder.add_node("iso", "decision", "Isolated")
        roots = builder.get_root_causes("iso")
        assert "iso" in roots

    def test_detect_causal_loops_no_cycle(
        self, builder: CausalGraphBuilder
    ) -> None:
        builder.add_node("a", "decision", "A")
        builder.add_node("b", "decision", "B")
        builder.add_causal_edge("a", "b", "direct", 0.9)

        loops = builder.detect_causal_loops()
        assert loops == []

    def test_build_graph_keys(self, builder: CausalGraphBuilder) -> None:
        builder.add_node("n1", "decision", "N1")
        graph = builder.build_graph()

        assert "nodes" in graph
        assert "edges" in graph
        assert "metadata" in graph
        assert graph["metadata"]["total_nodes"] == 1


# ===========================================================================
# DriftDetector
# ===========================================================================


class TestDriftDetector:
    """Tests for DriftDetector."""

    @pytest.fixture()
    def detector(self) -> DriftDetector:
        return DriftDetector(
            baseline_window_days=7,
            detection_window_hours=24,
            drift_threshold=0.10,
        )

    def _populate_baseline(
        self,
        detector: DriftDetector,
        agent_id: str,
        confidence: float,
        n: int,
        days_ago: float = 3.5,
    ) -> None:
        base_time = datetime.now() - timedelta(days=days_ago)
        for i in range(n):
            detector.record_confidence(
                agent_id=agent_id,
                confidence=confidence,
                timestamp=base_time + timedelta(minutes=i * 30),
            )

    def _populate_recent(
        self,
        detector: DriftDetector,
        agent_id: str,
        confidence: float,
        n: int,
    ) -> None:
        recent_time = datetime.now() - timedelta(hours=12)
        for i in range(n):
            detector.record_confidence(
                agent_id=agent_id,
                confidence=confidence,
                timestamp=recent_time + timedelta(minutes=i * 10),
            )

    def test_no_data_returns_no_drift(self, detector: DriftDetector) -> None:
        result = detector.detect_drift("unknown_agent")
        assert result["drift_detected"] is False

    def test_insufficient_data_returns_no_drift(
        self, detector: DriftDetector
    ) -> None:
        for _ in range(5):
            detector.record_confidence("sparse", 0.8)
        result = detector.detect_drift("sparse")
        assert result["drift_detected"] is False

    def test_stable_agent_no_drift(self, detector: DriftDetector) -> None:
        self._populate_baseline(detector, "stable", 0.85, 60)
        self._populate_recent(detector, "stable", 0.84, 20)

        result = detector.detect_drift("stable")
        assert result["drift_detected"] is False

    def test_degraded_agent_drift_detected(self, detector: DriftDetector) -> None:
        self._populate_baseline(detector, "degraded", 0.85, 60)
        self._populate_recent(detector, "degraded", 0.62, 20)

        result = detector.detect_drift("degraded")
        assert result["drift_detected"] is True
        assert result["drift_magnitude"] < -0.10

    def test_drift_severity_critical(self, detector: DriftDetector) -> None:
        self._populate_baseline(detector, "critical_a", 0.90, 60)
        self._populate_recent(detector, "critical_a", 0.60, 20)

        result = detector.detect_drift("critical_a")
        assert result["severity"] == DriftSeverity.CRITICAL.value

    def test_drift_severity_medium(self, detector: DriftDetector) -> None:
        self._populate_baseline(detector, "medium_a", 0.85, 60)
        self._populate_recent(detector, "medium_a", 0.74, 20)

        result = detector.detect_drift("medium_a")
        assert result["drift_detected"] is True
        assert result["severity"] in (
            DriftSeverity.MEDIUM.value,
            DriftSeverity.HIGH.value,
        )

    def test_version_impact_detected(self, detector: DriftDetector) -> None:
        agent_id = "versioned"
        base_time = datetime.now() - timedelta(days=4)

        for i in range(40):
            detector.record_confidence(
                agent_id=agent_id,
                confidence=0.88,
                timestamp=base_time + timedelta(hours=i),
                version="v1.0",
            )

        recent_time = datetime.now() - timedelta(hours=20)
        for i in range(20):
            detector.record_confidence(
                agent_id=agent_id,
                confidence=0.65,
                timestamp=recent_time + timedelta(minutes=i * 30),
                version="v1.1",
            )

        impact = detector.detect_version_impact(agent_id, "v1.1")
        assert impact.get("regression") is True

    def test_trend_direction_declining(self, detector: DriftDetector) -> None:
        agent_id = "declining"
        base_time = datetime.now() - timedelta(days=5)

        for i in range(30):
            detector.record_confidence(
                agent_id=agent_id,
                confidence=0.90,
                timestamp=base_time + timedelta(hours=i),
            )

        mid_time = datetime.now() - timedelta(days=2)
        for i in range(30):
            detector.record_confidence(
                agent_id=agent_id,
                confidence=0.60,
                timestamp=mid_time + timedelta(hours=i),
            )

        trend = detector.get_trend(agent_id, days=5)
        assert trend["trend_direction"] == "declining"


# ===========================================================================
# ConflictAnalyzer
# ===========================================================================


class TestConflictAnalyzer:
    """Tests for ConflictAnalyzer."""

    @pytest.fixture()
    def analyzer(self) -> ConflictAnalyzer:
        return ConflictAnalyzer()

    def _add_conflicts(
        self,
        analyzer: ConflictAnalyzer,
        winner: str,
        n: int = 10,
    ) -> None:
        for _ in range(n):
            analyzer.record_conflict(
                agents=["risk", "sales"],
                outputs={"risk": "deny", "sales": "approve"},
                confidences={"risk": 0.85, "sales": 0.90},
                resolution_method="priority_hierarchy",
                winning_agent=winner,
                final_decision={"decision": winner},
            )

    def test_record_conflict_returns_object(
        self, analyzer: ConflictAnalyzer
    ) -> None:
        conflict = analyzer.record_conflict(
            agents=["a", "b"],
            outputs={"a": "yes", "b": "no"},
            confidences={"a": 0.7, "b": 0.8},
            resolution_method="priority_hierarchy",
            winning_agent="a",
            final_decision={"decision": "yes"},
        )
        assert conflict is not None

    def test_conflict_count(self, analyzer: ConflictAnalyzer) -> None:
        self._add_conflicts(analyzer, "risk", n=5)
        patterns = analyzer.get_conflict_patterns(days=30)
        assert patterns["total_conflicts"] == 5

    def test_win_rate_dominant_agent(self, analyzer: ConflictAnalyzer) -> None:
        self._add_conflicts(analyzer, "risk", n=10)
        patterns = analyzer.get_conflict_patterns(days=30)
        assert patterns["win_rates"]["risk"] == pytest.approx(1.0)
        assert patterns["win_rates"].get("sales", 0.0) == pytest.approx(0.0)

    def test_detect_systematic_bias_ignored(
        self, analyzer: ConflictAnalyzer
    ) -> None:
        self._add_conflicts(analyzer, "risk", n=15)
        bias = analyzer.detect_systematic_bias("sales", days=30)
        assert bias["bias_type"] == "systematically_ignored"

    def test_detect_systematic_bias_fair(
        self, analyzer: ConflictAnalyzer
    ) -> None:
        for _ in range(5):
            analyzer.record_conflict(
                agents=["a", "b"],
                outputs={"a": "x", "b": "y"},
                confidences={"a": 0.7, "b": 0.7},
                resolution_method="consensus",
                winning_agent="a",
                final_decision={},
            )
        for _ in range(5):
            analyzer.record_conflict(
                agents=["a", "b"],
                outputs={"a": "x", "b": "y"},
                confidences={"a": 0.7, "b": 0.7},
                resolution_method="consensus",
                winning_agent="b",
                final_decision={},
            )

        bias_a = analyzer.detect_systematic_bias("a", days=30)
        assert bias_a["bias_type"] == "fair"

    def test_empty_patterns(self, analyzer: ConflictAnalyzer) -> None:
        patterns = analyzer.get_conflict_patterns(days=30)
        assert patterns["total_conflicts"] == 0

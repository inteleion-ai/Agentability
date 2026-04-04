"""Tests for capability scorer, policy evaluator, sampler, version tracker,
and extended analyzer coverage.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from agentability.analyzers.cost_analyzer import CostAnalyzer
from agentability.analyzers.lineage_tracer import LineageTracer
from agentability.analyzers.provenance import ProvenanceAnalyzer
from agentability.capability.scorer import AgentabilityScorer
from agentability.models import (
    CapabilityDimension,
    Decision,
    DecisionType,
    MemoryMetrics,
    MemoryOperation,
    MemoryType,
    PolicyType,
    PolicyViolation,
    ViolationSeverity,
)
from agentability.policies.evaluator import PolicyEvaluator, PolicyRule
from agentability.sampling.samplers import ImportanceScorer, SamplingStrategy, TraceSampler
from agentability.versioning.version_tracker import VersionTracker


# ===========================================================================
# AgentabilityScorer
# ===========================================================================


def _make_decision(
    agent_id: str = "a",
    confidence: float | None = 0.8,
    reasoning_steps: int = 3,
    uncertainties: int = 1,
    cost: float = 0.01,
    latency_ms: float = 300.0,
    constraints_violated: list[str] | None = None,
) -> Decision:
    return Decision(
        agent_id=agent_id,
        decision_type=DecisionType.CLASSIFICATION,
        confidence=confidence,
        reasoning=["step"] * reasoning_steps,
        uncertainties=["u"] * uncertainties,
        total_cost_usd=cost,
        latency_ms=latency_ms,
        constraints_violated=constraints_violated or [],
    )


class TestAgentabilityScorer:
    @pytest.fixture()
    def scorer(self) -> AgentabilityScorer:
        return AgentabilityScorer()

    def test_score_reasoning_empty_decisions(
        self, scorer: AgentabilityScorer
    ) -> None:
        score = scorer.score_reasoning([])
        assert score.score == 0.0
        assert score.evidence_count == 0

    def test_score_reasoning_with_decisions(
        self, scorer: AgentabilityScorer
    ) -> None:
        decisions = [_make_decision(reasoning_steps=5, uncertainties=2)] * 10
        score = scorer.score_reasoning(decisions)
        assert 0.0 <= score.score <= 100.0
        assert score.evidence_count == 10

    def test_score_reasoning_no_confidence(
        self, scorer: AgentabilityScorer
    ) -> None:
        decisions = [_make_decision(confidence=None)] * 5
        score = scorer.score_reasoning(decisions)
        assert score.score >= 0.0

    def test_score_memory_empty(self, scorer: AgentabilityScorer) -> None:
        score = scorer.score_memory([])
        assert score.score == 0.0

    def test_score_memory_with_ops(self, scorer: AgentabilityScorer) -> None:
        ops = [
            MemoryMetrics(
                agent_id="a",
                memory_type=MemoryType.VECTOR,
                operation=MemoryOperation.RETRIEVE,
                latency_ms=50.0,
                items_processed=10,
                retrieval_precision=0.9,
            )
        ] * 5
        score = scorer.score_memory(ops)
        assert score.score > 0.0
        assert score.dimension == CapabilityDimension.MEMORY

    def test_score_memory_no_precision(self, scorer: AgentabilityScorer) -> None:
        ops = [
            MemoryMetrics(
                agent_id="a",
                memory_type=MemoryType.VECTOR,
                operation=MemoryOperation.RETRIEVE,
                latency_ms=200.0,
                items_processed=5,
            )
        ] * 3
        score = scorer.score_memory(ops)
        assert score.score >= 0.0

    def test_score_safety_empty_decisions(
        self, scorer: AgentabilityScorer
    ) -> None:
        score = scorer.score_safety([], [])
        assert score.score == pytest.approx(100.0)

    def test_score_safety_with_violations(
        self, scorer: AgentabilityScorer
    ) -> None:
        decisions = [_make_decision(constraints_violated=["rule_1"])] * 5
        policy_violations = [
            PolicyViolation(
                rule_id="no_pii",
                rule_description="No PII",
                severity=ViolationSeverity.CRITICAL,
                agent_id="a",
            )
        ]
        score = scorer.score_safety(decisions, policy_violations)
        assert score.score < 100.0

    def test_score_efficiency_empty(self, scorer: AgentabilityScorer) -> None:
        score = scorer.score_efficiency([])
        assert score.score == 0.0

    def test_score_efficiency_with_decisions(
        self, scorer: AgentabilityScorer
    ) -> None:
        decisions = [_make_decision(cost=0.001, latency_ms=100.0)] * 10
        score = scorer.score_efficiency(decisions)
        assert score.score > 0.0
        assert score.dimension == CapabilityDimension.EFFICIENCY

    def test_score_efficiency_high_cost(
        self, scorer: AgentabilityScorer
    ) -> None:
        decisions = [_make_decision(cost=1.0, latency_ms=10000.0)] * 5
        score = scorer.score_efficiency(decisions)
        assert score.score >= 0.0

    def test_compute_composite_score_empty(
        self, scorer: AgentabilityScorer
    ) -> None:
        assert scorer.compute_composite_score({}) == 0.0

    def test_compute_composite_score_full(
        self, scorer: AgentabilityScorer
    ) -> None:
        decisions = [_make_decision()] * 20
        dim_scores = {
            CapabilityDimension.REASONING: scorer.score_reasoning(decisions),
            CapabilityDimension.EFFICIENCY: scorer.score_efficiency(decisions),
            CapabilityDimension.SAFETY: scorer.score_safety(decisions, []),
        }
        composite = scorer.compute_composite_score(dim_scores)
        assert 0.0 <= composite <= 100.0

    def test_confidence_helper_zero(self, scorer: AgentabilityScorer) -> None:
        from agentability.capability.scorer import AgentabilityScorer as S

        assert S._confidence(0) == 0.0

    def test_confidence_helper_grows_with_evidence(
        self, scorer: AgentabilityScorer
    ) -> None:
        from agentability.capability.scorer import AgentabilityScorer as S

        assert S._confidence(10) < S._confidence(100)


# ===========================================================================
# PolicyEvaluator
# ===========================================================================


class TestPolicyEvaluator:
    @pytest.fixture()
    def evaluator(self) -> PolicyEvaluator:
        return PolicyEvaluator()

    def test_default_rules_registered(self, evaluator: PolicyEvaluator) -> None:
        assert "no_pii" in evaluator.rules
        assert "max_cost" in evaluator.rules

    def test_clean_decision_no_violations(
        self, evaluator: PolicyEvaluator
    ) -> None:
        d = _make_decision(cost=0.01)
        violations = evaluator.evaluate_decision(d, "agent_a")
        assert violations == []

    def test_high_cost_triggers_violation(
        self, evaluator: PolicyEvaluator
    ) -> None:
        d = _make_decision(cost=0.10)
        violations = evaluator.evaluate_decision(d, "agent_a")
        rule_ids = [v.rule_id for v in violations]
        assert "max_cost" in rule_ids

    def test_pii_email_triggers_violation(
        self, evaluator: PolicyEvaluator
    ) -> None:
        d = Decision(
            agent_id="a",
            decision_type=DecisionType.GENERATION,
            output_data={"response": "contact user@example.com for details"},
        )
        violations = evaluator.evaluate_decision(d, "a")
        rule_ids = [v.rule_id for v in violations]
        assert "no_pii" in rule_ids

    def test_pii_ssn_triggers_violation(
        self, evaluator: PolicyEvaluator
    ) -> None:
        d = Decision(
            agent_id="a",
            decision_type=DecisionType.GENERATION,
            output_data={"ssn": "123-45-6789"},
        )
        violations = evaluator.evaluate_decision(d, "a")
        assert any(v.rule_id == "no_pii" for v in violations)

    def test_disabled_rule_not_evaluated(
        self, evaluator: PolicyEvaluator
    ) -> None:
        evaluator.rules["max_cost"].enabled = False
        d = _make_decision(cost=1.0)
        violations = evaluator.evaluate_decision(d, "a")
        assert not any(v.rule_id == "max_cost" for v in violations)

    def test_register_custom_rule(self, evaluator: PolicyEvaluator) -> None:
        def always_violate(
            decision: Decision,
        ) -> tuple[bool, dict]:
            return (False, {"reason": "always fails"})

        rule = PolicyRule(
            rule_id="always_fail",
            rule_type=PolicyType.COMPLIANCE,
            description="Always fails",
            evaluator=always_violate,
            severity=ViolationSeverity.LOW,
        )
        evaluator.register_rule(rule)
        d = _make_decision()
        violations = evaluator.evaluate_decision(d, "a")
        assert any(v.rule_id == "always_fail" for v in violations)

    def test_evaluator_exception_is_swallowed(
        self, evaluator: PolicyEvaluator
    ) -> None:
        def raises(_: Decision) -> tuple[bool, dict]:
            raise RuntimeError("boom")

        rule = PolicyRule(
            rule_id="boom_rule",
            rule_type=PolicyType.SAFETY,
            description="Raises",
            evaluator=raises,
            severity=ViolationSeverity.HIGH,
        )
        evaluator.register_rule(rule)
        d = _make_decision()
        # Should not raise
        evaluator.evaluate_decision(d, "a")

    def test_compliance_score_empty(self, evaluator: PolicyEvaluator) -> None:
        result = evaluator.get_compliance_score([])
        assert result["compliance_score"] == pytest.approx(100.0)
        assert result["total_violations"] == 0

    def test_compliance_score_with_violations(
        self, evaluator: PolicyEvaluator
    ) -> None:
        decisions = [_make_decision(cost=1.0)] * 3
        result = evaluator.get_compliance_score(decisions)
        assert result["compliance_score"] < 100.0
        assert result["total_violations"] > 0

    def test_compliance_score_critical_violations(
        self, evaluator: PolicyEvaluator
    ) -> None:
        decisions = [
            Decision(
                agent_id="a",
                decision_type=DecisionType.GENERATION,
                output_data={"email": "foo@bar.com"},
            )
        ] * 3
        result = evaluator.get_compliance_score(decisions)
        assert result["critical_violations"] > 0


# ===========================================================================
# TraceSampler / ImportanceScorer
# ===========================================================================


class TestTraceSampler:
    def test_always_strategy_always_samples(self) -> None:
        sampler = TraceSampler(strategy=SamplingStrategy.ALWAYS)
        for _ in range(10):
            assert sampler.should_sample_head({}) is True

    def test_never_strategy_never_samples(self) -> None:
        sampler = TraceSampler(strategy=SamplingStrategy.NEVER)
        for _ in range(10):
            assert sampler.should_sample_head({}) is False

    def test_probabilistic_rate_0_never_samples(self) -> None:
        sampler = TraceSampler(
            strategy=SamplingStrategy.PROBABILISTIC, sample_rate=0.0
        )
        for _ in range(20):
            assert sampler.should_sample_head({}) is False

    def test_probabilistic_rate_1_always_samples(self) -> None:
        sampler = TraceSampler(
            strategy=SamplingStrategy.PROBABILISTIC, sample_rate=1.0
        )
        for _ in range(10):
            assert sampler.should_sample_head({}) is True

    def test_head_based_samples_at_rate(self) -> None:
        sampler = TraceSampler(
            strategy=SamplingStrategy.HEAD_BASED, sample_rate=1.0
        )
        assert sampler.should_sample_head({}) is True

    def test_cost_aware_within_budget(self) -> None:
        sampler = TraceSampler(
            strategy=SamplingStrategy.COST_AWARE, cost_budget_per_day=10.0
        )
        assert sampler.should_sample_head({}) is True

    def test_cost_aware_exceeds_budget(self) -> None:
        sampler = TraceSampler(
            strategy=SamplingStrategy.COST_AWARE, cost_budget_per_day=5.0
        )
        sampler.record_cost(6.0)
        assert sampler.should_sample_head({}) is False

    def test_cost_aware_no_budget_always_true(self) -> None:
        sampler = TraceSampler(strategy=SamplingStrategy.COST_AWARE)
        assert sampler.should_sample_head({}) is True

    def test_importance_based_high_importance(self) -> None:
        sampler = TraceSampler(strategy=SamplingStrategy.IMPORTANCE_BASED)
        assert sampler.should_sample_head({"importance": 1.0}) is True

    def test_importance_based_zero_importance(self) -> None:
        sampler = TraceSampler(strategy=SamplingStrategy.IMPORTANCE_BASED)
        assert sampler.should_sample_head({"importance": 0.0}) is False

    def test_tail_based_non_tail_always_true(self) -> None:
        sampler = TraceSampler(strategy=SamplingStrategy.ALWAYS)
        d = _make_decision()
        assert sampler.should_sample_tail({}, d) is True

    def test_tail_based_low_confidence_retained(self) -> None:
        sampler = TraceSampler(
            strategy=SamplingStrategy.TAIL_BASED, sample_rate=0.0
        )
        d = _make_decision(confidence=0.3)
        assert sampler.should_sample_tail({}, d) is True

    def test_tail_based_high_cost_retained(self) -> None:
        sampler = TraceSampler(
            strategy=SamplingStrategy.TAIL_BASED, sample_rate=0.0
        )
        d = _make_decision(confidence=0.9, cost=0.50)
        assert sampler.should_sample_tail({}, d) is True

    def test_tail_based_with_violations_retained(self) -> None:
        sampler = TraceSampler(
            strategy=SamplingStrategy.TAIL_BASED, sample_rate=0.0
        )
        d = _make_decision(confidence=0.9, cost=0.001, constraints_violated=["r1"])
        assert sampler.should_sample_tail({}, d) is True

    def test_record_cost_accumulates(self) -> None:
        sampler = TraceSampler(strategy=SamplingStrategy.COST_AWARE)
        sampler.record_cost(1.0)
        sampler.record_cost(2.0)
        assert sampler.daily_cost_spent == pytest.approx(3.0)

    def test_reset_daily_budget(self) -> None:
        sampler = TraceSampler(strategy=SamplingStrategy.COST_AWARE)
        sampler.record_cost(5.0)
        sampler.reset_daily_budget()
        assert sampler.daily_cost_spent == 0.0

    def test_unknown_strategy_returns_true(self) -> None:
        sampler = TraceSampler(strategy=SamplingStrategy.ADAPTIVE)
        assert sampler.should_sample_head({}) is True


class TestImportanceScorer:
    def test_default_score(self) -> None:
        scorer = ImportanceScorer()
        assert scorer.score({}) == pytest.approx(0.5)

    def test_premium_user_adds_weight(self) -> None:
        scorer = ImportanceScorer()
        score = scorer.score({"user_tier": "premium"})
        assert score > 0.5

    def test_critical_flag_adds_weight(self) -> None:
        scorer = ImportanceScorer()
        score = scorer.score({"critical": True})
        assert score > 0.5

    def test_high_error_rate_adds_weight(self) -> None:
        scorer = ImportanceScorer()
        score = scorer.score({"error_rate": 0.5})
        assert score > 0.5

    def test_score_clamped_at_one(self) -> None:
        scorer = ImportanceScorer()
        score = scorer.score(
            {"user_tier": "premium", "critical": True, "error_rate": 0.9}
        )
        assert score == pytest.approx(1.0)


# ===========================================================================
# VersionTracker
# ===========================================================================


class TestVersionTracker:
    @pytest.fixture()
    def tracker(self) -> VersionTracker:
        return VersionTracker()

    def _snap(self, tracker: VersionTracker, model_version: str = "1.0") -> str:
        snap = tracker.capture_snapshot(
            model_name="claude-sonnet-4",
            model_version=model_version,
            prompt_template="You are a helpful assistant.",
            prompt_variables={"tone": "professional"},
            tools_available=["search", "calculator"],
            tool_versions={"search": "2.1", "calculator": "1.0"},
            system_config={"temperature": 0.7},
        )
        return str(snap.snapshot_id)

    def test_capture_snapshot_returns_snapshot(
        self, tracker: VersionTracker
    ) -> None:
        from agentability.models import VersionSnapshot

        snap = tracker.capture_snapshot(
            model_name="m",
            model_version="1",
            prompt_template="p",
            prompt_variables={},
            tools_available=[],
            tool_versions={},
            system_config={},
        )
        assert isinstance(snap, VersionSnapshot)

    def test_prompt_hash_generated(self, tracker: VersionTracker) -> None:
        snap = tracker.capture_snapshot(
            model_name="m", model_version="1",
            prompt_template="Hello!", prompt_variables={},
            tools_available=[], tool_versions={}, system_config={},
        )
        assert len(snap.prompt_hash) == 16

    def test_different_prompts_different_hashes(
        self, tracker: VersionTracker
    ) -> None:
        snap1 = tracker.capture_snapshot(
            model_name="m", model_version="1",
            prompt_template="Prompt A", prompt_variables={},
            tools_available=[], tool_versions={}, system_config={},
        )
        snap2 = tracker.capture_snapshot(
            model_name="m", model_version="1",
            prompt_template="Prompt B", prompt_variables={},
            tools_available=[], tool_versions={}, system_config={},
        )
        assert snap1.prompt_hash != snap2.prompt_hash

    def test_get_snapshot_found(self, tracker: VersionTracker) -> None:
        sid = self._snap(tracker)
        snap = tracker.get_snapshot(sid)
        assert snap is not None
        assert str(snap.snapshot_id) == sid

    def test_get_snapshot_not_found(self, tracker: VersionTracker) -> None:
        assert tracker.get_snapshot("nonexistent") is None

    def test_list_snapshots_order(self, tracker: VersionTracker) -> None:
        self._snap(tracker, "1.0")
        self._snap(tracker, "2.0")
        snaps = tracker.list_snapshots()
        assert len(snaps) == 2
        # newest first
        assert snaps[0].timestamp >= snaps[1].timestamp

    def test_compare_snapshots_model_version_change(
        self, tracker: VersionTracker
    ) -> None:
        id1 = self._snap(tracker, "1.0")
        id2 = self._snap(tracker, "2.0")
        diff = tracker.compare_snapshots(id1, id2)
        assert "model_version" in diff

    def test_compare_snapshots_no_diff(self, tracker: VersionTracker) -> None:
        id1 = self._snap(tracker, "1.0")
        id2 = self._snap(tracker, "1.0")
        diff = tracker.compare_snapshots(id1, id2)
        # Same version, same prompt — no differences
        assert "model_version" not in diff

    def test_compare_snapshots_missing_returns_error(
        self, tracker: VersionTracker
    ) -> None:
        id1 = self._snap(tracker)
        diff = tracker.compare_snapshots(id1, "ghost")
        assert "error" in diff

    def test_compare_tool_changes(self, tracker: VersionTracker) -> None:
        snap1 = tracker.capture_snapshot(
            model_name="m", model_version="1",
            prompt_template="p", prompt_variables={},
            tools_available=["search"], tool_versions={"search": "1.0"},
            system_config={},
        )
        snap2 = tracker.capture_snapshot(
            model_name="m", model_version="1",
            prompt_template="p", prompt_variables={},
            tools_available=["search", "calculator"],
            tool_versions={"search": "1.0", "calculator": "1.0"},
            system_config={},
        )
        diff = tracker.compare_snapshots(
            str(snap1.snapshot_id), str(snap2.snapshot_id)
        )
        assert "tools" in diff
        assert "calculator" in diff["tools"]["added"]

    def test_optional_fields(self, tracker: VersionTracker) -> None:
        snap = tracker.capture_snapshot(
            model_name="m", model_version="1",
            prompt_template="p", prompt_variables={},
            tools_available=[], tool_versions={}, system_config={},
            model_hash="abc123", dataset_version="v2",
        )
        assert snap.model_hash == "abc123"
        assert snap.dataset_version == "v2"


# ===========================================================================
# CostAnalyzer
# ===========================================================================


class TestCostAnalyzer:
    @pytest.fixture()
    def analyzer(self) -> CostAnalyzer:
        return CostAnalyzer()

    def test_record_returns_positive_cost(
        self, analyzer: CostAnalyzer
    ) -> None:
        cost = analyzer.record_llm_call("claude-sonnet-4", 1000, 500)
        assert cost > 0.0

    def test_zero_tokens_zero_cost(self, analyzer: CostAnalyzer) -> None:
        cost = analyzer.record_llm_call("claude-sonnet-4", 0, 0)
        assert cost == 0.0

    def test_unknown_model_uses_default_pricing(
        self, analyzer: CostAnalyzer
    ) -> None:
        cost = analyzer.record_llm_call("mystery-model-99", 1_000_000, 0)
        assert cost == pytest.approx(1.0)  # default input price = $1/M

    def test_get_total_cost_empty(self, analyzer: CostAnalyzer) -> None:
        assert analyzer.get_total_cost() == 0.0

    def test_get_total_cost_with_data(self, analyzer: CostAnalyzer) -> None:
        c1 = analyzer.record_llm_call("claude-sonnet-4", 1000, 500)
        c2 = analyzer.record_llm_call("gpt-4", 500, 200)
        assert analyzer.get_total_cost() == pytest.approx(c1 + c2)

    def test_get_cost_by_model(self, analyzer: CostAnalyzer) -> None:
        analyzer.record_llm_call("claude-sonnet-4", 1000, 500)
        analyzer.record_llm_call("gpt-4", 500, 200)
        by_model = analyzer.get_cost_by_model()
        assert "claude-sonnet-4" in by_model
        assert "gpt-4" in by_model

    def test_get_total_cost_time_window(self, analyzer: CostAnalyzer) -> None:
        # Record a call with an old timestamp
        old_ts = datetime.now() - timedelta(hours=48)
        analyzer.record_llm_call("gpt-4", 1000, 500, timestamp=old_ts)
        # Window of 24h should exclude it
        assert analyzer.get_total_cost(time_window_hours=24) == 0.0

    def test_suggest_optimizations_empty(
        self, analyzer: CostAnalyzer
    ) -> None:
        suggestions = analyzer.suggest_optimizations()
        assert suggestions == []

    def test_suggest_gpt4_downgrade(self, analyzer: CostAnalyzer) -> None:
        # Simulate >$10 of gpt-4 spend in last 24h
        for _ in range(3):
            analyzer.record_llm_call("gpt-4", 100_000, 50_000)
        suggestions = analyzer.suggest_optimizations()
        types = [s.optimization_type for s in suggestions]
        assert "model_downgrade" in types

    def test_suggest_claude_opus_downgrade(self, analyzer: CostAnalyzer) -> None:
        for _ in range(3):
            analyzer.record_llm_call("claude-opus-4", 100_000, 20_000)
        suggestions = analyzer.suggest_optimizations()
        assert any("claude-sonnet-4" in s.description for s in suggestions)

    def test_pricing_for_all_known_models(
        self, analyzer: CostAnalyzer
    ) -> None:
        for model in ["gpt-4-turbo", "gpt-3.5-turbo", "claude-haiku-4", "gemini-pro"]:
            cost = analyzer.record_llm_call(model, 1000, 500)
            assert cost >= 0.0


# ===========================================================================
# LineageTracer
# ===========================================================================


class TestLineageTracer:
    @pytest.fixture()
    def tracer(self) -> LineageTracer:
        return LineageTracer()

    def test_record_lineage_returns_object(
        self, tracer: LineageTracer
    ) -> None:
        from agentability.analyzers.lineage_tracer import InformationLineage

        lineage = tracer.record_lineage(
            source="api_a",
            destination="decision_1",
            path=["api_a", "transform", "decision_1"],
        )
        assert isinstance(lineage, InformationLineage)

    def test_lineage_stored(self, tracer: LineageTracer) -> None:
        tracer.record_lineage("src", "dst", ["src", "dst"])
        assert len(tracer.lineages) == 1

    def test_trace_back_finds_lineage(self, tracer: LineageTracer) -> None:
        tracer.record_lineage("src_a", "dst_1", ["src_a", "dst_1"])
        tracer.record_lineage("src_b", "dst_2", ["src_b", "dst_2"])
        result = tracer.trace_back("dst_1")
        assert len(result) == 1
        assert result[0].source == "src_a"

    def test_trace_forward_finds_lineage(self, tracer: LineageTracer) -> None:
        tracer.record_lineage("origin", "dest_x", ["origin", "dest_x"])
        tracer.record_lineage("other", "dest_y", ["other", "dest_y"])
        result = tracer.trace_forward("origin")
        assert len(result) == 1

    def test_get_all_sources_for(self, tracer: LineageTracer) -> None:
        tracer.record_lineage("src_1", "shared_dst", ["src_1", "shared_dst"])
        tracer.record_lineage("src_2", "shared_dst", ["src_2", "shared_dst"])
        sources = tracer.get_all_sources_for("shared_dst")
        assert set(sources) == {"src_1", "src_2"}

    def test_transformations_stored(self, tracer: LineageTracer) -> None:
        lineage = tracer.record_lineage(
            "src", "dst", ["src", "mid", "dst"],
            transformations=["normalize", "encode"],
        )
        assert lineage.transformations == ["normalize", "encode"]

    def test_empty_trace_back(self, tracer: LineageTracer) -> None:
        assert tracer.trace_back("nonexistent") == []

    def test_empty_trace_forward(self, tracer: LineageTracer) -> None:
        assert tracer.trace_forward("ghost") == []

    def test_graph_built_from_path(self, tracer: LineageTracer) -> None:
        tracer.record_lineage("a", "c", ["a", "b", "c"])
        # Graph should have a->b and b->c edges
        assert "b" in tracer._graph.get("a", set())
        assert "c" in tracer._graph.get("b", set())


# ===========================================================================
# ProvenanceAnalyzer
# ===========================================================================


class TestProvenanceAnalyzer:
    @pytest.fixture()
    def analyzer(self) -> ProvenanceAnalyzer:
        return ProvenanceAnalyzer()

    def test_create_provenance_returns_object(
        self, analyzer: ProvenanceAnalyzer
    ) -> None:
        from agentability.analyzers.provenance import DecisionProvenance

        prov = analyzer.create_provenance("d1", "agent_a", {"result": "deny"}, 0.42)
        assert isinstance(prov, DecisionProvenance)

    def test_get_provenance_found(self, analyzer: ProvenanceAnalyzer) -> None:
        analyzer.create_provenance("d1", "agent_a", "deny", 0.6)
        assert analyzer.get_provenance("d1") is not None

    def test_get_provenance_not_found(
        self, analyzer: ProvenanceAnalyzer
    ) -> None:
        assert analyzer.get_provenance("ghost") is None

    def test_add_record_stored(self, analyzer: ProvenanceAnalyzer) -> None:
        analyzer.create_provenance("d1", "a", "deny", 0.5)
        record = analyzer.add_record(
            "d1", "input_data", "income_api", {"income": 75000}, 0.8
        )
        assert record is not None
        prov = analyzer.get_provenance("d1")
        assert prov is not None
        assert len(prov.records) == 1

    def test_add_record_missing_decision_returns_none(
        self, analyzer: ProvenanceAnalyzer
    ) -> None:
        result = analyzer.add_record("ghost", "input_data", "src", {}, 0.5)
        assert result is None

    def test_explain_decision_not_found(
        self, analyzer: ProvenanceAnalyzer
    ) -> None:
        result = analyzer.explain_decision("ghost")
        assert "error" in result

    def test_explain_decision_with_records(
        self, analyzer: ProvenanceAnalyzer
    ) -> None:
        analyzer.create_provenance("d1", "a", "approve", 0.85)
        analyzer.add_record("d1", "input_data", "api", {"x": 1}, 0.9, impact=0.8)
        result = analyzer.explain_decision("d1")
        assert "summary" in result
        assert "timeline" in result

    def test_explain_decision_high_confidence_summary(
        self, analyzer: ProvenanceAnalyzer
    ) -> None:
        analyzer.create_provenance("d1", "a", "approve", 0.92)
        result = analyzer.explain_decision("d1")
        assert "High confidence" in result["summary"]

    def test_find_confidence_bottleneck_high_confidence(
        self, analyzer: ProvenanceAnalyzer
    ) -> None:
        analyzer.create_provenance("d1", "a", "approve", 0.95)
        assert analyzer.find_confidence_bottleneck("d1") is None

    def test_find_confidence_bottleneck_low_confidence(
        self, analyzer: ProvenanceAnalyzer
    ) -> None:
        analyzer.create_provenance("d1", "a", "deny", 0.35)
        analyzer.add_record(
            "d1", "input_data", "bad_api", {"data": "stale"},
            confidence=0.3, impact=0.9
        )
        bottleneck = analyzer.find_confidence_bottleneck("d1")
        assert bottleneck is not None
        assert bottleneck["source"] == "bad_api"

    def test_trace_information_lineage(
        self, analyzer: ProvenanceAnalyzer
    ) -> None:
        analyzer.create_provenance("d1", "a", "deny", 0.5)
        analyzer.add_record(
            "d1", "input_data", "income_api",
            {"income": 75000, "age": 35}, 0.8
        )
        flow = analyzer.trace_information_lineage("d1", "income")
        assert len(flow) >= 1

    def test_trace_information_flow_alias(
        self, analyzer: ProvenanceAnalyzer
    ) -> None:
        analyzer.create_provenance("d1", "a", "deny", 0.5)
        analyzer.add_record("d1", "input_data", "src", "some income data", 0.7)
        flow1 = analyzer.trace_information_flow("d1", "income")
        flow2 = analyzer.trace_information_lineage("d1", "income")
        assert flow1 == flow2

    def test_compare_decisions(self, analyzer: ProvenanceAnalyzer) -> None:
        analyzer.create_provenance("d1", "a", "approve", 0.9)
        analyzer.create_provenance("d2", "a", "deny", 0.4)
        analyzer.add_record("d1", "input_data", "src_a", {}, 0.9)
        analyzer.add_record("d2", "reasoning_step", "src_b", {}, 0.5)
        diff = analyzer.compare_decisions("d1", "d2")
        assert "differences" in diff
        assert diff["differences"]["confidence_delta"] == pytest.approx(0.4 - 0.9)

    def test_compare_decisions_missing(
        self, analyzer: ProvenanceAnalyzer
    ) -> None:
        result = analyzer.compare_decisions("ghost1", "ghost2")
        assert "error" in result

    def test_get_dependency_chain(self, analyzer: ProvenanceAnalyzer) -> None:
        analyzer.create_provenance("d1", "a", "ok", 0.8)
        dep_id = str(uuid4())
        analyzer.add_record(
            "d1", "dependency", "upstream",
            {"decision_id": dep_id}, 0.9
        )
        chain = analyzer.get_dependency_chain("d1")
        assert dep_id in chain

    def test_get_dependency_chain_string_content(
        self, analyzer: ProvenanceAnalyzer
    ) -> None:
        analyzer.create_provenance("d1", "a", "ok", 0.8)
        analyzer.add_record("d1", "dependency", "upstream", "decision_xyz", 0.9)
        chain = analyzer.get_dependency_chain("d1")
        assert "decision_xyz" in chain

    def test_provenances_property(self, analyzer: ProvenanceAnalyzer) -> None:
        analyzer.create_provenance("d1", "a", "ok", 0.8)
        assert "d1" in analyzer.provenances

"""Tests for core Pydantic data models.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from uuid import UUID

import pytest
from pydantic import ValidationError

from agentability.models import (
    AgentConflict,
    CapabilityDimension,
    CapabilityScore,
    CausalRelationship,
    ConflictType,
    Decision,
    DecisionType,
    LLMMetrics,
    MemoryMetrics,
    MemoryOperation,
    MemoryType,
    PolicyViolation,
    VersionSnapshot,
    ViolationSeverity,
)


class TestDecision:
    def test_default_factory_generates_uuid(self) -> None:
        d = Decision(agent_id="a", decision_type=DecisionType.CLASSIFICATION)
        assert isinstance(d.decision_id, UUID)

    def test_two_decisions_have_different_ids(self) -> None:
        d1 = Decision(agent_id="a", decision_type=DecisionType.CLASSIFICATION)
        d2 = Decision(agent_id="a", decision_type=DecisionType.CLASSIFICATION)
        assert d1.decision_id != d2.decision_id

    def test_confidence_too_high_raises(self) -> None:
        with pytest.raises(ValidationError):
            Decision(
                agent_id="a",
                decision_type=DecisionType.CLASSIFICATION,
                confidence=1.5,
            )

    def test_confidence_too_low_raises(self) -> None:
        with pytest.raises(ValidationError):
            Decision(
                agent_id="a",
                decision_type=DecisionType.CLASSIFICATION,
                confidence=-0.1,
            )

    def test_confidence_boundary_values_accepted(self) -> None:
        d0 = Decision(
            agent_id="a",
            decision_type=DecisionType.CLASSIFICATION,
            confidence=0.0,
        )
        d1 = Decision(
            agent_id="a",
            decision_type=DecisionType.CLASSIFICATION,
            confidence=1.0,
        )
        assert d0.confidence == 0.0
        assert d1.confidence == 1.0

    def test_missing_agent_id_raises(self) -> None:
        with pytest.raises(ValidationError):
            Decision(decision_type=DecisionType.CLASSIFICATION)  # type: ignore[call-arg]

    def test_default_list_fields_are_empty(self) -> None:
        d = Decision(agent_id="a", decision_type=DecisionType.GENERATION)
        assert d.reasoning == []
        assert d.uncertainties == []
        assert d.assumptions == []
        assert d.tags == []
        assert d.data_sources == []

    def test_all_decision_types_valid(self) -> None:
        for dt in DecisionType:
            d = Decision(agent_id="a", decision_type=dt)
            assert d.decision_type == dt

    def test_json_round_trip(self) -> None:
        d = Decision(
            agent_id="agent_x",
            decision_type=DecisionType.CLASSIFICATION,
            confidence=0.88,
            reasoning=["step 1", "step 2"],
        )
        d2 = Decision.model_validate_json(d.model_dump_json())
        assert d2.decision_id == d.decision_id
        assert d2.confidence == d.confidence
        assert d2.reasoning == d.reasoning


class TestMemoryMetrics:
    def test_vector_metrics_accepted(self) -> None:
        m = MemoryMetrics(
            agent_id="rag",
            memory_type=MemoryType.VECTOR,
            operation=MemoryOperation.RETRIEVE,
            latency_ms=42.5,
            items_processed=10,
            avg_similarity=0.81,
            retrieval_precision=0.85,
            top_k=10,
        )
        assert m.avg_similarity == pytest.approx(0.81)

    def test_similarity_out_of_range_raises(self) -> None:
        with pytest.raises(ValidationError):
            MemoryMetrics(
                agent_id="a",
                memory_type=MemoryType.VECTOR,
                operation=MemoryOperation.RETRIEVE,
                latency_ms=10.0,
                items_processed=5,
                avg_similarity=1.5,
            )

    def test_items_processed_negative_raises(self) -> None:
        with pytest.raises(ValidationError):
            MemoryMetrics(
                agent_id="a",
                memory_type=MemoryType.VECTOR,
                operation=MemoryOperation.RETRIEVE,
                latency_ms=10.0,
                items_processed=-1,
            )

    def test_episodic_fields_stored(self) -> None:
        m = MemoryMetrics(
            agent_id="chat",
            memory_type=MemoryType.EPISODIC,
            operation=MemoryOperation.RETRIEVE,
            latency_ms=12.0,
            items_processed=5,
            temporal_coherence=0.93,
            context_tokens_used=1840,
            context_tokens_limit=8192,
        )
        assert m.temporal_coherence == pytest.approx(0.93)


class TestLLMMetrics:
    def test_total_tokens_stored(self) -> None:
        m = LLMMetrics(
            agent_id="a",
            provider="anthropic",
            model="claude-sonnet-4",
            prompt_tokens=500,
            completion_tokens=200,
            total_tokens=700,
            latency_ms=900.0,
            cost_usd=0.005,
        )
        assert m.total_tokens == 700

    def test_negative_prompt_tokens_raises(self) -> None:
        with pytest.raises(ValidationError):
            LLMMetrics(
                agent_id="a",
                provider="openai",
                model="gpt-4",
                prompt_tokens=-1,
                completion_tokens=100,
                total_tokens=99,
                latency_ms=500.0,
                cost_usd=0.01,
            )

    def test_negative_cost_raises(self) -> None:
        with pytest.raises(ValidationError):
            LLMMetrics(
                agent_id="a",
                provider="openai",
                model="gpt-4",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                latency_ms=300.0,
                cost_usd=-0.01,
            )


class TestAgentConflict:
    def test_one_agent_raises(self) -> None:
        with pytest.raises(ValidationError):
            AgentConflict(
                session_id="s1",
                conflict_type=ConflictType.GOAL_CONFLICT,
                involved_agents=["only_one"],
                agent_positions={"only_one": {}},
                severity=0.5,
            )

    def test_two_agents_accepted(self) -> None:
        c = AgentConflict(
            session_id="s1",
            conflict_type=ConflictType.GOAL_CONFLICT,
            involved_agents=["a", "b"],
            agent_positions={"a": {"d": "approve"}, "b": {"d": "deny"}},
            severity=0.7,
        )
        assert len(c.involved_agents) == 2

    def test_severity_too_high_raises(self) -> None:
        with pytest.raises(ValidationError):
            AgentConflict(
                session_id="s",
                conflict_type=ConflictType.BELIEF_CONFLICT,
                involved_agents=["a", "b"],
                agent_positions={"a": {}, "b": {}},
                severity=1.5,
            )

    def test_all_conflict_types_valid(self) -> None:
        for ct in ConflictType:
            c = AgentConflict(
                session_id="s",
                conflict_type=ct,
                involved_agents=["a", "b"],
                agent_positions={"a": {}, "b": {}},
                severity=0.5,
            )
            assert c.conflict_type == ct


class TestCapabilityScore:
    def test_score_above_100_raises(self) -> None:
        with pytest.raises(ValidationError):
            CapabilityScore(
                dimension=CapabilityDimension.REASONING,
                score=101.0,
                confidence=0.8,
                evidence_count=50,
            )

    def test_valid_score(self) -> None:
        cs = CapabilityScore(
            dimension=CapabilityDimension.MEMORY,
            score=75.0,
            confidence=0.9,
            evidence_count=100,
        )
        assert cs.score == pytest.approx(75.0)


class TestPolicyViolation:
    def test_all_severity_levels(self) -> None:
        for sev in ViolationSeverity:
            v = PolicyViolation(
                rule_id="r",
                rule_description="Test",
                severity=sev,
                agent_id="a",
            )
            assert v.severity == sev

    def test_violation_details_defaults_empty(self) -> None:
        v = PolicyViolation(
            rule_id="pii",
            rule_description="No PII",
            severity=ViolationSeverity.CRITICAL,
            agent_id="a",
        )
        assert v.violation_details == {}


class TestVersionSnapshot:
    def test_created_with_required_fields(self) -> None:
        s = VersionSnapshot(
            model_name="claude-sonnet-4",
            model_version="20260101",
            prompt_template="You are helpful.",
            prompt_hash="abcdef01",
        )
        assert s.model_name == "claude-sonnet-4"
        assert isinstance(s.snapshot_id, UUID)

    def test_tools_default_empty(self) -> None:
        s = VersionSnapshot(
            model_name="m",
            model_version="1",
            prompt_template="p",
            prompt_hash="h",
        )
        assert s.tools_available == []


class TestCausalRelationship:
    def test_strength_too_high_raises(self) -> None:
        with pytest.raises(ValidationError):
            CausalRelationship(
                source_decision_id=UUID(int=1),
                target_decision_id=UUID(int=2),
                relationship_type="causes",
                strength=1.5,
                time_delta_ms=100.0,
                confidence=0.9,
            )

    def test_valid_relationship(self) -> None:
        r = CausalRelationship(
            source_decision_id=UUID(int=1),
            target_decision_id=UUID(int=2),
            relationship_type="causes",
            strength=0.8,
            time_delta_ms=250.0,
            confidence=0.95,
        )
        assert r.strength == pytest.approx(0.8)

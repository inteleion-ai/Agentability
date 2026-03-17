"""Capability scoring system.

Measures agent capabilities across eight dimensions and produces a
composite AgentabilityScore (0–100).

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import math

from agentability.models import (
    CapabilityDimension,
    CapabilityScore,
    Decision,
    MemoryMetrics,
    PolicyViolation,
)


class AgentabilityScorer:
    """Compute capability scores across all eight dimensions."""

    def __init__(self) -> None:
        self.dimension_weights: dict[CapabilityDimension, float] = {
            CapabilityDimension.REASONING: 0.20,
            CapabilityDimension.MEMORY: 0.15,
            CapabilityDimension.TOOL_USE: 0.15,
            CapabilityDimension.AUTONOMY: 0.15,
            CapabilityDimension.ROBUSTNESS: 0.10,
            CapabilityDimension.SAFETY: 0.10,
            CapabilityDimension.EFFICIENCY: 0.10,
            CapabilityDimension.COLLABORATION: 0.05,
        }

    def score_reasoning(self, decisions: list[Decision]) -> CapabilityScore:
        """Score the Reasoning dimension (confidence, depth, uncertainty)."""
        if not decisions:
            return CapabilityScore(
                dimension=CapabilityDimension.REASONING,
                score=0.0,
                confidence=0.0,
                evidence_count=0,
            )

        conf_scores = [d.confidence for d in decisions if d.confidence is not None]
        avg_confidence = sum(conf_scores) / len(conf_scores) if conf_scores else 0.5
        avg_steps = sum(len(d.reasoning) for d in decisions) / len(decisions)
        depth_score = min(avg_steps / 5.0, 1.0)
        uncertainty_score = sum(1 for d in decisions if d.uncertainties) / len(decisions)

        raw = 0.30 * avg_confidence + 0.30 * depth_score + 0.40 * uncertainty_score
        return CapabilityScore(
            dimension=CapabilityDimension.REASONING,
            score=min(raw * 100, 100.0),
            confidence=self._confidence(len(decisions)),
            evidence_count=len(decisions),
        )

    def score_memory(self, memory_ops: list[MemoryMetrics]) -> CapabilityScore:
        """Score the Memory dimension (precision, latency)."""
        if not memory_ops:
            return CapabilityScore(
                dimension=CapabilityDimension.MEMORY,
                score=0.0,
                confidence=0.0,
                evidence_count=0,
            )

        precisions = [
            op.retrieval_precision
            for op in memory_ops
            if op.retrieval_precision is not None
        ]
        avg_precision = sum(precisions) / len(precisions) if precisions else 0.7
        avg_latency = sum(op.latency_ms for op in memory_ops) / len(memory_ops)
        latency_score = max(0.0, 1.0 - avg_latency / 1000.0)

        raw = 0.60 * avg_precision + 0.40 * latency_score
        return CapabilityScore(
            dimension=CapabilityDimension.MEMORY,
            score=min(raw * 100, 100.0),
            confidence=self._confidence(len(memory_ops)),
            evidence_count=len(memory_ops),
        )

    def score_safety(
        self,
        decisions: list[Decision],
        policy_violations: list[PolicyViolation],
    ) -> CapabilityScore:
        """Score the Safety dimension (compliance rate, critical violations)."""
        if not decisions:
            return CapabilityScore(
                dimension=CapabilityDimension.SAFETY,
                score=100.0,
                confidence=0.0,
                evidence_count=0,
            )

        violations_count = sum(1 for d in decisions if d.constraints_violated)
        compliance_rate = 1.0 - violations_count / len(decisions)
        critical = sum(
            1 for v in policy_violations if v.severity.value == "critical"
        )
        penalty = min(critical * 0.2, 0.5)
        raw = max(0.0, compliance_rate - penalty)

        return CapabilityScore(
            dimension=CapabilityDimension.SAFETY,
            score=min(raw * 100, 100.0),
            confidence=self._confidence(len(decisions)),
            evidence_count=len(decisions),
        )

    def score_efficiency(self, decisions: list[Decision]) -> CapabilityScore:
        """Score the Efficiency dimension (cost, latency)."""
        if not decisions:
            return CapabilityScore(
                dimension=CapabilityDimension.EFFICIENCY,
                score=0.0,
                confidence=0.0,
                evidence_count=0,
            )

        costs = [d.total_cost_usd for d in decisions if d.total_cost_usd > 0]
        avg_cost = sum(costs) / len(costs) if costs else 0.01
        cost_score = max(0.0, 1.0 - avg_cost / 0.10)

        latencies = [d.latency_ms for d in decisions if d.latency_ms is not None]
        avg_latency = sum(latencies) / len(latencies) if latencies else 1000.0
        latency_score = max(0.0, 1.0 - avg_latency / 5000.0)

        raw = 0.50 * cost_score + 0.50 * latency_score
        return CapabilityScore(
            dimension=CapabilityDimension.EFFICIENCY,
            score=min(raw * 100, 100.0),
            confidence=self._confidence(len(decisions)),
            evidence_count=len(decisions),
        )

    def compute_composite_score(
        self,
        dimension_scores: dict[CapabilityDimension, CapabilityScore],
    ) -> float:
        """Return weighted composite AgentabilityScore in [0, 100]."""
        total_score = 0.0
        total_weight = 0.0
        for dim, weight in self.dimension_weights.items():
            if dim in dimension_scores:
                obj = dimension_scores[dim]
                w = weight * obj.confidence
                total_score += obj.score * w
                total_weight += w
        return 0.0 if total_weight == 0.0 else total_score / total_weight

    @staticmethod
    def _confidence(evidence_count: int) -> float:
        if evidence_count == 0:
            return 0.0
        return min(1.0, math.log1p(evidence_count) / math.log1p(100))

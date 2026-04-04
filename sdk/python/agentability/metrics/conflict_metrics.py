"""Multi-agent conflict tracking and game-theoretic analysis.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ConflictType(Enum):
    DECISION_DISAGREEMENT = "decision_disagreement"
    RESOURCE_CONTENTION = "resource_contention"
    PRIORITY_CONFLICT = "priority_conflict"
    CONSTRAINT_VIOLATION = "constraint_violation"
    TEMPORAL_CONFLICT = "temporal_conflict"
    DATA_INCONSISTENCY = "data_inconsistency"


class ResolutionStrategy(Enum):
    VOTING = "voting"
    HIERARCHY = "hierarchy"
    CONSENSUS = "consensus"
    ARBITRATION = "arbitration"
    FIRST_COME = "first_come"
    CONFIDENCE_BASED = "confidence_based"


@dataclass
class AgentPosition:
    """An agent's stated position in a conflict."""

    agent_id: str
    position: Any
    confidence: float
    reasoning: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    priority: int = 0


@dataclass
class ConflictMetric:
    """Metrics for a single conflict event."""

    conflict_id: str
    conflict_type: ConflictType
    timestamp: datetime
    agents_involved: set[str]
    agent_positions: list[AgentPosition]
    resolution_strategy: ResolutionStrategy | None = None
    resolution_time_ms: float | None = None
    consensus_reached: bool = False
    final_decision: Any = None
    conflict_severity: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)


class ConflictMetricsCollector:
    """Collect and analyse multi-agent conflict metrics."""

    def __init__(self) -> None:
        self.conflicts: list[ConflictMetric] = []
        self._agent_conflict_matrix: dict[tuple[str, str], int] = defaultdict(int)
        self._resolution_success: dict[ResolutionStrategy, list[bool]] = defaultdict(
            list
        )

    def record_conflict(
        self,
        conflict_type: str,
        agents: list[str],
        positions: list[AgentPosition],
        conflict_id: str | None = None,
    ) -> str:
        """Record a conflict and return its ID."""
        if conflict_id is None:
            conflict_id = (
                f"conflict_{len(self.conflicts)}_{int(datetime.now().timestamp())}"
            )

        metric = ConflictMetric(
            conflict_id=conflict_id,
            conflict_type=ConflictType(conflict_type),
            timestamp=datetime.now(),
            agents_involved=set(agents),
            agent_positions=positions,
            conflict_severity=self._calculate_severity(positions),
        )
        self.conflicts.append(metric)

        for i, agent_a in enumerate(agents):
            for agent_b in agents[i + 1 :]:
                pair: tuple[str, str] = (min(agent_a, agent_b), max(agent_a, agent_b))
                self._agent_conflict_matrix[pair] += 1

        return conflict_id

    def resolve_conflict(
        self,
        conflict_id: str,
        strategy: str,
        final_decision: Any,
        resolution_time_ms: float,
        consensus_reached: bool = False,
    ) -> None:
        """Record how a conflict was resolved."""
        strat = ResolutionStrategy(strategy)
        for conflict in self.conflicts:
            if conflict.conflict_id == conflict_id:
                conflict.resolution_strategy = strat
                conflict.final_decision = final_decision
                conflict.resolution_time_ms = resolution_time_ms
                conflict.consensus_reached = consensus_reached
                self._resolution_success[strat].append(consensus_reached)
                break

    def get_conflict_rate(
        self,
        agent_id: str | None = None,
        time_window_hours: int | None = None,
    ) -> float:
        """Return conflicts per hour."""
        conflicts = self._filter_conflicts(agent_id, time_window_hours)
        if not conflicts:
            return 0.0
        if time_window_hours:
            return len(conflicts) / time_window_hours
        if len(conflicts) < 2:
            return 0.0
        span_hours = (
            conflicts[-1].timestamp - conflicts[0].timestamp
        ).total_seconds() / 3600
        return len(conflicts) / max(span_hours, 1.0)

    def get_agent_conflict_matrix(self) -> dict[tuple[str, str], int]:
        return dict(self._agent_conflict_matrix)

    def get_most_conflicting_pairs(
        self, top_n: int = 5
    ) -> list[tuple[tuple[str, str], int]]:
        return sorted(
            self._agent_conflict_matrix.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:top_n]

    def get_resolution_effectiveness(
        self, strategy: str | None = None
    ) -> dict[str, Any]:
        strats = (
            [ResolutionStrategy(strategy)] if strategy else list(ResolutionStrategy)
        )
        results: dict[str, Any] = {}
        for strat in strats:
            successes = self._resolution_success.get(strat, [])
            results[strat.value] = {
                "total_uses": len(successes),
                "consensus_rate": (
                    sum(successes) / len(successes) if successes else 0.0
                ),
                "avg_resolution_time_ms": self._get_avg_resolution_time(strat),
            }
        return results

    def get_conflict_by_type(
        self, time_window_hours: int | None = None
    ) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for conflict in self._filter_conflicts(None, time_window_hours):
            counts[conflict.conflict_type.value] += 1
        return dict(counts)

    def get_avg_severity(
        self,
        agent_id: str | None = None,
        conflict_type: str | None = None,
        time_window_hours: int | None = None,
    ) -> float:
        conflicts = self._filter_conflicts(agent_id, time_window_hours)
        if conflict_type:
            ct = ConflictType(conflict_type)
            conflicts = [c for c in conflicts if c.conflict_type == ct]
        if not conflicts:
            return 0.0
        return statistics.mean(c.conflict_severity for c in conflicts)

    def analyze_agent_behavior(
        self,
        agent_id: str,
        time_window_hours: int | None = None,
    ) -> dict[str, Any]:
        conflicts = self._filter_conflicts(agent_id, time_window_hours)
        if not conflicts:
            return {
                "total_conflicts": 0,
                "conflict_rate": 0.0,
                "avg_severity": 0.0,
                "most_common_conflict_type": None,
                "most_conflicting_agents": [],
            }

        type_counts: dict[str, int] = defaultdict(int)
        for c in conflicts:
            type_counts[c.conflict_type.value] += 1

        most_common_type: str | None = (
            max(type_counts, key=lambda k: type_counts[k]) if type_counts else None
        )

        partner_counts: dict[str, int] = defaultdict(int)
        for c in conflicts:
            for other in c.agents_involved:
                if other != agent_id:
                    partner_counts[other] += 1

        return {
            "total_conflicts": len(conflicts),
            "conflict_rate": self.get_conflict_rate(agent_id, time_window_hours),
            "avg_severity": statistics.mean(c.conflict_severity for c in conflicts),
            "most_common_conflict_type": most_common_type,
            "most_conflicting_agents": sorted(
                partner_counts.items(), key=lambda x: x[1], reverse=True
            )[:3],
            "conflict_types_distribution": dict(type_counts),
        }

    def get_game_theoretic_analysis(self, conflict_id: str) -> dict[str, Any]:
        conflict: ConflictMetric | None = next(
            (c for c in self.conflicts if c.conflict_id == conflict_id), None
        )
        if conflict is None:
            return {}

        positions = conflict.agent_positions
        dominant: str | None = None
        if positions:
            top = max(positions, key=lambda p: p.confidence)
            if top.confidence > 0.8:
                dominant = top.agent_id

        diversity = 0.0
        if len(positions) > 1:
            confs = [p.confidence for p in positions]
            diversity = statistics.stdev(confs) if len(confs) > 1 else 0.0

        pareto: list[dict[str, Any]] = [
            {
                "agent": pa.agent_id,
                "could_defer_to": pb.agent_id,
                "potential_gain": pb.confidence - pa.confidence,
            }
            for i, pa in enumerate(positions)
            for pb in positions[i + 1 :]
            if pa.confidence < 0.5 and pb.confidence > 0.7
        ]

        return {
            "agents_count": len(positions),
            "dominant_strategy_agent": dominant,
            "position_diversity": diversity,
            "consensus_likelihood": 1.0 - diversity,
            "pareto_improvements_possible": len(pareto),
            "pareto_improvements": pareto,
            "is_zero_sum": conflict.conflict_type is ConflictType.RESOURCE_CONTENTION,
            "recommended_resolution": self._recommend_resolution(conflict),
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _calculate_severity(self, positions: list[AgentPosition]) -> float:
        if len(positions) < 2:
            return 0.0
        return min(1.0, statistics.mean(p.confidence for p in positions))

    def _get_avg_resolution_time(self, strategy: ResolutionStrategy) -> float:
        times = [
            c.resolution_time_ms
            for c in self.conflicts
            if c.resolution_strategy is strategy
            and c.resolution_time_ms is not None
        ]
        return statistics.mean(times) if times else 0.0

    def _recommend_resolution(self, conflict: ConflictMetric) -> str:
        if conflict.conflict_type is ConflictType.RESOURCE_CONTENTION:
            return "hierarchy"
        positions = conflict.agent_positions
        if not positions:
            return "arbitration"
        if max(p.confidence for p in positions) > 0.9:
            return "confidence_based"
        total_priority = sum(p.priority for p in positions)
        avg_priority = total_priority / len(positions) if positions else 0.0
        if max(p.priority for p in positions) > avg_priority * 1.5:
            return "hierarchy"
        return "voting"

    def _filter_conflicts(
        self,
        agent_id: str | None,
        time_window_hours: int | None,
    ) -> list[ConflictMetric]:
        result = self.conflicts
        if agent_id:
            result = [c for c in result if agent_id in c.agents_involved]
        if time_window_hours:
            cutoff = datetime.now().timestamp() - time_window_hours * 3600
            result = [c for c in result if c.timestamp.timestamp() > cutoff]
        return result

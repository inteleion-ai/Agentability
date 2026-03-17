"""Multi-agent conflict analyser.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


class ConflictResolutionMethod(Enum):
    PRIORITY_HIERARCHY = "priority_hierarchy"
    CONSENSUS = "consensus"
    HUMAN_ESCALATION = "human_escalation"
    CONFIDENCE_BASED = "confidence_based"
    CUSTOM_LOGIC = "custom_logic"


@dataclass
class AgentConflict:
    """Record of a conflict between agents."""

    conflict_id: str
    timestamp: datetime
    agents: list[str]
    outputs: dict[str, Any]
    confidences: dict[str, float]
    resolution_method: ConflictResolutionMethod
    winning_agent: str
    final_decision: Any
    context: dict[str, Any] = field(default_factory=dict)


class ConflictAnalyzer:
    """Analyse conflicts in multi-agent systems.

    Example:
        >>> analyzer = ConflictAnalyzer()
        >>> analyzer.record_conflict(
        ...     agents=["risk", "sales"],
        ...     outputs={"risk": "deny", "sales": "approve"},
        ...     confidences={"risk": 0.85, "sales": 0.90},
        ...     resolution_method="priority_hierarchy",
        ...     winning_agent="risk",
        ...     final_decision="deny",
        ... )
        >>> patterns = analyzer.get_conflict_patterns(days=30)
    """

    def __init__(self) -> None:
        self.conflicts: list[AgentConflict] = []

    def record_conflict(
        self,
        agents: list[str],
        outputs: dict[str, Any],
        confidences: dict[str, float],
        resolution_method: str,
        winning_agent: str,
        final_decision: Any,
        context: dict[str, Any] | None = None,
    ) -> AgentConflict:
        """Record a conflict and return the created record."""
        conflict = AgentConflict(
            conflict_id=(
                f"conflict_{len(self.conflicts)}_{datetime.now().isoformat()}"
            ),
            timestamp=datetime.now(),
            agents=agents,
            outputs=outputs,
            confidences=confidences,
            resolution_method=ConflictResolutionMethod(resolution_method),
            winning_agent=winning_agent,
            final_decision=final_decision,
            context=context or {},
        )
        self.conflicts.append(conflict)
        return conflict

    def get_conflict_patterns(self, days: int = 30) -> dict[str, Any]:
        """Analyse conflict patterns over the last *days* days."""
        cutoff = datetime.now() - timedelta(days=days)
        recent = [c for c in self.conflicts if c.timestamp >= cutoff]

        if not recent:
            return {"total_conflicts": 0}

        pair_counts: Counter[tuple[str, str]] = Counter()
        win_counts: Counter[str] = Counter()
        resolution_counts: Counter[str] = Counter()

        for conflict in recent:
            if len(conflict.agents) == 2:
                pair: tuple[str, str] = (
                    min(conflict.agents),
                    max(conflict.agents),
                )
                pair_counts[pair] += 1
            win_counts[conflict.winning_agent] += 1
            resolution_counts[conflict.resolution_method.value] += 1

        most_common_pairs: list[dict[str, Any]] = []
        for pair, count in pair_counts.most_common(10):
            pair_conflicts = [c for c in recent if set(c.agents) == set(pair)]
            a1_wins = sum(1 for c in pair_conflicts if c.winning_agent == pair[0])
            a2_wins = sum(1 for c in pair_conflicts if c.winning_agent == pair[1])
            most_common_pairs.append(
                {
                    "agents": list(pair),
                    "count": count,
                    "agent_wins": {pair[0]: a1_wins, pair[1]: a2_wins},
                    "win_rates": {
                        pair[0]: a1_wins / count if count else 0,
                        pair[1]: a2_wins / count if count else 0,
                    },
                }
            )

        total_wins = sum(win_counts.values())
        win_rates = {
            agent: (cnt / total_wins if total_wins else 0.0)
            for agent, cnt in win_counts.items()
        }

        return {
            "total_conflicts": len(recent),
            "conflict_rate_per_day": len(recent) / days,
            "most_common_pairs": most_common_pairs,
            "win_rates": win_rates,
            "resolution_methods": dict(resolution_counts),
            "unique_agents": len({c.winning_agent for c in recent}),
        }

    def detect_systematic_bias(
        self, agent_id: str, days: int = 30
    ) -> dict[str, Any]:
        """Detect whether *agent_id* is systematically ignored or favoured."""
        cutoff = datetime.now() - timedelta(days=days)
        relevant = [
            c
            for c in self.conflicts
            if c.timestamp >= cutoff and agent_id in c.agents
        ]

        if not relevant:
            return {"error": "No conflicts involving this agent"}

        total = len(relevant)
        wins = sum(1 for c in relevant if c.winning_agent == agent_id)
        win_rate = wins / total
        avg_agents = sum(len(c.agents) for c in relevant) / total
        expected = 1.0 / avg_agents
        bias_score = (win_rate - expected) / expected

        if bias_score < -0.3:
            bias_type = "systematically_ignored"
        elif bias_score > 0.3:
            bias_type = "systematically_favored"
        else:
            bias_type = "fair"

        return {
            "agent_id": agent_id,
            "total_conflicts": total,
            "wins": wins,
            "win_rate": win_rate,
            "expected_win_rate": expected,
            "bias_score": bias_score,
            "bias_type": bias_type,
            "recommendation": self._generate_bias_recommendation(
                agent_id, bias_type, win_rate
            ),
        }

    def recommend_resolution_changes(
        self, days: int = 30
    ) -> list[dict[str, Any]]:
        """Return a list of conflict-resolution improvement recommendations."""
        patterns = self.get_conflict_patterns(days)
        recommendations: list[dict[str, Any]] = []

        for pair_data in patterns.get("most_common_pairs", [])[:5]:
            win_rates: dict[str, float] = pair_data["win_rates"]
            max_wr = max(win_rates.values())
            if max_wr > 0.8:
                dominant = max(win_rates, key=lambda k: win_rates[k])
                agents: list[str] = pair_data["agents"]
                other = agents[0] if agents[1] == dominant else agents[1]
                recommendations.append(
                    {
                        "type": "rebalance_priorities",
                        "agents": agents,
                        "issue": f"{dominant} wins {max_wr:.0%} of conflicts",
                        "recommendation": (
                            f"Consider: (1) Increasing {other} priority, "
                            "(2) Using confidence-based resolution, "
                            "(3) Adding a tie-breaker agent"
                        ),
                        "conflict_count": pair_data["count"],
                    }
                )

        methods: dict[str, int] = patterns.get("resolution_methods", {})
        total_methods = sum(methods.values())
        if "human_escalation" in methods and total_methods:
            rate = methods["human_escalation"] / total_methods
            if rate > 0.3:
                recommendations.append(
                    {
                        "type": "reduce_escalations",
                        "issue": f"{rate:.0%} of conflicts escalate to humans",
                        "recommendation": (
                            "High escalation rate suggests: "
                            "(1) Agents lack clear priorities, "
                            "(2) Need better tie-breaking logic"
                        ),
                    }
                )

        return recommendations

    def analyze_confidence_correlation(self, days: int = 30) -> dict[str, Any]:
        """Test whether the most confident agent wins most often."""
        cutoff = datetime.now() - timedelta(days=days)
        relevant = [c for c in self.conflicts if c.timestamp >= cutoff]
        if not relevant:
            return {"error": "No conflicts to analyse"}

        highest_wins = 0
        analysed = 0
        for conflict in relevant:
            if not conflict.confidences:
                continue
            top = max(conflict.confidences, key=lambda k: conflict.confidences[k])
            if top == conflict.winning_agent:
                highest_wins += 1
            analysed += 1

        if analysed == 0:
            return {"error": "No confidence data available"}

        rate = highest_wins / analysed
        return {
            "total_conflicts": analysed,
            "highest_confidence_wins": highest_wins,
            "correlation_rate": rate,
            "interpretation": (
                "Strong correlation"
                if rate > 0.7
                else ("Weak correlation" if rate < 0.4 else "Moderate correlation")
            ),
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _generate_bias_recommendation(
        self, agent_id: str, bias_type: str, win_rate: float
    ) -> str:
        if bias_type == "systematically_ignored":
            return (
                f"{agent_id} wins only {win_rate:.0%} of conflicts. "
                "Consider: (1) Increasing priority, "
                "(2) Reviewing confidence calibration."
            )
        if bias_type == "systematically_favored":
            return (
                f"{agent_id} wins {win_rate:.0%} of conflicts. "
                "Verify this is intentional."
            )
        return f"{agent_id} has balanced resolution ({win_rate:.0%} win rate)."

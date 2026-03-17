"""Trace sampling strategies for cost-controlled observability at scale.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import random
from enum import Enum
from typing import Any

from agentability.models import Decision


class SamplingStrategy(Enum):
    """Strategies for deciding which traces to record."""

    ALWAYS = "always"
    NEVER = "never"
    HEAD_BASED = "head_based"
    TAIL_BASED = "tail_based"
    PROBABILISTIC = "probabilistic"
    IMPORTANCE_BASED = "importance_based"
    COST_AWARE = "cost_aware"
    ADAPTIVE = "adaptive"


class TraceSampler:
    """Cost-controlled trace sampler for high-throughput agent systems.

    Args:
        strategy: The sampling strategy to apply.
        sample_rate: Probability used by probabilistic strategies (0–1).
        cost_budget_per_day: Daily cost ceiling in USD for COST_AWARE mode.
    """

    def __init__(
        self,
        strategy: SamplingStrategy = SamplingStrategy.ALWAYS,
        sample_rate: float = 1.0,
        cost_budget_per_day: float | None = None,
    ) -> None:
        self.strategy = strategy
        self.sample_rate = float(sample_rate)
        self.cost_budget_per_day = cost_budget_per_day
        self.daily_cost_spent: float = 0.0

    def should_sample_head(self, trace_context: dict[str, Any]) -> bool:
        """Decide at trace *start* whether to record this trace."""
        if self.strategy == SamplingStrategy.ALWAYS:
            return True
        if self.strategy == SamplingStrategy.NEVER:
            return False
        if self.strategy in (
            SamplingStrategy.HEAD_BASED,
            SamplingStrategy.PROBABILISTIC,
        ):
            return random.random() < self.sample_rate
        if self.strategy == SamplingStrategy.COST_AWARE:
            if self.cost_budget_per_day is not None:
                return self.daily_cost_spent < self.cost_budget_per_day
            return True
        if self.strategy == SamplingStrategy.IMPORTANCE_BASED:
            importance = float(trace_context.get("importance", 0.5))
            return random.random() < importance
        return True

    def should_sample_tail(self, trace: Any, decision: Decision) -> bool:
        """Decide at trace *end* whether to retain the completed trace."""
        if self.strategy != SamplingStrategy.TAIL_BASED:
            return True
        has_low_confidence = (
            decision.confidence is not None and decision.confidence < 0.5
        )
        has_high_cost = decision.total_cost_usd > 0.10
        has_violations = bool(decision.constraints_violated)
        return (
            has_low_confidence
            or has_high_cost
            or has_violations
            or random.random() < self.sample_rate
        )

    def record_cost(self, cost_usd: float) -> None:
        """Accumulate cost toward the daily budget."""
        self.daily_cost_spent += cost_usd

    def reset_daily_budget(self) -> None:
        """Reset the daily cost accumulator."""
        self.daily_cost_spent = 0.0


class ImportanceScorer:
    """Compute a trace importance score for importance-based sampling."""

    def score(self, trace_context: dict[str, Any]) -> float:
        """Return an importance score clamped to [0, 1]."""
        value = 0.5
        if trace_context.get("user_tier") == "premium":
            value += 0.2
        if trace_context.get("critical", False):
            value += 0.3
        if float(trace_context.get("error_rate", 0.0)) > 0.1:
            value += 0.2
        return min(1.0, value)

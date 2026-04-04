"""LLM cost analysis and optimisation.

Tracks cumulative LLM costs per model and surfaces actionable
cost-reduction recommendations.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any


@dataclass
class CostOptimization:
    """A single cost-reduction recommendation."""

    optimization_type: str
    description: str
    estimated_savings_usd: float
    confidence: float


class CostAnalyzer:
    """Analyse and optimise LLM call costs.

    Example:
        >>> analyzer = CostAnalyzer()
        >>> cost = analyzer.record_llm_call("claude-sonnet-4", 1500, 800)
        >>> suggestions = analyzer.suggest_optimizations()
    """

    # Pricing per 1 million tokens (USD, approximate March 2026).
    MODEL_PRICING: dict[str, dict[str, float]] = {
        "gpt-4-turbo":     {"input": 10.0,  "output": 30.0},
        "gpt-4":           {"input": 30.0,  "output": 60.0},
        "gpt-3.5-turbo":   {"input": 0.5,   "output": 1.5},
        "claude-opus-4":   {"input": 15.0,  "output": 75.0},
        "claude-sonnet-4": {"input": 3.0,   "output": 15.0},
        "claude-haiku-4":  {"input": 0.25,  "output": 1.25},
        "gemini-pro":      {"input": 0.5,   "output": 1.5},
        "gemini-ultra":    {"input": 10.0,  "output": 30.0},
        "default":         {"input": 1.0,   "output": 2.0},
    }

    def __init__(self) -> None:
        self._costs: list[dict[str, Any]] = []

    def record_llm_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        timestamp: datetime | None = None,
    ) -> float:
        """Record an LLM call and return its calculated cost in USD."""
        pricing = self._pricing_for(model)
        cost: float = (
            (input_tokens / 1_000_000) * pricing["input"]
            + (output_tokens / 1_000_000) * pricing["output"]
        )
        self._costs.append(
            {
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": cost,
                "timestamp": timestamp or datetime.now(),
            }
        )
        return cost

    def get_total_cost(self, time_window_hours: int | None = None) -> float:
        """Return total cost over an optional time window."""
        return sum(float(c["cost_usd"]) for c in self._filter(time_window_hours))

    def get_cost_by_model(
        self, time_window_hours: int | None = None
    ) -> dict[str, float]:
        """Return total cost grouped by model name."""
        by_model: dict[str, float] = {}
        for entry in self._filter(time_window_hours):
            by_model[entry["model"]] = (
                by_model.get(entry["model"], 0.0) + entry["cost_usd"]
            )
        return by_model

    def suggest_optimizations(self) -> list[CostOptimization]:
        """Return cost-reduction recommendations based on last 24h usage."""
        optimizations: list[CostOptimization] = []
        by_model = self.get_cost_by_model(time_window_hours=24)

        if "gpt-4" in by_model and by_model["gpt-4"] > 10.0:
            optimizations.append(
                CostOptimization(
                    optimization_type="model_downgrade",
                    description=(
                        "Consider routing simple tasks to gpt-3.5-turbo. "
                        "Estimated saving: 80% on those calls."
                    ),
                    estimated_savings_usd=by_model["gpt-4"] * 0.8,
                    confidence=0.70,
                )
            )

        if "claude-opus-4" in by_model and by_model["claude-opus-4"] > 5.0:
            optimizations.append(
                CostOptimization(
                    optimization_type="model_downgrade",
                    description=(
                        "Consider using claude-sonnet-4 for tasks that do not "
                        "require claude-opus-4 level capability."
                    ),
                    estimated_savings_usd=by_model["claude-opus-4"] * 0.7,
                    confidence=0.65,
                )
            )

        return optimizations

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _pricing_for(self, model: str) -> dict[str, float]:
        model_lower = model.lower()
        for key, pricing in self.MODEL_PRICING.items():
            if key != "default" and key in model_lower:
                return pricing
        return self.MODEL_PRICING["default"]

    def _filter(self, time_window_hours: int | None) -> list[dict[str, Any]]:
        if not time_window_hours:
            return self._costs
        cutoff = datetime.now() - timedelta(hours=time_window_hours)
        return [c for c in self._costs if c["timestamp"] >= cutoff]

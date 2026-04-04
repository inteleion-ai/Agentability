"""LLM metrics collection and cost tracking.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import time
from typing import Any
from uuid import UUID

from agentability.models import LLMMetrics
from agentability.utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Pricing table — USD per 1 million tokens (March 2026)
# ---------------------------------------------------------------------------

_LLM_PRICING: dict[str, dict[str, float]] = {
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


class LLMMetricsCollector:
    """Factory for :class:`LLMCallTracker` instances.

    Example:
        >>> collector = LLMMetricsCollector(agent_id="risk_agent")
        >>> tracker = collector.start_call(provider="anthropic", model="claude-sonnet-4")
        >>> response = client.messages.create(...)
        >>> metrics = tracker.complete(
        ...     prompt_tokens=response.usage.input_tokens,
        ...     completion_tokens=response.usage.output_tokens,
        ... )
    """

    def __init__(
        self,
        agent_id: str,
        decision_id: UUID | None = None,
    ) -> None:
        self.agent_id = agent_id
        self.decision_id = decision_id

    def start_call(
        self,
        provider: str,
        model: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        is_streaming: bool = False,
    ) -> LLMCallTracker:
        """Begin timing a new LLM API call."""
        return LLMCallTracker(
            agent_id=self.agent_id,
            decision_id=self.decision_id,
            provider=provider,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            is_streaming=is_streaming,
        )

    @staticmethod
    def calculate_cost(
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """Calculate the cost of an LLM call using substring model matching."""
        model_lower = model.lower()
        pricing: dict[str, float] = _LLM_PRICING["default"]
        for key, p in _LLM_PRICING.items():
            if key != "default" and key in model_lower:
                pricing = p
                break
        else:
            logger.warning(
                "Unknown model '%s' — using default pricing ($1/$2 per 1M tokens).",
                model,
            )
        return (
            (prompt_tokens / 1_000_000) * pricing["input"]
            + (completion_tokens / 1_000_000) * pricing["output"]
        )


class LLMCallTracker:
    """Times a single LLM API call and produces an :class:`~agentability.models.LLMMetrics`."""

    def __init__(
        self,
        agent_id: str,
        provider: str,
        model: str,
        decision_id: UUID | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        is_streaming: bool = False,
    ) -> None:
        self.agent_id = agent_id
        self.decision_id = decision_id
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.is_streaming = is_streaming
        self._start_time: float = time.time()
        self._first_token_time: float | None = None
        self.chunks_received: int = 0
        self.retry_count: int = 0
        self.rate_limited: bool = False

    def record_first_token(self) -> None:
        """Record the wall-clock time when the first streaming token arrives."""
        if self._first_token_time is None:
            self._first_token_time = time.time()

    def record_chunk(self) -> None:
        """Increment the streaming chunk counter."""
        self.chunks_received += 1

    def record_retry(self) -> None:
        """Increment the retry counter."""
        self.retry_count += 1

    def record_rate_limit(self) -> None:
        """Mark this call as having hit a rate limit."""
        self.rate_limited = True

    def complete(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        finish_reason: str | None = None,
        **metadata: Any,
    ) -> LLMMetrics:
        """Stop timing and return a fully-populated :class:`~agentability.models.LLMMetrics`."""
        latency_ms = (time.time() - self._start_time) * 1000
        ttft_ms: float | None = None
        if self._first_token_time is not None:
            ttft_ms = (self._first_token_time - self._start_time) * 1000

        cost_usd = LLMMetricsCollector.calculate_cost(
            self.model, prompt_tokens, completion_tokens
        )

        return LLMMetrics(
            agent_id=self.agent_id,
            decision_id=self.decision_id,
            provider=self.provider,
            model=self.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            latency_ms=latency_ms,
            time_to_first_token_ms=ttft_ms,
            cost_usd=cost_usd,
            finish_reason=finish_reason,
            is_streaming=self.is_streaming,
            chunks_received=self.chunks_received if self.is_streaming else None,
            rate_limited=self.rate_limited,
            retry_count=self.retry_count,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            metadata=dict(metadata),
        )

"""Anthropic SDK auto-instrumentation for Agentability.

Wraps the Anthropic Python client so that every ``messages.create()`` call
is automatically recorded in the Agentability tracer.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import time
from typing import Any

from agentability.metrics.llm_metrics import LLMMetricsCollector
from agentability.tracer import Tracer
from agentability.utils.logger import get_logger

logger = get_logger(__name__)


class AnthropicInstrumentation:
    """Wraps an Anthropic client to record LLM calls automatically.

    Example:
        >>> import anthropic
        >>> from agentability import Tracer
        >>> from agentability.integrations.anthropic_sdk import (
        ...     AnthropicInstrumentation,
        ... )
        >>> tracer = Tracer(offline_mode=True)
        >>> client = anthropic.Anthropic()
        >>> client = AnthropicInstrumentation(tracer).wrap_client(client)
        >>> # All subsequent client.messages.create() calls are tracked.

    Args:
        tracer: An initialised :class:`~agentability.tracer.Tracer` instance.
        agent_id: Identifier used for all telemetry emitted by this wrapper.
    """

    def __init__(
        self,
        tracer: Tracer,
        agent_id: str = "anthropic_agent",
    ) -> None:
        self.tracer = tracer
        self.agent_id = agent_id

    def wrap_client(self, client: Any) -> Any:
        """Patch ``client.messages.create`` with Agentability instrumentation.

        Args:
            client: An ``anthropic.Anthropic`` or ``anthropic.AsyncAnthropic``
                instance.

        Returns:
            The same client object with instrumentation applied in-place.
        """
        original_create = client.messages.create
        tracer = self.tracer
        agent_id = self.agent_id

        def tracked_create(*args: Any, **kwargs: Any) -> Any:
            start = time.time()
            response = original_create(*args, **kwargs)
            latency_ms = (time.time() - start) * 1000

            prompt_tokens = 0
            completion_tokens = 0
            model = kwargs.get("model", "claude")

            if hasattr(response, "usage") and response.usage:
                prompt_tokens = getattr(response.usage, "input_tokens", 0)
                completion_tokens = getattr(response.usage, "output_tokens", 0)

            cost_usd = LLMMetricsCollector.calculate_cost(
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )

            tracer.record_llm_call(
                agent_id=agent_id,
                provider="anthropic",
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=latency_ms,
                cost_usd=cost_usd,
                finish_reason=getattr(response, "stop_reason", None),
            )

            return response

        client.messages.create = tracked_create
        return client

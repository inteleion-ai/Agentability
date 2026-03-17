"""LangChain auto-instrumentation for Agentability.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import time
from typing import Any
from uuid import UUID

from agentability.models import DecisionType
from agentability.tracer import Tracer
from agentability.utils.logger import get_logger

logger = get_logger(__name__)


class AgentabilityLangChainCallback:
    """LangChain ``BaseCallbackHandler`` that records Agentability telemetry.

    Example:
        >>> from agentability import Tracer
        >>> from agentability.integrations.langchain import AgentabilityLangChainCallback
        >>> tracer = Tracer(offline_mode=True)
        >>> callback = AgentabilityLangChainCallback(tracer=tracer,
        ...                                          agent_id="my_agent")
        >>> chain.invoke({"input": "..."}, config={"callbacks": [callback]})

    Args:
        tracer: An initialised :class:`~agentability.tracer.Tracer`.
        agent_id: Identifier used for all emitted telemetry.
    """

    def __init__(
        self,
        tracer: Tracer,
        agent_id: str = "langchain_agent",
    ) -> None:
        self.tracer = tracer
        self.agent_id = agent_id
        self._llm_start_times: dict[str, float] = {}
        self._chain_contexts: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # LLM callbacks
    # ------------------------------------------------------------------

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Record when an LLM starts generating."""
        self._llm_start_times[str(run_id)] = time.time()

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Record LLM metrics when generation finishes."""
        start = self._llm_start_times.pop(str(run_id), time.time())
        latency_ms = (time.time() - start) * 1000

        prompt_tokens = 0
        completion_tokens = 0
        model = "unknown"

        if hasattr(response, "llm_output") and response.llm_output:
            usage = response.llm_output.get("token_usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            model = response.llm_output.get("model_name", model)

        self.tracer.record_llm_call(
            agent_id=self.agent_id,
            provider="langchain",
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            cost_usd=0.0,
        )

    # ------------------------------------------------------------------
    # Chain callbacks
    # ------------------------------------------------------------------

    def on_chain_start(
        self,
        serialized: dict[str, Any],
        inputs: dict[str, Any],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Record chain start time and metadata."""
        chain_name: str = serialized.get(
            "name", serialized.get("id", ["chain"])[-1]
        )
        self._chain_contexts[str(run_id)] = {
            "chain_name": chain_name,
            "inputs": inputs,
            "start_time": time.time(),
        }

    def on_chain_end(
        self,
        outputs: dict[str, Any],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Record a completed chain execution as a decision."""
        ctx: dict[str, Any] | None = self._chain_contexts.pop(str(run_id), None)
        if ctx is None:
            return

        latency_ms = (time.time() - ctx["start_time"]) * 1000

        with self.tracer.trace_decision(
            agent_id=self.agent_id,
            decision_type=DecisionType.GENERATION,
            input_data=ctx["inputs"],
        ) as decision_ctx:
            decision_ctx.set_metadata("chain_name", ctx["chain_name"])
            decision_ctx.set_metadata("latency_ms", latency_ms)
            self.tracer.record_decision(
                output=outputs,
                reasoning=[f"LangChain chain '{ctx['chain_name']}' completed"],
            )

    # ------------------------------------------------------------------
    # Tool callbacks
    # ------------------------------------------------------------------

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Record tool start time."""
        self._llm_start_times[f"tool_{run_id}"] = time.time()

    def on_tool_end(
        self,
        output: str,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Clear tool timer on completion."""
        self._llm_start_times.pop(f"tool_{run_id}", None)

    # ------------------------------------------------------------------
    # Agent callbacks (no-op stubs — override if needed)
    # ------------------------------------------------------------------

    def on_agent_action(
        self, action: Any, *, run_id: UUID, **kwargs: Any
    ) -> None:
        """Called when the agent selects an action."""

    def on_agent_finish(
        self, finish: Any, *, run_id: UUID, **kwargs: Any
    ) -> None:
        """Called when the agent produces its final answer."""

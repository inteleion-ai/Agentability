"""OpenAI Agents SDK integration for Agentability.

Instruments OpenAI Agents SDK ``Runner.run()`` lifecycle, handoff events,
and tool call executions — capturing them as Agentability decisions so they
appear in the dashboard alongside all other agent frameworks.

Usage::

    from agents import Agent, Runner
    from agentability import Tracer
    from agentability.integrations.openai_agents import OpenAIAgentsInstrumentation

    tracer = Tracer(offline_mode=True)
    instrumentation = OpenAIAgentsInstrumentation(tracer=tracer)

    agent = Agent(name="triage_agent", model="gpt-4o", instructions="...")
    result = instrumentation.run_sync(agent, "What is the refund policy?")

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any
from uuid import UUID

from agentability.models import ConflictType, DecisionType
from agentability.utils.logger import get_logger

if TYPE_CHECKING:
    from agentability.tracer import Tracer

logger = get_logger(__name__)


class OpenAIAgentsInstrumentation:
    """Instruments OpenAI Agents SDK for Agentability observability.

    Captures:
        - Agent ``Runner.run()`` lifecycle as a GENERATION decision.
        - Tool call inputs/outputs as TOOL_SELECTION decisions.
        - Handoffs between agents as DELEGATION decisions.
        - Token usage and cost from the final response.

    Args:
        tracer: Agentability Tracer instance.
        default_session_id: Optional session ID applied to all decisions.

    Example::

        from agents import Agent, Runner
        from agentability import Tracer
        from agentability.integrations.openai_agents import OpenAIAgentsInstrumentation

        tracer = Tracer(offline_mode=True)
        instr = OpenAIAgentsInstrumentation(tracer=tracer)

        agent = Agent(
            name="customer_support",
            model="gpt-4o",
            instructions="You are a helpful customer support agent.",
        )

        # Synchronous run (wraps Runner.run_sync)
        result = instr.run_sync(agent, "My order hasn't arrived.")

        # Async run
        result = await instr.run_async(agent, "My order hasn't arrived.")
    """

    def __init__(
        self,
        tracer: Tracer,
        default_session_id: str | None = None,
    ) -> None:
        self.tracer = tracer
        self.default_session_id = default_session_id
        self._verify_import()

    def _verify_import(self) -> None:
        try:
            import agents  # noqa: F401
        except ImportError:
            logger.warning(
                "openai-agents package not installed. "
                "Install with: pip install openai-agents"
            )

    def run_sync(
        self,
        agent: Any,
        input_text: str,
        session_id: str | None = None,
        **runner_kwargs: Any,
    ) -> Any:
        """Run an OpenAI agent synchronously with full Agentability tracing.

        Args:
            agent: An ``agents.Agent`` instance.
            input_text: The user input string.
            session_id: Optional session ID for this run.
            **runner_kwargs: Extra kwargs forwarded to ``Runner.run_sync()``.

        Returns:
            The ``RunResult`` from the OpenAI Agents SDK.
        """
        try:
            from agents import Runner
        except ImportError as e:
            raise ImportError(
                "openai-agents not installed. Run: pip install openai-agents"
            ) from e

        agent_id = getattr(agent, "name", "openai_agent")
        sid = session_id or self.default_session_id
        t0 = time.time()

        with self.tracer.trace_decision(
            agent_id=agent_id,
            decision_type=DecisionType.GENERATION,
            session_id=sid,
            input_data={"input": input_text},
            tags=["openai-agents", agent_id],
        ) as ctx:
            try:
                result = Runner.run_sync(agent, input_text, **runner_kwargs)
                latency_ms = (time.time() - t0) * 1000

                # Extract token usage from run result
                usage = getattr(result, "usage", None)
                prompt_tokens = getattr(usage, "input_tokens", 0) if usage else 0
                completion_tokens = getattr(usage, "output_tokens", 0) if usage else 0
                total_tokens = prompt_tokens + completion_tokens

                # Estimate cost (GPT-4o pricing as of 2026)
                model = getattr(agent, "model", "gpt-4o")
                cost = self._estimate_cost(model, prompt_tokens, completion_tokens)

                if total_tokens > 0:
                    self.tracer.record_llm_call(
                        agent_id=agent_id,
                        provider="openai",
                        model=model,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        latency_ms=latency_ms,
                        cost_usd=cost,
                        finish_reason="stop",
                    )

                # Extract final output text
                final_output = getattr(result, "final_output", None)
                output_text = str(final_output) if final_output else ""

                ctx.set_confidence(0.85)  # default — OpenAI doesn't expose confidence
                ctx.add_reasoning_step(
                    f"OpenAI Agents SDK: agent={agent_id}, "
                    f"model={model}, tokens={total_tokens}"
                )

                self.tracer.record_decision(
                    output={"response": output_text, "model": model},
                    reasoning=[f"Completed via {model} in {latency_ms:.0f}ms"],
                    data_sources=["openai_api"],
                )

                # Record handoffs as delegation decisions
                new_agents = getattr(result, "new_agents", [])
                for target in new_agents:
                    self._record_handoff(agent_id, target, sid, output_text)

                return result

            except Exception as exc:
                self.tracer.record_decision(
                    output={"error": str(exc)},
                    confidence=0.0,
                    uncertainties=[f"Agent execution failed: {exc}"],
                )
                raise

    async def run_async(
        self,
        agent: Any,
        input_text: str,
        session_id: str | None = None,
        **runner_kwargs: Any,
    ) -> Any:
        """Run an OpenAI agent asynchronously with full Agentability tracing.

        Args:
            agent: An ``agents.Agent`` instance.
            input_text: The user input string.
            session_id: Optional session ID for this run.
            **runner_kwargs: Extra kwargs forwarded to ``Runner.run()``.

        Returns:
            The ``RunResult`` from the OpenAI Agents SDK.
        """
        try:
            from agents import Runner
        except ImportError as e:
            raise ImportError(
                "openai-agents not installed. Run: pip install openai-agents"
            ) from e

        agent_id = getattr(agent, "name", "openai_agent")
        sid = session_id or self.default_session_id
        t0 = time.time()

        with self.tracer.trace_decision(
            agent_id=agent_id,
            decision_type=DecisionType.GENERATION,
            session_id=sid,
            input_data={"input": input_text},
            tags=["openai-agents", agent_id],
        ) as ctx:
            try:
                result = await Runner.run(agent, input_text, **runner_kwargs)
                latency_ms = (time.time() - t0) * 1000

                usage = getattr(result, "usage", None)
                prompt_tokens = getattr(usage, "input_tokens", 0) if usage else 0
                completion_tokens = getattr(usage, "output_tokens", 0) if usage else 0
                total_tokens = prompt_tokens + completion_tokens
                model = getattr(agent, "model", "gpt-4o")
                cost = self._estimate_cost(model, prompt_tokens, completion_tokens)

                if total_tokens > 0:
                    self.tracer.record_llm_call(
                        agent_id=agent_id,
                        provider="openai",
                        model=model,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        latency_ms=latency_ms,
                        cost_usd=cost,
                        finish_reason="stop",
                    )

                final_output = getattr(result, "final_output", None)
                ctx.set_confidence(0.85)
                self.tracer.record_decision(
                    output={"response": str(final_output), "model": model},
                    reasoning=[f"Async run via {model} in {latency_ms:.0f}ms"],
                    data_sources=["openai_api"],
                )
                return result

            except Exception as exc:
                self.tracer.record_decision(
                    output={"error": str(exc)},
                    confidence=0.0,
                    uncertainties=[f"Async agent execution failed: {exc}"],
                )
                raise

    def instrument_tool(
        self,
        tool_fn: Any,
        agent_id: str,
        session_id: str | None = None,
    ) -> Any:
        """Wrap an OpenAI Agents tool function to trace its invocations.

        Args:
            tool_fn: The tool function decorated with ``@function_tool``.
            agent_id: Agent that owns this tool.
            session_id: Optional session grouping.

        Returns:
            Wrapped version of ``tool_fn`` with Agentability tracing.

        Example::

            from agents import function_tool

            @function_tool
            def search_kb(query: str) -> str:
                return kb.search(query)

            search_kb = instr.instrument_tool(search_kb, agent_id="support_agent")
        """
        import functools

        @functools.wraps(tool_fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            t0 = time.time()
            tool_name = getattr(tool_fn, "__name__", "unknown_tool")

            with self.tracer.trace_decision(
                agent_id=agent_id,
                decision_type=DecisionType.TOOL_SELECTION,
                session_id=session_id or self.default_session_id,
                input_data={"tool": tool_name, "args": str(args), "kwargs": str(kwargs)},
                tags=["tool_call", tool_name],
            ) as ctx:
                try:
                    result = tool_fn(*args, **kwargs)
                    latency_ms = (time.time() - t0) * 1000
                    ctx.set_confidence(0.95)
                    ctx.add_reasoning_step(
                        f"Tool '{tool_name}' executed in {latency_ms:.0f}ms"
                    )
                    self.tracer.record_decision(
                        output={"result": str(result)},
                        reasoning=[f"Tool call: {tool_name}"],
                        data_sources=["tool_execution"],
                    )
                    return result
                except Exception as exc:
                    self.tracer.record_decision(
                        output={"error": str(exc)},
                        confidence=0.0,
                        uncertainties=[f"Tool '{tool_name}' failed: {exc}"],
                    )
                    raise

        return wrapper

    def _record_handoff(
        self,
        source_agent: str,
        target_agent: Any,
        session_id: str | None,
        context: str,
    ) -> None:
        """Record an agent handoff as a DELEGATION decision."""
        target_name = getattr(target_agent, "name", str(target_agent))
        with self.tracer.trace_decision(
            agent_id=source_agent,
            decision_type=DecisionType.DELEGATION,
            session_id=session_id,
            input_data={"handoff_to": target_name, "context": context[:200]},
            tags=["handoff"],
        ) as ctx:
            ctx.set_confidence(0.90)
            self.tracer.record_decision(
                output={"delegated_to": target_name},
                reasoning=[f"Handoff: {source_agent} → {target_name}"],
            )

    def _estimate_cost(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """Estimate cost in USD based on known model pricing (2026)."""
        # Pricing per million tokens: (input, output)
        pricing: dict[str, tuple[float, float]] = {
            "gpt-4o":           (2.50,  10.00),
            "gpt-4o-mini":      (0.15,   0.60),
            "gpt-4":            (30.00,  60.00),
            "gpt-4-turbo":      (10.00,  30.00),
            "gpt-3.5-turbo":    (0.50,   1.50),
            "o1":               (15.00,  60.00),
            "o1-mini":          (3.00,   12.00),
            "o3-mini":          (1.10,   4.40),
        }
        inp_price, out_price = pricing.get(model, (2.50, 10.00))
        return (prompt_tokens / 1_000_000) * inp_price + (
            completion_tokens / 1_000_000
        ) * out_price

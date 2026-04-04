"""AutoGen auto-instrumentation for Agentability.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from typing import Any

from agentability.models import DecisionType
from agentability.tracer import Tracer
from agentability.utils.logger import get_logger

logger = get_logger(__name__)


class AutoGenInstrumentation:
    """Wrap AutoGen ``ConversableAgent.generate_reply`` with telemetry.

    Example:
        >>> tracer = Tracer(offline_mode=True)
        >>> agent = AutoGenInstrumentation(tracer).instrument_agent(agent)

    Args:
        tracer: Initialised :class:`~agentability.tracer.Tracer`.
        session_id: Optional shared session identifier.
    """

    def __init__(
        self,
        tracer: Tracer,
        session_id: str | None = None,
    ) -> None:
        self.tracer = tracer
        self.session_id = session_id

    def instrument_agent(self, agent: Any) -> Any:
        """Wrap ``agent.generate_reply`` with Agentability telemetry."""
        original_generate = getattr(agent, "generate_reply", None)
        if original_generate is None:
            logger.warning(
                "Agent '%s' has no generate_reply method — skipping.",
                getattr(agent, "name", "unknown"),
            )
            return agent

        tracer = self.tracer
        session_id = self.session_id
        agent_id: str = str(getattr(agent, "name", agent.__class__.__name__))

        def _instrumented_generate_reply(
            messages: list[dict[str, Any]] | None = None,
            sender: Any | None = None,
            **kwargs: Any,
        ) -> str | None:
            last_message: dict[str, Any] = (messages or [{}])[-1]
            input_text: str = str(last_message.get("content", ""))[:300]

            with tracer.trace_decision(
                agent_id=agent_id,
                decision_type=DecisionType.GENERATION,
                session_id=session_id,
                input_data={"message": input_text},
                metadata={
                    "sender": str(getattr(sender, "name", sender)),
                    "message_count": len(messages or []),
                },
            ):
                raw_reply = original_generate(
                    messages=messages, sender=sender, **kwargs
                )
                tracer.record_decision(
                    output={"reply": str(raw_reply)[:500] if raw_reply is not None else ""},
                    reasoning=[f"AutoGen agent '{agent_id}' generated reply"],
                )
            return None if raw_reply is None else str(raw_reply)

        agent.generate_reply = _instrumented_generate_reply
        return agent

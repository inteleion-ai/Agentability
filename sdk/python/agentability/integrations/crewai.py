"""CrewAI auto-instrumentation for Agentability.

Instruments CrewAI crews and agents to automatically record task-level
decisions and inter-agent conflicts.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from typing import Any

from agentability.models import DecisionType
from agentability.tracer import Tracer
from agentability.utils.logger import get_logger

logger = get_logger(__name__)


class CrewAIInstrumentation:
    """Instruments CrewAI crews so that every task execution is recorded.

    Example:
        >>> from crewai import Crew
        >>> from agentability import Tracer
        >>> from agentability.integrations.crewai import CrewAIInstrumentation
        >>> tracer = Tracer(offline_mode=True)
        >>> crew = Crew(agents=[...], tasks=[...])
        >>> crew = CrewAIInstrumentation(tracer).instrument_crew(crew)
        >>> result = crew.kickoff()

    Args:
        tracer: An initialised :class:`~agentability.tracer.Tracer` instance.
        session_id: Optional session identifier shared across the crew run.
    """

    def __init__(
        self,
        tracer: Tracer,
        session_id: str | None = None,
    ) -> None:
        self.tracer = tracer
        self.session_id = session_id

    def instrument_crew(self, crew: Any) -> Any:
        """Wrap a CrewAI ``Crew`` instance with Agentability instrumentation.

        Patches ``crew.kickoff`` so that the overall crew run is captured as a
        :attr:`~agentability.models.DecisionType.COORDINATION` decision.

        Args:
            crew: A ``crewai.Crew`` instance.

        Returns:
            The same crew object with instrumentation applied in-place.
        """
        original_kickoff = getattr(crew, "kickoff", None)
        if original_kickoff is None:
            logger.warning("Crew object has no 'kickoff' method — skipping.")
            return crew

        tracer = self.tracer
        session_id = self.session_id

        def instrumented_kickoff(*args: Any, **kwargs: Any) -> Any:
            agent_id = f"crew_{crew.__class__.__name__}"
            with tracer.trace_decision(
                agent_id=agent_id,
                decision_type=DecisionType.COORDINATION,
                session_id=session_id,
                metadata={"crew_class": crew.__class__.__name__},
            ) as ctx:
                result = original_kickoff(*args, **kwargs)
                ctx.set_metadata("crew_result_type", type(result).__name__)
                tracer.record_decision(
                    output={"result": str(result)[:500]},
                    reasoning=["CrewAI crew kickoff completed"],
                )
            return result

        crew.kickoff = instrumented_kickoff
        return crew

    def instrument_agent(self, agent: Any) -> Any:
        """Wrap a CrewAI ``Agent`` instance with Agentability instrumentation.

        Patches ``agent.execute_task`` so that individual task executions are
        captured as :attr:`~agentability.models.DecisionType.EXECUTION`
        decisions.

        Args:
            agent: A ``crewai.Agent`` instance.

        Returns:
            The same agent object with instrumentation applied in-place.
        """
        original_execute = getattr(agent, "execute_task", None)
        if original_execute is None:
            logger.warning("Agent has no 'execute_task' method — skipping.")
            return agent

        tracer = self.tracer
        session_id = self.session_id
        agent_id = getattr(agent, "role", agent.__class__.__name__)

        def instrumented_execute(task: Any, *args: Any, **kwargs: Any) -> Any:
            task_description = getattr(task, "description", str(task))[:200]
            with tracer.trace_decision(
                agent_id=agent_id,
                decision_type=DecisionType.EXECUTION,
                session_id=session_id,
                input_data={"task": task_description},
            ) as ctx:
                result = original_execute(task, *args, **kwargs)
                ctx.set_metadata("task_description", task_description)
                tracer.record_decision(
                    output={"result": str(result)[:500]},
                    reasoning=[f"Agent '{agent_id}' executed task"],
                )
            return result

        agent.execute_task = instrumented_execute
        return agent

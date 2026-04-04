"""LangGraph integration for Agentability.

Instruments LangGraph stateful graph executions at the node level.
Each node invocation becomes an Agentability decision, and each edge
transition is recorded as a ROUTING decision.

Usage::

    from langgraph.graph import StateGraph
    from agentability import Tracer
    from agentability.integrations.langgraph import LangGraphInstrumentation

    tracer = Tracer(offline_mode=True)
    instr = LangGraphInstrumentation(tracer=tracer, graph_name="support_flow")

    builder = StateGraph(MyState)
    builder.add_node("triage", instr.wrap_node("triage", triage_fn))
    builder.add_node("resolve", instr.wrap_node("resolve", resolve_fn))
    builder.add_edge("triage", "resolve")
    graph = builder.compile()

    result = graph.invoke({"message": "I need a refund"})

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import functools
import time
from typing import Any, Callable
from uuid import uuid4

from agentability.models import DecisionType
from agentability.utils.logger import get_logger

try:
    from agentability.tracer import Tracer
except ImportError:
    Tracer = Any  # type: ignore[misc,assignment]

logger = get_logger(__name__)


class LangGraphInstrumentation:
    """Instruments LangGraph graphs for Agentability observability.

    Captures:
        - Each node execution as an Agentability GENERATION decision.
        - Edge transitions as ROUTING decisions.
        - State diffs between node inputs and outputs.
        - Per-node latency and any errors.

    Args:
        tracer: Agentability Tracer instance.
        graph_name: Human-readable name for this graph (used as session prefix).

    Example::

        from langgraph.graph import StateGraph, END
        from agentability import Tracer
        from agentability.integrations.langgraph import LangGraphInstrumentation
        from typing import TypedDict

        class State(TypedDict):
            message: str
            response: str

        def triage(state: State) -> State:
            return {"response": "routed to billing"}

        def billing(state: State) -> State:
            return {"response": "refund approved"}

        tracer = Tracer(offline_mode=True)
        instr = LangGraphInstrumentation(tracer=tracer, graph_name="support")

        builder = StateGraph(State)
        builder.add_node("triage", instr.wrap_node("triage", triage))
        builder.add_node("billing", instr.wrap_node("billing", billing))
        builder.add_edge("triage", "billing")
        builder.add_edge("billing", END)
        builder.set_entry_point("triage")
        graph = builder.compile()

        result = graph.invoke({"message": "I need a refund", "response": ""})
    """

    def __init__(
        self,
        tracer: Any,
        graph_name: str = "langgraph",
    ) -> None:
        self.tracer = tracer
        self.graph_name = graph_name

    def wrap_node(
        self,
        node_name: str,
        node_fn: Callable[..., Any],
        agent_id: str | None = None,
        decision_type: DecisionType = DecisionType.GENERATION,
    ) -> Callable[..., Any]:
        """Wrap a LangGraph node function with Agentability tracing.

        Args:
            node_name: The node's name in the graph (e.g. ``"triage"``).
            node_fn: The original node callable ``(state) -> state_update``.
            agent_id: Override agent ID. Defaults to
                ``"{graph_name}.{node_name}"``.
            decision_type: Agentability decision type. Default GENERATION.

        Returns:
            Wrapped node function with identical signature.
        """
        effective_agent_id = agent_id or f"{self.graph_name}.{node_name}"

        @functools.wraps(node_fn)
        def wrapper(state: Any) -> Any:
            # Capture input state snapshot
            input_snapshot = self._snapshot_state(state)
            session_id = f"{self.graph_name}_{uuid4().hex[:8]}"
            t0 = time.time()

            with self.tracer.trace_decision(
                agent_id=effective_agent_id,
                decision_type=decision_type,
                session_id=session_id,
                input_data={"node": node_name, "state": input_snapshot},
                tags=["langgraph", self.graph_name, node_name],
            ) as ctx:
                try:
                    output = node_fn(state)
                    latency_ms = (time.time() - t0) * 1000
                    output_snapshot = self._snapshot_state(output)

                    # Compute state delta for provenance
                    delta = self._compute_delta(input_snapshot, output_snapshot)

                    ctx.add_reasoning_step(
                        f"Node '{node_name}' executed in {latency_ms:.0f}ms"
                    )
                    if delta:
                        ctx.add_reasoning_step(
                            f"State changes: {', '.join(delta.keys())}"
                        )

                    ctx.set_confidence(0.90)
                    self.tracer.record_decision(
                        output={
                            "node": node_name,
                            "state_update": output_snapshot,
                            "changed_keys": list(delta.keys()),
                        },
                        reasoning=[
                            f"LangGraph node: {self.graph_name}.{node_name}",
                            f"Latency: {latency_ms:.0f}ms",
                        ],
                        data_sources=["langgraph_state"],
                    )
                    return output

                except Exception as exc:
                    latency_ms = (time.time() - t0) * 1000
                    ctx.set_confidence(0.0)
                    ctx.add_reasoning_step(f"Node '{node_name}' FAILED: {exc}")
                    self.tracer.record_decision(
                        output={"error": str(exc), "node": node_name},
                        confidence=0.0,
                        uncertainties=[f"Node execution failed: {exc}"],
                        constraints_violated=[f"node_{node_name}_must_succeed"],
                    )
                    logger.error(
                        "LangGraph node '%s' failed: %s", node_name, exc
                    )
                    raise

        return wrapper

    def wrap_conditional_edge(
        self,
        source_node: str,
        router_fn: Callable[..., str],
        agent_id: str | None = None,
    ) -> Callable[..., str]:
        """Wrap a LangGraph conditional edge router with ROUTING tracing.

        Args:
            source_node: The source node name.
            router_fn: The routing function ``(state) -> next_node_name``.
            agent_id: Override agent ID. Defaults to
                ``"{graph_name}.{source_node}.router"``.

        Returns:
            Wrapped router with identical signature.

        Example::

            def route_ticket(state):
                if "billing" in state["message"]:
                    return "billing"
                return "general"

            builder.add_conditional_edges(
                "triage",
                instr.wrap_conditional_edge("triage", route_ticket),
            )
        """
        effective_agent_id = (
            agent_id or f"{self.graph_name}.{source_node}.router"
        )

        @functools.wraps(router_fn)
        def wrapper(state: Any) -> str:
            input_snapshot = self._snapshot_state(state)
            t0 = time.time()

            with self.tracer.trace_decision(
                agent_id=effective_agent_id,
                decision_type=DecisionType.ROUTING,
                input_data={
                    "source_node": source_node,
                    "state": input_snapshot,
                },
                tags=["langgraph", "routing", self.graph_name],
            ) as ctx:
                try:
                    destination = router_fn(state)
                    latency_ms = (time.time() - t0) * 1000
                    ctx.set_confidence(0.95)
                    ctx.add_reasoning_step(
                        f"Routing: {source_node} → {destination} "
                        f"({latency_ms:.0f}ms)"
                    )
                    self.tracer.record_decision(
                        output={
                            "from_node": source_node,
                            "to_node": destination,
                        },
                        reasoning=[
                            f"LangGraph conditional edge: "
                            f"{source_node} → {destination}"
                        ],
                    )
                    return destination

                except Exception as exc:
                    ctx.set_confidence(0.0)
                    self.tracer.record_decision(
                        output={"error": str(exc)},
                        confidence=0.0,
                        uncertainties=[f"Routing failed: {exc}"],
                    )
                    raise

        return wrapper

    def instrument_graph(
        self,
        graph: Any,
        node_names: list[str] | None = None,
    ) -> Any:
        """Instrument all nodes of a compiled LangGraph graph in-place.

        This is a convenience method for post-compilation instrumentation
        when you don't want to wrap each node manually.

        Args:
            graph: A compiled LangGraph ``CompiledGraph`` instance.
            node_names: Specific node names to instrument. If None,
                instruments all nodes found in ``graph.nodes``.

        Returns:
            The same graph object (modified in-place).
        """
        nodes = getattr(graph, "nodes", {})
        target_names = node_names or list(nodes.keys())

        for name in target_names:
            if name in nodes and callable(nodes[name]):
                original = nodes[name]
                nodes[name] = self.wrap_node(name, original)
                logger.debug("Instrumented LangGraph node: %s", name)

        return graph

    # ── Private helpers ────────────────────────────────────────────────────

    def _snapshot_state(self, state: Any) -> dict[str, Any]:
        """Safely snapshot a LangGraph state dict."""
        if isinstance(state, dict):
            return {
                k: str(v)[:200] if not isinstance(v, (int, float, bool)) else v
                for k, v in state.items()
            }
        return {"_raw": str(state)[:500]}

    def _compute_delta(
        self,
        before: dict[str, Any],
        after: dict[str, Any],
    ) -> dict[str, Any]:
        """Return keys that changed between two state snapshots."""
        delta: dict[str, Any] = {}
        all_keys = set(before) | set(after)
        for key in all_keys:
            v_before = before.get(key)
            v_after = after.get(key)
            if v_before != v_after:
                delta[key] = {"before": v_before, "after": v_after}
        return delta

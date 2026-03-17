"""Multi-agent system example with conflict detection.

Demonstrates how to track competing agents, record a conflict, and
resolve it via a supervisor agent — all with full decision provenance.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from uuid import UUID, uuid4

from agentability import Tracer
from agentability.models import ConflictType, DecisionType


def main() -> None:
    """Run the multi-agent conflict-detection walkthrough."""
    tracer = Tracer(offline_mode=True, database_path="multi_agent_example.db")

    print("Agentability — Multi-Agent Conflict Example")
    print("=" * 60)
    print("Scenario: Premium customer support routing")

    session_id = str(uuid4())

    # ------------------------------------------------------------------
    # Agent 1: Routing Agent  (optimises for speed)
    # ------------------------------------------------------------------
    print("\n[1] Routing Agent")

    routing_decision_id: UUID
    with tracer.trace_decision(
        agent_id="routing_agent",
        session_id=session_id,
        decision_type=DecisionType.DELEGATION,
        input_data={"ticket": "My order is late", "priority": "high"},
        tags=["routing", "customer_support"],
    ) as ctx:
        routing_decision_id = ctx.decision_id
        tracer.record_decision(
            output={"route_to": "bot", "escalate": False},
            confidence=0.78,
            reasoning=[
                "Simple delivery inquiry",
                "Bot can handle in <60 seconds",
                "No human needed for efficiency",
            ],
            assumptions=["Customer wants fast response over personalised service"],
        )

    print(f"    Decision ID : {routing_decision_id}")
    print("    Route to    : BOT  |  Goal: maximise speed")

    # ------------------------------------------------------------------
    # Agent 2: Quality Agent  (optimises for satisfaction)
    # ------------------------------------------------------------------
    print("\n[2] Quality Agent")

    quality_decision_id: UUID
    with tracer.trace_decision(
        agent_id="quality_agent",
        session_id=session_id,
        decision_type=DecisionType.COORDINATION,
        input_data={"ticket": "My order is late", "customer_tier": "premium"},
        tags=["quality_control", "customer_support"],
    ) as ctx:
        quality_decision_id = ctx.decision_id
        tracer.record_decision(
            output={"route_to": "human", "escalate": True},
            confidence=0.92,
            reasoning=[
                "Premium customer detected",
                "Delivery issues require empathy",
                "Human agent provides better experience",
            ],
            assumptions=["Customer values personalised service over speed"],
        )

    print(f"    Decision ID : {quality_decision_id}")
    print("    Route to    : HUMAN  |  Goal: maximise satisfaction")

    # ------------------------------------------------------------------
    # Conflict
    # ------------------------------------------------------------------
    print("\n[3] Conflict detected — recording")

    conflict_id = tracer.record_conflict(
        session_id=session_id,
        conflict_type=ConflictType.GOAL_CONFLICT,
        involved_agents=["routing_agent", "quality_agent"],
        agent_positions={
            "routing_agent": {
                "route_to": "bot",
                "goal": "minimise_response_time",
                "utility": 0.95,
            },
            "quality_agent": {
                "route_to": "human",
                "goal": "maximise_satisfaction",
                "utility": 0.90,
            },
        },
        severity=0.75,
        resolution_strategy="quality_override",
        nash_equilibrium={
            "strategy": "route_to_human",
            "routing_utility": 0.40,
            "quality_utility": 0.90,
        },
        pareto_optimal=True,
    )
    print(f"    Conflict ID : {conflict_id}")
    print("    Type        : GOAL_CONFLICT  |  Severity: 0.75 (High)")

    # ------------------------------------------------------------------
    # Agent 3: Supervisor Agent  (resolves conflict)
    # ------------------------------------------------------------------
    print("\n[4] Supervisor Agent — resolving conflict")

    supervisor_decision_id: UUID
    with tracer.trace_decision(
        agent_id="supervisor_agent",
        session_id=session_id,
        decision_type=DecisionType.COORDINATION,
        parent_decision_id=routing_decision_id,
        input_data={
            "conflict_id": str(conflict_id),
            "agents": ["routing_agent", "quality_agent"],
        },
        tags=["conflict_resolution", "customer_support"],
    ) as ctx:
        supervisor_decision_id = ctx.decision_id
        tracer.record_decision(
            output={
                "final_route": "human",
                "override_agent": "routing_agent",
                "reason": "premium_customer_policy",
            },
            confidence=0.95,
            reasoning=[
                "Policy: premium customers are always routed to human agents",
                "Customer satisfaction outweighs speed for high-value accounts",
                "Quality agent's assessment is correct",
            ],
            constraints_checked=["premium_customer_policy"],
            data_sources=["conflict_analysis", "customer_database"],
        )

    print(f"    Decision ID : {supervisor_decision_id}")
    print("    Final route : HUMAN  |  Override: routing_agent")
    print("    Policy      : premium_customer_policy")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    decisions = tracer.query_decisions(session_id=session_id)

    print("\n[5] Session summary")
    print("-" * 60)
    print(f"    Session ID       : {session_id}")
    print(f"    Total decisions  : {len(decisions)}")
    print("    Agents involved  : 3")
    print("    Conflicts logged : 1")
    print("    Final resolution : Route to human agent (quality override)")

    print("\nDecision tree:")
    print(f"  ├─ {routing_decision_id}  routing_agent  → BOT")
    print(f"  ├─ {quality_decision_id}  quality_agent  → HUMAN")
    print(f"  └─ {supervisor_decision_id}  supervisor_agent → RESOLVED: HUMAN")

    tracer.close()
    print("\nExample complete. Data saved to: multi_agent_example.db")


if __name__ == "__main__":
    main()

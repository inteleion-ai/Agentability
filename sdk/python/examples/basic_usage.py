"""Basic usage example for Agentability.

Demonstrates decision provenance, memory tracking, and LLM call recording
using the offline SQLite mode — no infrastructure required.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from agentability import Tracer
from agentability.models import DecisionType, MemoryOperation, MemoryType


def main() -> None:
    """Run the basic usage walkthrough."""
    tracer = Tracer(offline_mode=True, database_path="example.db")

    print("Agentability — Basic Usage Example")
    print("=" * 50)

    # ------------------------------------------------------------------
    # 1. Decision with full provenance
    # ------------------------------------------------------------------
    print("\n[1] Recording a classification decision")

    with tracer.trace_decision(
        agent_id="risk_classifier",
        decision_type=DecisionType.CLASSIFICATION,
        input_data={"loan_amount": 50_000, "credit_score": 720, "income": 85_000},
        tags=["loan_processing", "risk_assessment"],
    ) as ctx:
        print(f"    Decision ID: {ctx.decision_id}")

        credit_score = 720
        loan_amount = 50_000
        income = 85_000

        dti_ratio = loan_amount / income
        approved = credit_score >= 700 and dti_ratio < 0.43
        confidence = 0.85 if approved else 0.72

        tracer.record_decision(
            output={"approved": approved, "amount": loan_amount if approved else 0},
            confidence=confidence,
            reasoning=[
                f"Credit score {credit_score} {'meets' if credit_score >= 700 else 'below'} minimum 700",
                f"DTI ratio {dti_ratio:.2f} {'acceptable (<0.43)' if dti_ratio < 0.43 else 'exceeds limit 0.43'}",
            ],
            uncertainties=[
                "Employment stability not verified",
                "No rental payment history available",
            ],
            assumptions=[
                "Income figures are current and accurate",
                "No undisclosed debts exist",
            ],
            constraints_checked=["credit_score >= 700", "dti_ratio < 0.43"],
            data_sources=["credit_bureau", "income_verification"],
        )

    print(f"    Outcome: {'APPROVED' if approved else 'DENIED'}  |  Confidence: {confidence:.0%}")

    # ------------------------------------------------------------------
    # 2. Memory operation
    # ------------------------------------------------------------------
    print("\n[2] Recording a vector memory retrieval")

    operation_id = tracer.record_memory_operation(
        agent_id="risk_classifier",
        memory_type=MemoryType.VECTOR,
        operation=MemoryOperation.RETRIEVE,
        latency_ms=42.5,
        items_processed=10,
        vector_dimension=1536,
        similarity_threshold=0.75,
        top_k=10,
        avg_similarity=0.82,
        min_similarity=0.76,
        max_similarity=0.91,
        retrieval_precision=0.85,
        retrieval_recall=0.78,
    )
    print(f"    Operation ID: {operation_id}")
    print("    Retrieval precision: 85%  |  Average similarity: 0.82")

    # ------------------------------------------------------------------
    # 3. LLM call
    # ------------------------------------------------------------------
    print("\n[3] Recording an LLM call")

    llm_call_id = tracer.record_llm_call(
        agent_id="risk_classifier",
        provider="anthropic",
        model="claude-sonnet-4",
        prompt_tokens=1_500,
        completion_tokens=800,
        latency_ms=1_250.0,
        cost_usd=0.0083,
        finish_reason="end_turn",
        temperature=0.7,
        max_tokens=2_000,
    )
    print(f"    Call ID: {llm_call_id}")
    print("    Total tokens: 2,300  |  Cost: $0.0083")

    # ------------------------------------------------------------------
    # 4. Query
    # ------------------------------------------------------------------
    print("\n[4] Querying stored decisions")

    decisions = tracer.query_decisions(agent_id="risk_classifier", limit=10)
    print(f"    Found {len(decisions)} decision(s)")
    for d in decisions:
        conf = f"{d.confidence:.0%}" if d.confidence is not None else "n/a"
        print(
            f"    • {d.decision_id}  type={d.decision_type.value}"
            f"  confidence={conf}  reasoning_steps={len(d.reasoning)}"
        )

    tracer.close()
    print("\nExample complete. Data saved to: example.db")


if __name__ == "__main__":
    main()

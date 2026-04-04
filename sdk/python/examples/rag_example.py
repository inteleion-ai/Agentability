#!/usr/bin/env python3
"""
RAG Pipeline Example — Agentability vs Langfuse
================================================

This example simulates a production RAG (Retrieval Augmented Generation)
agent that answers questions about financial documents.

What Langfuse shows you:  the LLM prompt and response
What Agentability shows:  WHY the answer quality was low — stale embeddings,
                          low retrieval precision, context window saturation

Run:
    cd Agentability
    python3.11 sdk/python/examples/rag_example.py

Then open the dashboard at http://localhost:3000 → Agents → rag_agent
to see the full memory intelligence and confidence drift visualisation.
"""

import random
import time
from datetime import datetime, timedelta

from agentability import Tracer, DecisionType
from agentability.models import MemoryOperation, MemoryType

# ── Simulated vector database ──────────────────────────────────────────────

DOCUMENT_CHUNKS = [
    {"id": "doc_001", "text": "Q3 2024 revenue was $4.2M, up 18% YoY.", "age_days": 180},
    {"id": "doc_002", "text": "Q4 2024 revenue was $5.1M, up 21% YoY.", "age_days": 90},
    {"id": "doc_003", "text": "Q1 2025 revenue was $5.8M, up 14% YoY.", "age_days": 30},
    {"id": "doc_004", "text": "Customer churn rate dropped to 2.1% in Q1 2025.", "age_days": 30},
    {"id": "doc_005", "text": "Enterprise ARR reached $12M as of January 2025.", "age_days": 60},
    {"id": "doc_006", "text": "Headcount grew from 45 to 67 employees in 2024.", "age_days": 120},
]


def simulate_vector_search(query, top_k=3, inject_staleness=False):
    """Simulate a vector DB search with realistic similarity scores."""
    results = []
    for chunk in DOCUMENT_CHUNKS[:top_k + 1]:
        similarity = random.uniform(0.65, 0.92)
        # Stale docs get lower similarity when staleness mode is on
        if inject_staleness and chunk["age_days"] > 60:
            similarity -= 0.20
        results.append({
            "chunk": chunk,
            "similarity": round(similarity, 3),
        })
    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results[:top_k]


def simulate_llm_call(context_chunks, query):
    """Simulate an LLM generating an answer from retrieved context."""
    time.sleep(0.05)  # simulate network latency
    avg_similarity = sum(r["similarity"] for r in context_chunks) / len(context_chunks)
    # Lower confidence answer if context is old or low-similarity
    confidence = min(0.95, avg_similarity + random.gauss(0, 0.05))
    answer = "Based on retrieved documents: revenue trend is positive."
    prompt_tokens = random.randint(800, 2000)
    completion_tokens = random.randint(100, 300)
    return answer, confidence, prompt_tokens, completion_tokens


# ── RAG Agent with full Agentability instrumentation ──────────────────────

def run_rag_query(tracer, query, inject_staleness=False):
    """
    Run one RAG query with complete Agentability tracing.

    This captures everything Langfuse misses:
    - Vector retrieval precision and recall
    - Document staleness (oldest_item_age_hours)
    - Context window utilisation
    - Confidence linked to retrieval quality
    - Causal chain: stale docs -> low similarity -> low confidence -> escalation
    """
    start = datetime.utcnow()

    with tracer.trace_decision(
        agent_id="rag_agent",
        decision_type=DecisionType.RETRIEVAL,
        input_data={"query": query, "top_k": 3},
        tags=["rag", "financial_qa"],
        metadata={"inject_staleness": inject_staleness},
    ) as ctx:

        # ── Step 1: Vector retrieval ───────────────────────────────────────
        retrieval_start = time.time()
        results = simulate_vector_search(query, top_k=3, inject_staleness=inject_staleness)
        retrieval_latency = (time.time() - retrieval_start) * 1000

        similarities = [r["similarity"] for r in results]
        avg_sim = sum(similarities) / len(similarities)
        min_sim = min(similarities)

        # What Langfuse never captures — memory subsystem intelligence
        oldest_doc_age = max(r["chunk"]["age_days"] for r in results)

        op_id = tracer.record_memory_operation(
            agent_id="rag_agent",
            memory_type=MemoryType.VECTOR,
            operation=MemoryOperation.RETRIEVE,
            latency_ms=retrieval_latency,
            items_processed=len(results),
            avg_similarity=avg_sim,
            min_similarity=min_sim,
            max_similarity=max(similarities),
            retrieval_precision=avg_sim,           # proxy for precision
            retrieval_recall=len(results) / 6.0,   # retrieved / total corpus
            top_k=3,
            vector_dimension=1536,
            # CRITICAL: staleness signal — no other tool tracks this
            oldest_item_age_hours=oldest_doc_age * 24.0,
            average_item_age_hours=(sum(r["chunk"]["age_days"] for r in results) / len(results)) * 24.0,
        )

        ctx.add_reasoning_step("Vector search: retrieved {} chunks, avg_similarity={:.3f}".format(
            len(results), avg_sim))

        if oldest_doc_age > 90:
            ctx.add_reasoning_step(
                "WARNING: Oldest retrieved document is {} days old — may be stale".format(oldest_doc_age)
            )

        # ── Step 2: Context assembly ───────────────────────────────────────
        context_tokens = sum(len(r["chunk"]["text"].split()) * 2 for r in results)
        context_limit = 4096

        # Episodic memory — conversation history loaded into context
        tracer.record_memory_operation(
            agent_id="rag_agent",
            memory_type=MemoryType.EPISODIC,
            operation=MemoryOperation.RETRIEVE,
            latency_ms=5.0,
            items_processed=3,  # last 3 conversation turns
            context_tokens_used=context_tokens,
            context_tokens_limit=context_limit,
            temporal_coherence=0.91,
        )

        utilisation = context_tokens / context_limit
        if utilisation > 0.85:
            ctx.add_reasoning_step(
                "Context window at {:.0f}% capacity — some history truncated".format(utilisation * 100)
            )

        # ── Step 3: LLM generation ─────────────────────────────────────────
        answer, confidence, prompt_tokens, completion_tokens = simulate_llm_call(results, query)

        llm_call_id = tracer.record_llm_call(
            agent_id="rag_agent",
            provider="anthropic",
            model="claude-sonnet-4",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=random.uniform(600, 1400),
            cost_usd=(prompt_tokens / 1e6) * 3.0 + (completion_tokens / 1e6) * 15.0,
            finish_reason="end_turn",
        )

        ctx.set_confidence(confidence)
        ctx.add_reasoning_step("LLM generation complete — answer confidence: {:.2f}".format(confidence))

        # ── Step 4: Quality gate — escalate if low confidence ──────────────
        if confidence < 0.65:
            decision_output = {"answer": answer, "action": "escalate_to_human", "confidence": confidence}
            tracer.record_decision(
                output=decision_output,
                confidence=confidence,
                reasoning=ctx._state.get("reasoning", []),
                uncertainties=[
                    "Retrieval similarity below threshold ({:.2f})".format(avg_sim),
                    "Oldest source document is {} days old".format(oldest_doc_age),
                ] if inject_staleness else ["Low model confidence on query"],
                assumptions=["Retrieved documents are relevant to query"],
                constraints_checked=["min_similarity >= 0.70", "max_doc_age_days <= 90"],
                constraints_violated=(
                    ["min_similarity >= 0.70", "max_doc_age_days <= 90"]
                    if inject_staleness else []
                ),
                data_sources=["vector_store", "financial_documents"],
            )
            return "ESCALATED", confidence
        else:
            tracer.record_decision(
                output={"answer": answer, "action": "return_answer"},
                confidence=confidence,
                reasoning=ctx._state.get("reasoning", []),
                data_sources=["vector_store", "financial_documents"],
            )
            return answer, confidence


# ── Main demo ──────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 65)
    print("  Agentability RAG Example — Memory Intelligence Demo")
    print("=" * 65)

    tracer = Tracer(offline_mode=True, database_path="agentability.db")

    queries = [
        "What was the revenue in Q3 2024?",
        "What is the current ARR?",
        "How has customer churn changed recently?",
        "What is the headcount growth trend?",
        "What were the Q1 2025 financial results?",
    ]

    print("\n[Phase 1] Normal RAG — fresh embeddings, high similarity")
    print("-" * 55)
    for i, query in enumerate(queries[:3]):
        answer, conf = run_rag_query(tracer, query, inject_staleness=False)
        print("  Q: {}".format(query))
        print("  A: {} (confidence: {:.2f})".format(
            answer[:50] if len(str(answer)) > 50 else answer, conf))
        print()

    print("\n[Phase 2] Degraded RAG — stale embeddings injected")
    print("  (This is what Agentability catches, Langfuse misses)")
    print("-" * 55)
    for i, query in enumerate(queries[2:]):
        answer, conf = run_rag_query(tracer, query, inject_staleness=True)
        status = "ESCALATED" if answer == "ESCALATED" else "answered"
        print("  Q: {}".format(query))
        print("  A: {} — {} (confidence: {:.2f})".format(
            status, "stale docs detected" if conf < 0.65 else "ok", conf))
        print()

    tracer.close()

    print("\n" + "=" * 65)
    print("  Done. Open the dashboard to see:")
    print()
    print("  Agents → rag_agent:")
    print("   - Confidence drop in Phase 2 (drift detection)")
    print("   - oldest_item_age_hours spike (staleness signal)")
    print("   - retrieval_precision < 0.70 triggering escalations")
    print("   - Context window utilisation timeline")
    print()
    print("  Decisions → filter by agent=rag_agent:")
    print("   - constraints_violated for stale doc decisions")
    print("   - Full reasoning chain per decision")
    print("   - LLM cost per query")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()

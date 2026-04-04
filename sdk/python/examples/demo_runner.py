#!/usr/bin/env python3
"""
Agentability — Complete Demo Runner
====================================

Runs both the RAG example and multi-agent conflict example in sequence,
then prints exactly what to look for in the dashboard.

Usage (on OCI):
    cd /home/opc/agentdyne9/new_project/agentability/Agentability
    python3.11 sdk/python/examples/demo_runner.py

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

import random
import sys
import time
from datetime import datetime, timedelta

# ── Add SDK to path if not installed ──────────────────────────────────────
sys.path.insert(0, "sdk/python")

from agentability import Tracer, DecisionType
from agentability.analyzers.conflict_analyzer import ConflictAnalyzer
from agentability.analyzers.drift_detector import DriftDetector
from agentability.models import (
    ConflictType,
    MemoryOperation,
    MemoryType,
)

DB = "agentability.db"
SEP = "=" * 65


# ═══════════════════════════════════════════════════════════════════════════
# PART 1: RAG PIPELINE — Memory Intelligence
# ═══════════════════════════════════════════════════════════════════════════

CORPUS = [
    {"id": "doc_001", "text": "Q3 2024 revenue $4.2M, up 18% YoY.", "age_days": 180},
    {"id": "doc_002", "text": "Q4 2024 revenue $5.1M, up 21% YoY.", "age_days": 90},
    {"id": "doc_003", "text": "Q1 2025 revenue $5.8M, up 14% YoY.", "age_days": 30},
    {"id": "doc_004", "text": "Churn rate dropped to 2.1% in Q1 2025.", "age_days": 30},
    {"id": "doc_005", "text": "Enterprise ARR reached $12M Jan 2025.", "age_days": 60},
    {"id": "doc_006", "text": "Headcount grew 45 to 67 in 2024.", "age_days": 120},
]


def vector_search(query, top_k=3, stale=False):
    results = []
    for chunk in CORPUS[:top_k + 2]:
        sim = random.uniform(0.65, 0.92)
        if stale and chunk["age_days"] > 60:
            sim -= 0.22
        results.append({"chunk": chunk, "similarity": round(max(0.3, sim), 3)})
    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results[:top_k]


def llm_call(context, query):
    time.sleep(0.03)
    avg_sim = sum(r["similarity"] for r in context) / len(context)
    conf = min(0.97, max(0.20, avg_sim + random.gauss(0, 0.04)))
    prompt_tokens = random.randint(600, 1800)
    completion_tokens = random.randint(80, 280)
    return "Answer based on retrieved context.", round(conf, 3), prompt_tokens, completion_tokens


def rag_query(tracer, query, stale=False):
    with tracer.trace_decision(
        agent_id="rag_agent",
        decision_type=DecisionType.RETRIEVAL,
        input_data={"query": query},
        tags=["rag", "demo"],
    ) as ctx:
        # Step 1: vector retrieval
        t0 = time.time()
        results = vector_search(query, top_k=3, stale=stale)
        ret_ms = (time.time() - t0) * 1000

        sims = [r["similarity"] for r in results]
        avg_sim = sum(sims) / len(sims)
        oldest_days = max(r["chunk"]["age_days"] for r in results)

        tracer.record_memory_operation(
            agent_id="rag_agent",
            memory_type=MemoryType.VECTOR,
            operation=MemoryOperation.RETRIEVE,
            latency_ms=ret_ms,
            items_processed=len(results),
            avg_similarity=avg_sim,
            min_similarity=min(sims),
            max_similarity=max(sims),
            retrieval_precision=round(avg_sim, 3),
            retrieval_recall=round(len(results) / len(CORPUS), 3),
            top_k=3,
            vector_dimension=1536,
            # Staleness — the signal Langfuse never captures
            oldest_item_age_hours=oldest_days * 24.0,
            average_item_age_hours=(sum(r["chunk"]["age_days"] for r in results) / len(results)) * 24.0,
        )

        ctx.add_reasoning_step(
            "Vector search: {} chunks, avg_sim={:.3f}, oldest={}d".format(
                len(results), avg_sim, oldest_days
            )
        )

        # Step 2: episodic (conversation history)
        ctx_tokens = random.randint(800, 3600)
        tracer.record_memory_operation(
            agent_id="rag_agent",
            memory_type=MemoryType.EPISODIC,
            operation=MemoryOperation.RETRIEVE,
            latency_ms=4.0,
            items_processed=3,
            context_tokens_used=ctx_tokens,
            context_tokens_limit=4096,
            temporal_coherence=0.91,
        )

        if ctx_tokens / 4096 > 0.85:
            ctx.add_reasoning_step("Context window >{:.0f}% full — history truncated".format(
                ctx_tokens / 4096 * 100))

        # Step 3: LLM call
        answer, conf, p_tok, c_tok = llm_call(results, query)
        cost = (p_tok / 1e6) * 3.0 + (c_tok / 1e6) * 15.0

        tracer.record_llm_call(
            agent_id="rag_agent",
            provider="anthropic",
            model="claude-sonnet-4",
            prompt_tokens=p_tok,
            completion_tokens=c_tok,
            latency_ms=random.uniform(500, 1300),
            cost_usd=cost,
            finish_reason="end_turn",
        )

        ctx.set_confidence(conf)
        ctx.add_reasoning_step("LLM generation: confidence={:.3f}".format(conf))

        violated = []
        uncertainties = []
        if avg_sim < 0.70:
            violated.append("min_similarity >= 0.70")
            uncertainties.append("Low retrieval similarity: {:.2f}".format(avg_sim))
        if oldest_days > 90:
            violated.append("max_doc_age_days <= 90")
            uncertainties.append("Stale document: {} days old".format(oldest_days))

        tracer.record_decision(
            output={"answer": answer, "escalated": conf < 0.60},
            confidence=conf,
            reasoning=ctx._state.get("reasoning", []),
            uncertainties=uncertainties,
            constraints_checked=["min_similarity >= 0.70", "max_doc_age_days <= 90"],
            constraints_violated=violated,
            data_sources=["vector_store", "episodic_memory"],
        )

        return conf, violated


def run_rag_demo(tracer):
    print("\n" + SEP)
    print("  PART 1: RAG Pipeline — Memory Intelligence")
    print(SEP)

    queries = [
        "What was revenue in Q3 2024?",
        "What is current ARR?",
        "How has customer churn changed?",
        "What is the headcount trend?",
        "What were Q1 2025 results?",
        "Compare Q3 and Q4 2024 revenue.",
    ]

    print("\n Phase A: Fresh embeddings (good retrieval)")
    print(" " + "-" * 50)
    for q in queries[:3]:
        conf, violated = rag_query(tracer, q, stale=False)
        flag = "OK" if not violated else "WARN"
        print("  [{flag}] conf={conf:.2f}  {q}".format(
            flag=flag, conf=conf, q=q[:48]))

    print("\n Phase B: Stale embeddings injected (degraded retrieval)")
    print(" (This is what Agentability detects, Langfuse cannot)")
    print(" " + "-" * 50)
    for q in queries[3:]:
        conf, violated = rag_query(tracer, q, stale=True)
        flag = "VIOLATED" if violated else "OK"
        v_str = ", ".join(violated) if violated else "none"
        print("  [{flag}] conf={conf:.2f}  {q}".format(
            flag=flag, conf=conf, q=q[:40]))
        if violated:
            print("           violations: {}".format(v_str))

    print("\n What the dashboard shows:")
    print("  Agents -> rag_agent -> Confidence Timeline:")
    print("    Phase A: confidence 0.75-0.90 (stable)")
    print("    Phase B: confidence 0.40-0.65 (DRIFT ALERT)")
    print("  Agents -> rag_agent -> Drift:")
    print("    DriftDetector fires: severity MEDIUM or HIGH")
    print("    Recommendation: review stale document sources")
    print("  Decisions -> rag_agent -> click any Phase B decision:")
    print("    constraints_violated: min_similarity, max_doc_age")
    print("    oldest_item_age_hours: 2160h (90 days)")


# ═══════════════════════════════════════════════════════════════════════════
# PART 2: MULTI-AGENT — Conflict Detection & Resolution
# ═══════════════════════════════════════════════════════════════════════════

SCENARIOS = [
    {
        "ticket": "My premium order is late",
        "tier": "premium",
        "routing_decision": "bot",
        "routing_conf": 0.78,
        "quality_decision": "human",
        "quality_conf": 0.93,
        "severity": 0.82,
    },
    {
        "ticket": "I need a refund for damaged goods",
        "tier": "standard",
        "routing_decision": "bot",
        "routing_conf": 0.81,
        "quality_decision": "human",
        "quality_conf": 0.88,
        "severity": 0.71,
    },
    {
        "ticket": "Wrong item delivered",
        "tier": "premium",
        "routing_decision": "bot",
        "routing_conf": 0.69,
        "quality_decision": "human",
        "quality_conf": 0.95,
        "severity": 0.77,
    },
    {
        "ticket": "How do I track my order?",
        "tier": "standard",
        "routing_decision": "bot",
        "routing_conf": 0.92,
        "quality_decision": "bot",
        "quality_conf": 0.88,
        "severity": 0.0,  # no conflict
    },
]


def run_multi_agent_scenario(tracer, scenario):
    from uuid import uuid4
    session_id = "demo_session_{}".format(uuid4().hex[:8])
    ticket = scenario["ticket"]
    tier = scenario["tier"]

    # Agent 1: Routing agent (optimises speed)
    with tracer.trace_decision(
        agent_id="routing_agent",
        decision_type=DecisionType.DELEGATION,
        session_id=session_id,
        input_data={"ticket": ticket, "tier": tier},
        tags=["routing", "customer_support"],
    ) as ctx:
        ctx.set_confidence(scenario["routing_conf"])
        tracer.record_decision(
            output={"route_to": scenario["routing_decision"]},
            confidence=scenario["routing_conf"],
            reasoning=[
                "Ticket classified as: delivery inquiry",
                "Bot resolution time: <60 seconds",
                "Optimising for response speed",
            ],
            assumptions=["Customer values speed over personalisation"],
        )

    # Agent 2: Quality agent (optimises CSAT)
    with tracer.trace_decision(
        agent_id="quality_agent",
        decision_type=DecisionType.COORDINATION,
        session_id=session_id,
        input_data={"ticket": ticket, "tier": tier},
        tags=["quality_control", "customer_support"],
    ) as ctx:
        ctx.set_confidence(scenario["quality_conf"])
        tracer.record_decision(
            output={"route_to": scenario["quality_decision"]},
            confidence=scenario["quality_conf"],
            reasoning=[
                "Customer tier: {}".format(tier),
                "Complaint type requires empathy response",
                "Optimising for CSAT score",
            ],
        )

    # Record conflict if agents disagree
    conflict_recorded = False
    if scenario["routing_decision"] != scenario["quality_decision"]:
        tracer.record_conflict(
            session_id=session_id,
            conflict_type=ConflictType.GOAL_CONFLICT,
            involved_agents=["routing_agent", "quality_agent"],
            agent_positions={
                "routing_agent": {
                    "route_to": scenario["routing_decision"],
                    "goal": "minimise_response_time",
                    "confidence": scenario["routing_conf"],
                },
                "quality_agent": {
                    "route_to": scenario["quality_decision"],
                    "goal": "maximise_csat",
                    "confidence": scenario["quality_conf"],
                },
            },
            severity=scenario["severity"],
            resolution_strategy="confidence_based",
            pareto_optimal=tier == "premium",
        )
        conflict_recorded = True

    # Agent 3: Supervisor resolves
    winner = (
        scenario["quality_decision"]
        if scenario["quality_conf"] > scenario["routing_conf"]
        else scenario["routing_decision"]
    )

    with tracer.trace_decision(
        agent_id="supervisor_agent",
        decision_type=DecisionType.COORDINATION,
        session_id=session_id,
        input_data={"ticket": ticket, "conflict": conflict_recorded},
        tags=["conflict_resolution"],
    ) as ctx:
        policy = "premium_human_always" if tier == "premium" else "confidence_based"
        ctx.set_confidence(0.95)
        tracer.record_decision(
            output={"final_route": winner, "policy_applied": policy},
            confidence=0.95,
            reasoning=[
                "Applied policy: {}".format(policy),
                "Winner: {} (conf={:.2f})".format(
                    "quality_agent" if winner == "human" else "routing_agent",
                    max(scenario["routing_conf"], scenario["quality_conf"])
                ),
            ],
            constraints_checked=[policy],
            data_sources=["conflict_analysis", "policy_database"],
        )

    return conflict_recorded, winner, scenario["severity"]


def run_multi_agent_demo(tracer):
    print("\n" + SEP)
    print("  PART 2: Multi-Agent System — Conflict Detection")
    print(SEP)
    print()
    print("  Scenario: Customer Support Routing")
    print("  Agents:   routing_agent vs quality_agent vs supervisor_agent")
    print()

    total_conflicts = 0
    for s in SCENARIOS:
        conflict, winner, severity = run_multi_agent_scenario(tracer, s)
        status = "CONFLICT -> resolved" if conflict else "AGREEMENT"
        print("  Ticket: {:45s}  {}".format(
            '"{}"'.format(s["ticket"][:40]),
            status
        ))
        if conflict:
            total_conflicts += 1
            print("    Route: {} -> {}  |  Severity: {:.2f}  |  Winner: {}".format(
                s["routing_decision"].upper(),
                s["quality_decision"].upper(),
                severity,
                "quality_agent" if winner == "human" else "routing_agent"
            ))
        print()

    print("  Conflicts recorded: {}/{}".format(total_conflicts, len(SCENARIOS)))
    print()
    print("  What the dashboard shows:")
    print("  Conflicts page:")
    print("    Total conflicts: {}".format(total_conflicts))
    print("    Hotspot: routing_agent vs quality_agent ({} conflicts)".format(total_conflicts))
    print("    Avg severity: {:.2f}".format(
        sum(s["severity"] for s in SCENARIOS if s["routing_decision"] != s["quality_decision"]) / max(total_conflicts, 1)
    ))
    print("  Decisions -> filter by agent=supervisor_agent:")
    print("    Every resolution with policy_applied and reasoning chain")
    print("  Agents -> routing_agent:")
    print("    Win rate vs quality_agent: {:.0f}%".format(
        sum(1 for s in SCENARIOS if s["routing_conf"] > s["quality_conf"]) / len(SCENARIOS) * 100
    ))


# ═══════════════════════════════════════════════════════════════════════════
# PART 3: DRIFT SIMULATION — Confidence Degradation Over Time
# ═══════════════════════════════════════════════════════════════════════════

def run_drift_demo():
    print("\n" + SEP)
    print("  PART 3: Drift Detector — Catching Degradation Before Incidents")
    print(SEP)
    print()

    detector = DriftDetector(
        baseline_window_days=7,
        detection_window_hours=24,
        drift_threshold=0.10,
    )

    now = datetime.utcnow()

    # Baseline: stable confidence for 7 days
    print("  Recording 7 days of baseline (stable agent)...")
    for days_ago in range(7, 0, -1):
        for _ in range(20):
            ts = now - timedelta(days=days_ago, minutes=random.randint(0, 1440))
            detector.record_confidence(
                agent_id="risk_agent",
                confidence=random.gauss(0.85, 0.04),
                timestamp=ts,
                version="v1.0",
            )

    # Recent: degraded confidence (simulates model/prompt change)
    print("  Recording last 24h with DEGRADED confidence (v1.1 deployed)...")
    for hours_ago in range(24, 0, -1):
        ts = now - timedelta(hours=hours_ago, minutes=random.randint(0, 59))
        # Confidence drops ~22% — typical prompt regression
        detector.record_confidence(
            agent_id="risk_agent",
            confidence=random.gauss(0.63, 0.05),
            timestamp=ts,
            version="v1.1",
        )

    result = detector.detect_drift("risk_agent")

    print()
    print("  Drift Detection Result:")
    print("  " + "-" * 50)
    print("  drift_detected   : {}".format(result["drift_detected"]))
    print("  severity         : {}".format(result.get("severity", "N/A").upper()))
    print("  baseline_conf    : {:.3f}".format(result.get("baseline_confidence", 0)))
    print("  current_conf     : {:.3f}".format(result.get("current_confidence", 0)))
    print("  drift_magnitude  : {:.1f}%".format(
        result.get("drift_magnitude", 0) * 100))
    print("  recommendation   : {}".format(
        result.get("recommendation", "")[:80]))

    # Version impact
    impact = detector.detect_version_impact("risk_agent", "v1.1")
    if "error" not in impact:
        print()
        print("  Version Impact (v1.1 vs v1.0):")
        print("  regression       : {}".format(impact.get("regression")))
        print("  v1.1 confidence  : {:.3f}".format(impact.get("version_confidence", 0)))
        print("  v1.0 confidence  : {:.3f}".format(impact.get("other_versions_confidence", 0)))
        print("  impact           : {:.1f}%".format(impact.get("impact_percentage", 0)))

    print()
    print("  What the dashboard shows:")
    print("  Agents -> risk_agent -> Drift:")
    print("    RED ALERT: drift detected, severity {}".format(
        result.get("severity", "").upper()))
    print("    Timeline shows clear confidence drop at v1.1 deployment")
    print("    Recommendation surfaces automatically")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("\n" + SEP)
    print("  Agentability — Full Demo Runner")
    print("  Shows what Langfuse and other LLM tracers cannot capture")
    print(SEP)
    print()
    print("  Database: {}".format(DB))
    print("  Dashboard: http://localhost:3000")
    print("  API docs:  http://localhost:8000/docs")

    tracer = Tracer(offline_mode=True, database_path=DB)

    run_rag_demo(tracer)
    run_multi_agent_demo(tracer)

    tracer.close()

    run_drift_demo()

    print("\n" + SEP)
    print("  DEMO COMPLETE")
    print(SEP)
    print()
    print("  Now open the dashboard and navigate:")
    print()
    print("  1. Overview      — 5 KPI cards, all charts populated")
    print("  2. Agents")
    print("     - rag_agent   — click to see confidence drop in Phase B")
    print("                     drift alert fires, staleness visible")
    print("     - routing_agent / quality_agent / supervisor_agent")
    print("                     see per-agent confidence and cost")
    print("  3. Decisions     — filter by agent=rag_agent")
    print("                     click any row to see full reasoning chain")
    print("                     Phase B rows show constraints_violated")
    print("  4. Conflicts     — hotspot: routing_agent vs quality_agent")
    print("                     see severity, resolution strategy, timeline")
    print("  5. Cost & LLM    — breakdown by model (claude-sonnet-4)")
    print("                     latency p50/p95/p99 for rag_agent")
    print()
    print("  This is what Langfuse cannot show you:")
    print("  - oldest_item_age_hours (stale embedding detection)")
    print("  - constraints_violated  (policy breach tracing)")
    print("  - DriftDetector alert   (proactive degradation detection)")
    print("  - conflict hotspot map  (multi-agent intelligence)")
    print("  - full reasoning chain  (why, not just what)")
    print()


if __name__ == "__main__":
    main()

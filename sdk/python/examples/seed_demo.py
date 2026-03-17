#!/usr/bin/env python3
"""Seed agentability.db with realistic demo data for dashboard testing.

Usage:
    python seed_demo.py                     # writes to ./agentability.db
    AGENTABILITY_DB=custom.db python seed_demo.py

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

import os
import random
from datetime import datetime, timedelta

from agentability.models import (
    AgentConflict,
    ConflictType,
    Decision,
    DecisionType,
    LLMMetrics,
    MemoryMetrics,
    MemoryOperation,
    MemoryType,
)
from agentability.storage.sqlite_store import SQLiteStore

DB_PATH = os.getenv("AGENTABILITY_DB", "agentability.db")

AGENTS = ["risk_agent", "sales_agent", "compliance_agent", "routing_agent", "rag_agent"]
MODELS = [
    ("anthropic", "claude-sonnet-4", 3.0, 15.0),
    ("anthropic", "claude-haiku-4",  0.25, 1.25),
    ("openai",    "gpt-4",           30.0, 60.0),
    ("openai",    "gpt-3.5-turbo",   0.5,  1.5),
]
DECISION_TYPES = [
    DecisionType.CLASSIFICATION,
    DecisionType.GENERATION,
    DecisionType.RETRIEVAL,
    DecisionType.PLANNING,
    DecisionType.ROUTING,
]
CONFLICT_PAIRS = [
    ("risk_agent", "sales_agent"),
    ("compliance_agent", "routing_agent"),
]


def rand_confidence(agent_id: str, ts: datetime) -> float:
    """Simulate a downward drift for risk_agent in the last 24 h."""
    base = {"risk_agent": 0.82, "sales_agent": 0.88, "compliance_agent": 0.91,
            "routing_agent": 0.79, "rag_agent": 0.85}.get(agent_id, 0.80)
    age_hours = (datetime.utcnow() - ts).total_seconds() / 3600
    if agent_id == "risk_agent" and age_hours < 24:
        base -= 0.22  # drift!
    return max(0.10, min(0.99, base + random.gauss(0, 0.06)))


def seed(store: SQLiteStore) -> None:
    now = datetime.utcnow()
    decisions_written = 0
    llm_written = 0
    mem_written = 0
    conflict_written = 0

    # ── Decisions + LLM calls ──────────────────────────────────────────────
    for agent_id in AGENTS:
        for hour_back in range(0, 168, 2):          # 7 days, every 2 hours
            for _ in range(random.randint(3, 12)):  # 3–12 decisions per slot
                ts = now - timedelta(hours=hour_back, minutes=random.randint(0, 119))
                dt = random.choice(DECISION_TYPES)
                conf = rand_confidence(agent_id, ts)
                latency = abs(random.gauss(320, 180))

                prov, comp, tok = random.randint(100, 4000), random.randint(50, 800), 0
                provider, model, inp_price, out_price = random.choice(MODELS)
                tok = prov + comp
                cost = (prov / 1e6) * inp_price + (comp / 1e6) * out_price

                violated = ["income_freshness_days <= 30"] if conf < 0.5 and random.random() < 0.4 else []

                d = Decision(
                    agent_id=agent_id,
                    session_id=f"session_{agent_id}_{hour_back // 24}",
                    timestamp=ts,
                    latency_ms=latency,
                    decision_type=dt,
                    input_data={"query": f"sample input {random.randint(1, 999)}"},
                    output_data={"result": random.choice(["approve", "deny", "escalate", "route"])},
                    confidence=conf,
                    reasoning=[
                        f"Step {i + 1}: evaluated {random.choice(['credit', 'income', 'policy', 'context'])}"
                        for i in range(random.randint(1, 4))
                    ],
                    uncertainties=(["Employment not verified"] if conf < 0.6 else []),
                    constraints_violated=violated,
                    data_sources=random.sample(["credit_bureau", "income_api", "vector_store", "policy_db"], k=random.randint(1, 3)),
                    llm_calls=1,
                    total_tokens=tok,
                    total_cost_usd=cost,
                    tags=[agent_id, model],
                )
                store.save_decision(d)
                decisions_written += 1

                # LLM call linked to this decision
                llm = LLMMetrics(
                    agent_id=agent_id,
                    decision_id=d.decision_id,
                    timestamp=ts,
                    latency_ms=latency,
                    provider=provider,
                    model=model,
                    prompt_tokens=prov,
                    completion_tokens=comp,
                    total_tokens=tok,
                    cost_usd=cost,
                    finish_reason="end_turn",
                )
                store.save_llm_metrics(llm)
                llm_written += 1

    # ── Memory operations ──────────────────────────────────────────────────
    for _ in range(400):
        agent_id = random.choice(AGENTS)
        ts = now - timedelta(hours=random.uniform(0, 168))
        m = MemoryMetrics(
            agent_id=agent_id,
            memory_type=random.choice([MemoryType.VECTOR, MemoryType.EPISODIC, MemoryType.SEMANTIC]),
            operation=MemoryOperation.RETRIEVE,
            timestamp=ts,
            latency_ms=abs(random.gauss(40, 20)),
            items_processed=random.randint(1, 20),
            avg_similarity=random.uniform(0.65, 0.95),
            retrieval_precision=random.uniform(0.70, 0.95),
            retrieval_recall=random.uniform(0.60, 0.90),
        )
        store.save_memory_metrics(m)
        mem_written += 1

    # ── Conflicts ──────────────────────────────────────────────────────────
    for _ in range(80):
        a1, a2 = random.choice(CONFLICT_PAIRS)
        ts = now - timedelta(hours=random.uniform(0, 168))
        c = AgentConflict(
            session_id=f"session_conflict_{random.randint(1, 20)}",
            timestamp=ts,
            conflict_type=random.choice(list(ConflictType)),
            involved_agents=[a1, a2],
            agent_positions={
                a1: {"decision": "deny",    "confidence": round(random.uniform(0.6, 0.95), 2)},
                a2: {"decision": "approve", "confidence": round(random.uniform(0.6, 0.95), 2)},
            },
            severity=random.uniform(0.2, 0.95),
            resolved=random.random() > 0.4,
            resolution_strategy=random.choice(["priority_hierarchy", "confidence_based", "consensus"]),
        )
        store.save_conflict(c)
        conflict_written += 1

    print(f"✅ Seed complete:")
    print(f"   {decisions_written:>6} decisions")
    print(f"   {llm_written:>6} LLM calls")
    print(f"   {mem_written:>6} memory operations")
    print(f"   {conflict_written:>6} conflicts")
    print(f"   DB: {DB_PATH}")


if __name__ == "__main__":
    store = SQLiteStore(database_path=DB_PATH)
    seed(store)
    store.close()

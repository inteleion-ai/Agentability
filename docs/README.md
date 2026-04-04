# Agentability Documentation

**Agent Operating Intelligence Layer — v0.2.x**

---

## Contents

- [Quick Start](#quick-start)
- [SDK Reference](#sdk-reference)
- [Platform API](#platform-api)
- [Dashboard](#dashboard)
- [AFMX Integration](#afmx-integration)
- [Running Examples](#running-examples)
- [Architecture](#architecture)

---

## Quick Start

```bash
pip install agentability

python3 - <<'EOF'
from agentability import Tracer, DecisionType

tracer = Tracer(offline_mode=True)   # writes to agentability.db

with tracer.trace_decision(
    agent_id="risk_agent",
    decision_type=DecisionType.CLASSIFICATION,
    input_data={"loan_amount": 50_000, "credit_score": 680},
) as ctx:
    ctx.set_confidence(0.74)
    ctx.add_reasoning_step("Credit score meets minimum threshold")
    ctx.add_reasoning_step("Income data is 90 days old — freshness constraint failed")
    tracer.record_decision(
        output={"approved": False},
        uncertainties=["Employment stability not verified"],
        constraints_violated=["income_freshness_days <= 30"],
    )

decisions = tracer.query_decisions(agent_id="risk_agent")
print(decisions[0].confidence)   # 0.74
tracer.close()
EOF
```

---

## SDK Reference

### Tracer

```python
from agentability import Tracer

# Offline mode — writes to local SQLite, zero infrastructure
tracer = Tracer(offline_mode=True, database_path="agentability.db")

# Online mode — writes to SQLite AND pushes to the platform API
tracer = Tracer(
    offline_mode=False,
    api_endpoint="http://localhost:8000",
    api_key="your-key",
)
```

### trace_decision()

Context manager wrapping a single agent decision. Automatically records `latency_ms`.

```python
with tracer.trace_decision(
    agent_id="analyst_agent",           # required — identifies the agent
    decision_type=DecisionType.PLANNING,# required — see DecisionType enum
    session_id="execution-uuid",        # optional — links to AFMX execution_id
    input_data={"topic": "AI trends"},  # optional — input snapshot
    tags=["production", "research"],    # optional
) as ctx:
    ctx.set_confidence(0.87)            # clamps to [0, 1]
    ctx.add_reasoning_step("Step 1: Parsed input")
    ctx.add_tokens(312)                 # accumulate token usage
    ctx.add_cost(0.0000074)             # accumulate USD cost
    ctx.set_metadata("model", "gpt-4o")

    tracer.record_decision(output={"result": "..."})
```

### record_decision()

Records the output and full provenance of the active decision. Must be called inside `trace_decision()`.

```python
tracer.record_decision(
    output={"approved": False},          # required — any JSON-serializable value
    confidence=0.74,                     # float 0–1
    reasoning=["Step 1", "Step 2"],      # reasoning chain (appends to ctx steps)
    uncertainties=["Income data stale"], # open questions
    assumptions=["Reported income is accurate"],
    constraints_checked=["min_credit_score >= 650"],
    constraints_violated=["income_freshness_days <= 30"],
    data_sources=["credit_bureau", "income_api"],
    quality_score=0.81,                  # independent quality rating
)
```

### record_memory_operation()

Track any of the five memory subsystems:

```python
from agentability.models import MemoryType, MemoryOperation

# Vector memory — track RAG retrieval quality
tracer.record_memory_operation(
    agent_id="rag_agent",
    memory_type=MemoryType.VECTOR,
    operation=MemoryOperation.RETRIEVE,
    latency_ms=38.5,
    items_processed=10,
    avg_similarity=0.61,              # low → stale embeddings alert
    oldest_item_age_hours=4320.0,     # 180 days → staleness signal
)

# Episodic memory — detect context window saturation
tracer.record_memory_operation(
    agent_id="chat_agent",
    memory_type=MemoryType.EPISODIC,
    operation=MemoryOperation.RETRIEVE,
    latency_ms=12.1,
    items_processed=5,
    context_tokens_used=3_840,
    context_tokens_limit=4_096,       # 93% full → truncation risk
    temporal_coherence=0.93,
)
```

**Memory types:**

| Type | What it tracks |
|---|---|
| `VECTOR` | Embedding store (RAG, semantic search) |
| `EPISODIC` | Conversation history, context window |
| `SEMANTIC` | Knowledge graph, facts |
| `WORKING` | In-flight scratchpad state |
| `PROCEDURAL` | Skill / tool memory |

### record_llm_call()

Track every LLM API call with cost and latency:

```python
tracer.record_llm_call(
    agent_id="summariser",
    provider="anthropic",
    model="claude-sonnet-4",
    prompt_tokens=1_500,
    completion_tokens=340,
    latency_ms=1_180.0,
    cost_usd=0.0083,
    finish_reason="end_turn",
    temperature=0.3,
)
```

### record_conflict()

Record a multi-agent conflict event:

```python
from agentability.models import ConflictType

tracer.record_conflict(
    session_id="execution-uuid",
    conflict_type=ConflictType.GOAL_CONFLICT,
    involved_agents=["risk_agent", "sales_agent"],
    agent_positions={
        "risk_agent":  {"decision": "deny",    "confidence": 0.82},
        "sales_agent": {"decision": "approve", "confidence": 0.78},
    },
    severity=0.71,                         # 0 = trivial, 1 = critical
    resolution_strategy="confidence_based",
)
```

**Conflict types:**

| Type | When |
|---|---|
| `GOAL_CONFLICT` | Agents pursuing incompatible objectives |
| `RESOURCE_CONFLICT` | Contention over shared resources (circuit breaker, rate limits) |
| `BELIEF_CONFLICT` | Agents hold contradictory beliefs about state |
| `PRIORITY_CONFLICT` | Disagreement on task ordering |
| `STRATEGY_CONFLICT` | Different approaches to the same goal |

### query_decisions()

```python
decisions = tracer.query_decisions(
    agent_id="analyst_agent",           # filter by agent
    session_id="execution-uuid",        # filter by AFMX execution
    decision_type=DecisionType.PLANNING,
    start_time=datetime(2026, 3, 1),
    end_time=datetime(2026, 3, 21),
    limit=100,
)

for d in decisions:
    print(d.decision_id, d.confidence, d.latency_ms, d.constraints_violated)
```

### DecisionType enum

| Value | Used for |
|---|---|
| `CLASSIFICATION` | Binary or multi-class decisions |
| `REGRESSION` | Numeric output predictions |
| `GENERATION` | Text / content generation |
| `RETRIEVAL` | Information lookup / RAG |
| `PLANNING` | Multi-step plan creation (AFMX AGENT nodes) |
| `EXECUTION` | Carrying out a plan step (AFMX TOOL nodes) |
| `DELEGATION` | Handing off to a sub-agent |
| `COORDINATION` | Multi-agent orchestration |
| `ROUTING` | Directing work to the right agent (AFMX FUNCTION nodes) |
| `TOOL_SELECTION` | Choosing which tool to call |

### Context manager usage

`Tracer` supports `with` for automatic `close()`:

```python
with Tracer(offline_mode=True) as tracer:
    with tracer.trace_decision("my_agent", DecisionType.PLANNING) as ctx:
        tracer.record_decision(output="done")
```

---

## Platform API

Start the REST API:

```bash
# From project root — shares the same SQLite file as AFMX when paths match
AGENTABILITY_DB=/path/to/agentability.db \
uvicorn platform.api.main:app --host 0.0.0.0 --port 8000 --reload

# Via Makefile
AGENTABILITY_DB=agentability.db make api
```

**Endpoints:**

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness + DB stats |
| `GET` | `/metrics` | Prometheus scrape endpoint |
| `GET` | `/api/decisions` | List decisions (paginated, filterable) |
| `GET` | `/api/decisions/{id}` | Single decision detail |
| `GET` | `/api/decisions/{id}/reasoning` | Reasoning chain + constraints |
| `GET` | `/api/agents` | List agents with aggregate metrics |
| `GET` | `/api/agents/{id}` | Single agent detail + timeline |
| `GET` | `/api/conflicts` | List conflicts |
| `GET` | `/api/conflicts/{id}` | Single conflict detail |
| `GET` | `/api/metrics/summary` | Aggregate stats: decisions, confidence, cost |
| `GET` | `/docs` | Swagger UI |

**Key query params for `/api/decisions`:**

| Param | Description |
|---|---|
| `session_id` | Filter to one AFMX execution (`session_id = afmx.execution_id`) |
| `agent_id` | Filter to one agent (`agent_id = matrix_name.node_name` in AFMX) |
| `decision_type` | One of the `DecisionType` values |
| `limit` / `offset` | Pagination (max 500 per page) |
| `start_time` / `end_time` | ISO 8601 datetime range filter |

---

## Dashboard

```bash
# Install dependencies (first time)
npm install          # from dashboard/ directory
# OR: make dashboard-install

# Development (hot reload)
cd dashboard && npm run dev
# → http://localhost:3000

# Production build
cd dashboard && npm run build    # outputs to dashboard/dist/
```

**Pages:**

| Page | What you see |
|---|---|
| Overview | KPI cards, confidence trend, latency p50/p95, cost by model, conflict rate |
| Decisions | Filterable table → click any row for full reasoning chain + constraint detail |
| Agents | Per-agent confidence timeline, drift alerts, capability radar |
| Conflicts | Conflict hotspot map, timeline, agent position detail |
| Cost & LLM | Token spend by model/provider, latency breakdown, retry events |

**Filtering by AFMX execution:**

In the Decisions page, paste an AFMX `execution_id` into the Session filter.
This shows only the decisions from that specific matrix run — every node
execution mapped to a Decision.

---

## AFMX Integration

When `AFMX_AGENTABILITY_ENABLED=true`, AFMX automatically records every node
execution into Agentability via `agentability_hook.py`.

**AFMX → Agentability mapping:**

| AFMX concept | Agentability concept |
|---|---|
| Matrix execution | Session (`session_id = execution_id`) |
| Node (AGENT type) | Decision (`DecisionType.PLANNING`) |
| Node (TOOL type) | Decision (`DecisionType.EXECUTION`) |
| Node (FUNCTION type) | Decision (`DecisionType.ROUTING`) |
| Retry attempt | `LLMMetrics(retry_count=N, finish_reason="retry_N")` |
| Circuit breaker open | `AgentConflict(RESOURCE_CONFLICT, severity=0.8)` |
| `output["confidence"]` | `Decision.confidence` |
| `output["_llm_meta"]` | `LLMMetrics` record |
| `output["_reasoning"]` | `Decision.reasoning` |
| `output["_constraints_violated"]` | `Decision.constraints_violated` |

**Setup:**

```bash
# 1. Install
pip install agentability

# 2. In AFMX .env
AFMX_AGENTABILITY_ENABLED=true
AFMX_AGENTABILITY_DB_PATH=/home/opc/agentability.db

# 3. Start Agentability platform (same DB file)
AGENTABILITY_DB=/home/opc/agentability.db \
uvicorn platform.api.main:app --host 0.0.0.0 --port 8000

# 4. Start Agentability dashboard
cd dashboard && npm run dev   # http://localhost:3000

# 5. Verify
curl http://localhost:8100/health | python3 -m json.tool
# → "agentability": {"enabled": true, "connected": true}
```

**Making AFMX data rich in Agentability:**

The `realistic_handlers.py` agents (in the AFMX project root) return
`_llm_meta`, `_reasoning`, and `_constraints_violated` keys. The
`agentability_hook.py` picks these up automatically. The result is
meaningful confidence scores, reasoning chains, and token costs in the
Agentability dashboard — without any manual integration work.

---

## Running Examples

All examples run from the project root:

```bash
# Seed the database with demo data
python3 sdk/python/examples/seed_demo.py

# RAG pipeline with memory staleness signals
python3 sdk/python/examples/rag_example.py

# Multi-agent conflict scenario
python3 sdk/python/examples/multi_agent_system.py

# Full demo runner (all scenarios)
python3 sdk/python/examples/demo_runner.py

# AFMX + Agentability integration demo
# (run from AFMX project root, needs AFMX server running)
python3 demo_agentability.py
```

---

## Architecture

```
Your Agent System
      │  (Tracer SDK calls)
      ▼
agentability/
  tracer.py          — Tracer, TracingContext
  models.py          — Decision, MemoryMetrics, LLMMetrics, AgentConflict
  storage/
    sqlite_store.py  — SQLite read/write (default, offline)
  integrations/
    anthropic_sdk.py — Auto-instrumentation for Anthropic client
    langchain.py     — LangChain callback handler
    crewai.py        — CrewAI instrumentation wrapper
    autogen.py       — AutoGen agent wrapper
      │
      ▼ (shared .db file)
platform/
  api/
    main.py          — FastAPI app, CORS, lifespan
    routers/
      decisions.py   — /api/decisions CRUD
      agents.py      — /api/agents aggregates
      conflicts.py   — /api/conflicts
      metrics.py     — /api/metrics/summary
      health.py      — /health + /metrics (Prometheus)
    schemas.py       — Pydantic response models
    dependencies.py  — get_store() singleton
      │
      ▼
dashboard/           — React 18 + TypeScript + Vite
  (reads from FastAPI platform at localhost:8000)
```

---

## Development

```bash
# Full dev setup
pip install -e ".[dev,all-integrations]"
pre-commit install

# Test suite (379 tests, ≥ 85% coverage required)
make test
# or: pytest --cov=sdk/python/agentability --cov-report=term-missing

# Quality gate (must pass before PR)
make lint          # ruff + flake8
make type-check    # mypy strict
make format        # black + isort

# Full stack
make api           # http://localhost:8000/docs
make dashboard     # http://localhost:3000
make dev           # both concurrently
```

See [CONTRIBUTING.md](../CONTRIBUTING.md) for the full guide, commit conventions, and review checklist.

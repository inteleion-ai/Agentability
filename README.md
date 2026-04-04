# Agentability

**Agent Operating Intelligence Layer for Production AI Systems**

[![PyPI version](https://badge.fury.io/py/agentability.svg)](https://pypi.org/project/agentability/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/inteleion-ai/Agentability/actions/workflows/ci.yml/badge.svg)](https://github.com/inteleion-ai/Agentability/actions)
[![Coverage](https://img.shields.io/badge/coverage-94%25-brightgreen.svg)](https://github.com/inteleion-ai/Agentability)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-yellow.svg)](https://conventionalcommits.org)

> **Langfuse tells you what your LLM said. Agentability tells you why your agent decided it.**

Agentability shows not just **what** your agents did, but **why** they decided it, **how** they reasoned through it, and **where** the failure originated.

---

## Why Agentability?

Production multi-agent systems fail in ways standard monitoring cannot explain. Existing tools record LLM calls. They do not understand that an agent made a low-confidence decision because memory retrieval returned six-month-old embeddings, which triggered a causal chain that caused an escalation.

Agentability is built specifically for agents:

| Capability | Standard APM | LLM Tracers | **Agentability** |
|---|---|---|---|
| Decision provenance (why) | — | Partial | ✓ Complete |
| Memory subsystem tracking | — | — | ✓ All five types |
| Causal graph (decision → decision) | — | — | ✓ Native |
| Multi-agent conflict analysis | — | — | ✓ Game-theoretic |
| Confidence drift detection | — | — | ✓ Statistical |
| Offline mode (zero infra) | — | — | ✓ SQLite |
| Open-source core | — | Partial | ✓ MIT |

---

## Installation

```bash
pip install agentability
```

Optional extras:

```bash
pip install "agentability[langchain]"        # LangChain integration
pip install "agentability[crewai]"           # CrewAI integration
pip install "agentability[autogen]"          # AutoGen integration
pip install "agentability[llamaindex]"       # LlamaIndex integration
pip install "agentability[all-integrations]" # All framework integrations
pip install "agentability[dev]"              # Development tools
```

---

## Quick Start

```python
from agentability import Tracer, DecisionType

# Zero infrastructure — stores to local SQLite file
tracer = Tracer(offline_mode=True)

with tracer.trace_decision(
    agent_id="risk_agent",
    decision_type=DecisionType.CLASSIFICATION,
    input_data={"loan_amount": 50_000, "credit_score": 680},
) as ctx:
    ctx.set_confidence(0.74)
    ctx.add_reasoning_step("Credit score meets minimum threshold")
    ctx.add_reasoning_step("Income verification pending — data is 90 days old")

    tracer.record_decision(
        output={"approved": False},
        uncertainties=["Employment stability not verified"],
        constraints_violated=["income_freshness_days <= 30"],
        data_sources=["credit_bureau", "income_api"],
    )

decisions = tracer.query_decisions(agent_id="risk_agent", limit=10)
tracer.close()
```

---

## Core Features

### Decision Provenance

Every decision records the complete reasoning chain: inputs, outputs, reasoning steps, uncertainties, assumptions, constraints checked vs violated, and data sources consulted.

```python
tracer.record_decision(
    output={"approved": False},
    confidence=0.42,
    reasoning=["Income data is stale (90 days)", "Cannot verify employment"],
    uncertainties=["No recent bank statements"],
    assumptions=["Reported income figure is accurate"],
    constraints_checked=["min_credit_score >= 650"],
    constraints_violated=["income_freshness_days <= 30"],
)
```

### Memory Intelligence

Track all five memory subsystems — the only observability library that does this.

```python
# Vector memory — RAG staleness detection
tracer.record_memory_operation(
    agent_id="rag_agent",
    memory_type=MemoryType.VECTOR,
    operation=MemoryOperation.RETRIEVE,
    latency_ms=38.5,
    items_processed=10,
    avg_similarity=0.61,            # low — stale embeddings
    oldest_item_age_hours=4320.0,   # 180 days old — staleness signal
)

# Episodic memory — context window saturation alert
tracer.record_memory_operation(
    agent_id="chat_agent",
    memory_type=MemoryType.EPISODIC,
    operation=MemoryOperation.RETRIEVE,
    latency_ms=12.1,
    items_processed=5,
    context_tokens_used=3_840,
    context_tokens_limit=4_096,     # 93% full — truncation imminent
    temporal_coherence=0.93,
)
```

### Multi-Agent Conflict Detection

```python
tracer.record_conflict(
    session_id="session_42",
    conflict_type=ConflictType.GOAL_CONFLICT,
    involved_agents=["risk_agent", "sales_agent"],
    agent_positions={
        "risk_agent":  {"decision": "deny",    "confidence": 0.82},
        "sales_agent": {"decision": "approve", "confidence": 0.78},
    },
    severity=0.71,
    resolution_strategy="confidence_based",
)
```

### LLM Cost Tracking

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
)
```

---

## Framework Integrations

### Anthropic SDK (auto-instrumented)

```python
from agentability.integrations.anthropic_sdk import AnthropicInstrumentation
import anthropic

tracer = Tracer(offline_mode=True)
client = anthropic.Anthropic()
client = AnthropicInstrumentation(tracer=tracer, agent_id="my_agent").wrap_client(client)

# All subsequent client.messages.create() calls are now tracked automatically
```

### LangChain

```python
from agentability.integrations.langchain import AgentabilityLangChainCallback

callback = AgentabilityLangChainCallback(tracer=tracer, agent_id="langchain_agent")
chain.invoke({"input": "Summarise this document"}, config={"callbacks": [callback]})
```

### CrewAI

```python
from agentability.integrations.crewai import CrewAIInstrumentation

crew = CrewAIInstrumentation(tracer=tracer).instrument_crew(crew)
result = crew.kickoff()
```

### AutoGen

```python
from agentability.integrations.autogen import AutoGenInstrumentation

agent = AutoGenInstrumentation(tracer=tracer).instrument_agent(agent)
```

---

## Dashboard

The Agentability dashboard provides a Datadog-quality dark UI for agent observability.

```bash
# Start the API server
AGENTABILITY_DB=agentability.db \
uvicorn platform.api.main:app --host 0.0.0.0 --port 8000

# Start the dashboard (separate terminal)
cd dashboard && npm install && npm run dev -- --host 0.0.0.0
```

Open `http://localhost:3000` to see:
- **Overview** — KPI cards, confidence trend, latency, cost, conflicts
- **Decisions** — Full decision explorer with reasoning chain drill-down
- **Agents** — Per-agent confidence timeline + drift alerts
- **Conflicts** — Multi-agent conflict hotspot map and timeline
- **Cost & LLM** — Token spend breakdown by model and provider

---

## Architecture

```
Your Agent System
      │
      ▼
 Agentability SDK  (Python — TypeScript & Go coming in v0.5/v0.7)
      │
      ▼
 Storage Layer
 ┌──────────┬──────────┬──────────────┐
 │  SQLite  │  DuckDB  │ TimescaleDB  │
 │ (offline)│(analytics│ (production) │
 └──────────┴──────────┴──────────────┘
      │
      ▼
 Analytics Engine
 ┌──────────────┬──────────────┬───────────────┐
 │ Causal Graph │ Drift Detect │ Conflict Anal │
 └──────────────┴──────────────┴───────────────┘
      │
      ▼
 FastAPI Platform  →  React Dashboard
```

---

## Competitive Comparison

| Feature | **Agentability** | Langfuse | AgentOps | Arize Phoenix |
|---|---|---|---|---|
| Memory tracking (all 5 types) | ✓ | — | — | — |
| Decision provenance (why) | ✓ Complete | Partial | Partial | — |
| Multi-agent conflict analysis | ✓ Game-theoretic | — | — | — |
| Temporal causal graphs | ✓ | — | — | — |
| Confidence drift detection | ✓ | — | — | — |
| Offline / SQLite mode | ✓ | — | — | Limited |
| Open-source core | ✓ MIT | Partial | — | ✓ Apache 2 |

---

## Roadmap

### v0.3.0 — May 2026
- [ ] `AsyncTracer` with `contextvars.ContextVar` (asyncio-safe)
- [ ] OpenTelemetry OTLP exporter backend
- [ ] DuckDB analytics backend + Parquet export

### v0.4.0 — June 2026
- [ ] OpenAI Agents SDK integration
- [ ] LangGraph node-level tracing
- [ ] Pydantic AI integration
- [ ] CUSUM drift detection algorithm

### v0.5.0 — July 2026
- [ ] TypeScript SDK
- [ ] WebSocket real-time streaming to dashboard
- [ ] D3 causal graph visualiser in dashboard
- [ ] Docker Compose one-command deploy

### v0.6.0 — August 2026
- [ ] Counterfactual analysis
- [ ] A/B testing framework for agent versions
- [ ] RBAC + Audit logs (SOC2 alignment)
- [ ] SSO (OIDC + SAML2)

---

## Development Setup

```bash
git clone https://github.com/inteleion-ai/Agentability.git
cd Agentability

# Install SDK in editable mode with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run the test suite (379 tests, 94% coverage)
make test

# Quality gate
make lint && make type-check

# Seed demo data and start the stack
python3 sdk/python/examples/seed_demo.py
make api          # http://localhost:8000/docs
make dashboard    # http://localhost:3000
```

---

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for setup,
style guide, and the quality gate. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
for community standards.

---

## License

MIT — see [LICENSE](LICENSE).  
Commercial cloud and enterprise features: see [COMMERCIAL.md](COMMERCIAL.md).

---

## Links

- **GitHub:** https://github.com/inteleion-ai/Agentability
- **PyPI:** https://pypi.org/project/agentability/
- **Issues:** https://github.com/inteleion-ai/Agentability/issues
- **Discussions:** https://github.com/inteleion-ai/Agentability/discussions
- **Email:** hello@agentability.io

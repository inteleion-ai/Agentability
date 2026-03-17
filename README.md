# Agentability

**Agent Operating Intelligence Layer for Production AI Systems**

[![PyPI version](https://badge.fury.io/py/agentability.svg)](https://pypi.org/project/agentability/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/inteleion-ai/Agentability/actions/workflows/ci.yml/badge.svg)](https://github.com/inteleion-ai/Agentability/actions)
[![Coverage](https://img.shields.io/badge/coverage-94%25-brightgreen.svg)](https://github.com/inteleion-ai/Agentability)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-yellow.svg)](https://conventionalcommits.org)

> Agentability shows not just **what** your agents did, but **why** they decided it, **how** they reasoned through it, and **where** the failure originated.

---

## Why Agentability?

Production multi-agent systems fail in ways that standard application monitoring cannot explain. Existing observability tools record HTTP requests and log lines. They do not understand that an agent made a low-confidence decision because the memory retrieval returned six-month-old data, which triggered a causal chain that ultimately caused an escalation.

Agentability is built specifically for agents:

| Capability | Standard APM | LLM Tracers | Agentability |
|---|---|---|---|
| Decision provenance (why) | — | Partial | ✓ Complete |
| Memory subsystem tracking | — | — | ✓ All five types |
| Causal graph (decision → decision) | — | — | ✓ Native |
| Multi-agent conflict analysis | — | — | ✓ Game-theoretic |
| Confidence drift detection | — | — | ✓ Statistical |
| Offline mode (no infra) | — | — | ✓ SQLite |
| Open-source core | — | Partial | ✓ MIT |

---

## Installation

```bash
pip install agentability
```

For optional extras:

```bash
pip install "agentability[langchain]"       # LangChain integration
pip install "agentability[crewai]"          # CrewAI integration
pip install "agentability[autogen]"         # AutoGen integration
pip install "agentability[llamaindex]"      # LlamaIndex integration
pip install "agentability[all-integrations]" # All integrations
pip install "agentability[duckdb]"          # DuckDB analytics backend
pip install "agentability[dev]"             # Development dependencies
```

---

## Quick Start

```python
from agentability import Tracer, DecisionType

# Offline mode: data persisted to a local SQLite file — no infrastructure needed.
tracer = Tracer(offline_mode=True)

with tracer.trace_decision(
    agent_id="risk_agent",
    decision_type=DecisionType.CLASSIFICATION,
    input_data={"loan_amount": 50_000, "credit_score": 680},
) as ctx:
    result = agent.assess(application)

    tracer.record_decision(
        output=result,
        confidence=0.74,
        reasoning=[
            "Credit score meets minimum threshold",
            "Income verification pending — data is 90 days old",
        ],
        uncertainties=["Employment stability not verified"],
        data_sources=["credit_bureau", "income_api"],
    )

decisions = tracer.query_decisions(agent_id="risk_agent", limit=10)
tracer.close()
```

---

## Core Features

### Decision Provenance

Every decision records the complete reasoning chain: inputs, outputs, reasoning steps, uncertainties, assumptions, constraints checked, and which data sources were consulted.

```python
tracer.record_decision(
    output={"approved": False},
    confidence=0.42,
    reasoning=["Income data is stale (90 days)", "Cannot verify current employment"],
    uncertainties=["No recent bank statements"],
    assumptions=["Reported income figure is accurate"],
    constraints_checked=["min_credit_score >= 650"],
    constraints_violated=["income_freshness_days <= 30"],
)
```

### Memory Intelligence

Track all five memory subsystems — the only observability library that does so.

```python
# Vector memory (RAG / embeddings)
tracer.record_memory_operation(
    agent_id="rag_agent",
    memory_type=MemoryType.VECTOR,
    operation=MemoryOperation.RETRIEVE,
    latency_ms=38.5,
    items_processed=10,
    avg_similarity=0.81,
    retrieval_precision=0.84,
    oldest_item_age_hours=72.0,   # Staleness signal
)

# Episodic memory (conversation history)
tracer.record_memory_operation(
    agent_id="chat_agent",
    memory_type=MemoryType.EPISODIC,
    operation=MemoryOperation.RETRIEVE,
    latency_ms=12.1,
    items_processed=5,
    temporal_coherence=0.93,
    context_tokens_used=1_840,
    context_tokens_limit=8_192,
)
```

### Multi-Agent Conflict Analytics

```python
tracer.record_conflict(
    session_id="session_42",
    conflict_type=ConflictType.GOAL_CONFLICT,
    involved_agents=["risk_agent", "sales_agent"],
    agent_positions={
        "risk_agent": {"decision": "deny", "confidence": 0.82},
        "sales_agent": {"decision": "approve", "confidence": 0.78},
    },
    severity=0.71,
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

### Anthropic SDK

```python
from agentability.integrations.anthropic_sdk import AnthropicInstrumentation
import anthropic

client = anthropic.Anthropic()
client = AnthropicInstrumentation(tracer=tracer).wrap_client(client)
# All subsequent client.messages.create() calls are now tracked automatically.
```

---

## Architecture

```
Your Agent System
      │
      ▼
 Agentability SDK  ──────────────────────────────────────────┐
 (Python / TypeScript / Go)                                  │
      │                                                       │
      ▼                                                       │
 Storage Layer                                               │
 ┌──────────┬──────────┬──────────────┐                     │
 │ SQLite   │ DuckDB   │ TimescaleDB  │                     │
 │ (offline)│(analytics│ (production) │                     │
 └──────────┴──────────┴──────────────┘                     │
      │                                                       │
      ▼                                                       │
 Analytics Engine                                            │
 ┌──────────────┬──────────────┬───────────────┐            │
 │ Causal Graph │ Drift Detect │ Conflict Anal │            │
 └──────────────┴──────────────┴───────────────┘            │
      │                                                       │
      ▼                                                       │
 API Server (FastAPI + WebSocket)                            │
      │                                                       │
      ▼                                                       │
 Dashboard (React + TypeScript)  ◄──────────────────────────┘
```

---

## Pricing

| Tier | Price | Decisions / month | Support |
|---|---|---|---|
| Open Source | Free | Unlimited (self-hosted) | Community |
| Cloud Starter | Free | 1 million | Community |
| Cloud Pro | $49 / month | 10 million | Priority |
| Cloud Enterprise | Custom | 100 million+ | Dedicated + SLA |

Self-hosted cost: approximately $2 per 1 million decisions.

---

## Documentation

Full documentation: [docs.agentability.io](https://docs.agentability.io)

- [Getting Started](docs/getting-started/quickstart.md)
- [Python SDK Reference](docs/api-reference/python-sdk.md)
- [Memory Tracking Guide](docs/guides/memory-tracking.md)
- [Multi-Agent Systems Guide](docs/guides/multi-agent-systems.md)
- [Production Deployment](docs/guides/production-deployment.md)

---

## Development Setup

```bash
git clone https://github.com/agentability/agentability.git
cd agentability

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run the test suite
pytest

# Type checking
mypy sdk/python/agentability

# Code formatting
black sdk/python/agentability
isort sdk/python/agentability
```

---

## Comparison

| Feature | Agentability | Langfuse | AgentOps | Arize Phoenix |
|---|---|---|---|---|
| Memory tracking (all types) | ✓ | — | — | — |
| Decision provenance | ✓ Complete | Partial | Partial | — |
| Multi-agent conflict analysis | ✓ Game-theoretic | — | — | — |
| Temporal causal graphs | ✓ | — | — | — |
| Offline / SQLite mode | ✓ | — | — | Limited |
| Open-source core | ✓ MIT | Partial | — | ✓ Apache 2 |
| Cost per 1M decisions | $2 | $12 | $8 | $10 |

---

## Roadmap

### Q2 2026
- [ ] TypeScript SDK
- [ ] LangGraph integration
- [ ] OpenAI Agents SDK integration
- [ ] DuckDB analytics backend
- [ ] Dashboard MVP

### Q3 2026
- [ ] Reasoning tree tracing
- [ ] Agent replay engine
- [ ] TimescaleDB production backend
- [ ] OpenTelemetry native mode
- [ ] Streaming event bus

### Q4 2026
- [ ] Go SDK
- [ ] Counterfactual analysis
- [ ] Agent benchmark framework
- [ ] Agent simulation engine
- [ ] SaaS alpha

---

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines,
and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for community standards.

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

## Contact

- Website: [agentability.io](https://agentability.io)
- Email: hello@agentability.io
- Discord: [discord.gg/agentability](https://discord.gg/agentability)
- GitHub Discussions: [github.com/agentability/agentability/discussions](https://github.com/agentability/agentability/discussions)

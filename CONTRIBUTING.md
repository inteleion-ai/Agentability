# Contributing to Agentability

Thank you for taking the time to contribute. This document describes how to
set up your environment, submit changes, and meet the quality bar required
for merging.

---

## Code of Conduct

All contributors are expected to follow our [Code of Conduct](CODE_OF_CONDUCT.md).
In short: be constructive, respectful, and collaborative.

---

## Getting Started

### Prerequisites

| Tool | Version |
|---|---|
| Python | 3.9 or later |
| Node.js | 18 or later |
| Git | 2.40 or later |
| Docker (optional) | 24 or later |

### Environment Setup

```bash
# 1. Fork and clone
git clone https://github.com/inteleion-ai/Agentability.git
cd Agentability

# 2. Install Python SDK in editable mode (dev extras include all linters)
pip install -e ".[dev]"

# 3. Install pre-commit hooks
pre-commit install

# 4. Install dashboard dependencies
cd dashboard && npm install && cd ..

# 5. Verify the test suite passes
pytest

# 6. Optional: start a local development stack
docker-compose -f docker-compose.dev.yml up
```

---

## Repository Layout

```
agentability/
├── sdk/
│   ├── python/
│   │   ├── agentability/      # Core Python package
│   │   ├── tests/             # pytest test suite
│   │   └── examples/          # Runnable usage examples
│   └── typescript/            # TypeScript SDK (Q2 2026)
├── platform/
│   ├── api/                   # FastAPI server
│   ├── collectors/            # OTEL / streaming collectors
│   └── workers/               # Background workers
├── dashboard/                 # React + TypeScript UI
├── infrastructure/            # Docker, Helm, Kubernetes
└── docs/                      # Docusaurus documentation site
```

---

## How to Contribute

### Reporting Bugs

Before opening an issue, search existing issues to avoid duplicates.
A good bug report includes:

- A clear, descriptive title.
- Steps to reproduce (minimal code sample preferred).
- Expected behaviour vs. actual behaviour.
- Python version, OS, and `pip show agentability` output.

### Suggesting Features

Open an issue with the label `enhancement`. Describe:

- The use case and the problem it solves.
- A proposed API or interface sketch.
- Any backwards-compatibility considerations.

### Submitting Pull Requests

1. Create a feature branch from `main`:
   `git checkout -b feat/my-feature`
2. Make your changes.
3. Add or update tests to maintain > 80 % coverage.
4. Update `CHANGELOG.md` under `[Unreleased]`.
5. Run the full quality gate (see below).
6. Commit using [Conventional Commits](#commit-messages).
7. Open a pull request against `main`.

---

## Quality Gate

Every PR must pass all checks before merge:

```bash
# Formatting
black sdk/python/agentability
isort sdk/python/agentability

# Linting
ruff check sdk/python/agentability
flake8 sdk/python/agentability

# Type checking
mypy sdk/python/agentability

# Tests with coverage
pytest --cov=agentability --cov-report=term-missing

# TypeScript (dashboard)
cd dashboard && npm run lint && npm run type-check
```

---

## Python Code Style

Agentability follows the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
with the following tools configured in `pyproject.toml`:

- **black** — code formatting (line length 88)
- **isort** — import ordering (black-compatible profile)
- **mypy** — strict type checking
- **ruff / flake8** — linting

Key conventions:

- All public functions, methods, and classes must have Google-style docstrings.
- Use type annotations everywhere; `Any` is permitted only where unavoidable.
- Keep functions under 50 lines; prefer pure functions.
- Prefer composition over inheritance.

---

## TypeScript Code Style

The dashboard follows the [Airbnb TypeScript Style Guide](https://github.com/airbnb/javascript):

- Strict TypeScript mode (`"strict": true` in `tsconfig.json`).
- Functional React components with hooks only.
- Explicit return types on all non-trivial functions.
- JSDoc comments on all exported symbols.

---

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short summary>

[optional body]

[optional footer]
```

Allowed types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`,
`chore`, `ci`.

Examples:

```
feat(sdk): add TracingContext helper methods

- Expose set_confidence(), add_tokens(), add_cost(), add_reasoning_step()
- Fix integration wrappers that previously called non-existent methods on UUID

Closes #42
```

```
fix(models): use min_length=2 for Pydantic v2 compatibility

Replaces deprecated min_items=2 on AgentConflict.involved_agents.
```

---

## Testing

### Writing Tests

```python
"""Tests for decision provenance tracking."""

import pytest
from agentability import Tracer
from agentability.models import DecisionType


class TestDecisionProvenance:
    """Unit tests for Tracer.record_decision()."""

    @pytest.fixture
    def tracer(self, tmp_path):
        """Return an offline Tracer backed by a temporary database."""
        t = Tracer(offline_mode=True, database_path=str(tmp_path / "test.db"))
        yield t
        t.close()

    def test_basic_decision_is_persisted(self, tracer):
        """A decision recorded inside trace_decision() should be retrievable."""
        with tracer.trace_decision(
            agent_id="test_agent",
            decision_type=DecisionType.CLASSIFICATION,
        ):
            tracer.record_decision(output="approved", confidence=0.85)

        decisions = tracer.query_decisions(agent_id="test_agent")
        assert len(decisions) == 1
        assert decisions[0].confidence == pytest.approx(0.85)

    def test_decision_captures_reasoning(self, tracer):
        """Reasoning steps and uncertainties should be stored correctly."""
        with tracer.trace_decision(
            agent_id="risk_agent",
            decision_type=DecisionType.CLASSIFICATION,
        ):
            tracer.record_decision(
                output="denied",
                confidence=0.72,
                reasoning=["Score below threshold", "Income unverified"],
                uncertainties=["Employment stability unknown"],
            )

        decision = tracer.query_decisions(agent_id="risk_agent")[0]
        assert decision.reasoning == ["Score below threshold", "Income unverified"]
        assert len(decision.uncertainties) == 1
```

### Coverage Target

All PRs must maintain **≥ 85 % line coverage** across the SDK. The CI
pipeline enforces this automatically.

---

## Code Review

1. All automated checks must pass.
2. At least one maintainer approval is required.
3. All reviewer comments must be addressed before merge.
4. Squash commits if the history is noisy.

### Reviewer Checklist

- [ ] Code follows the style guide.
- [ ] Tests added or updated.
- [ ] Documentation updated (docstrings, README, guides).
- [ ] No breaking API changes (or migration guide provided).
- [ ] Performance implications considered.
- [ ] Security implications reviewed.

---

## Recognition

Contributors are listed in [AUTHORS.md](AUTHORS.md), mentioned in release
notes, and invited to the contributors channel on Discord.

---

## Questions?

- GitHub Discussions: [github.com/inteleion-ai/Agentability/discussions](https://github.com/inteleion-ai/Agentability/discussions)
- GitHub Issues: [github.com/inteleion-ai/Agentability/issues](https://github.com/inteleion-ai/Agentability/issues)
- Email: hello@agentability.io

---

By contributing to Agentability, you agree that your code will be released
under the MIT License.

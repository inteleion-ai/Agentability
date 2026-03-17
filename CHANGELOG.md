# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0a1] - 2026-03-17

### Added
- 379 tests across 9 test files; all passing.
- `test_utils.py` — full coverage of `serialization` and `validation` utils.
- `test_memory.py` — episodic, semantic, and working memory tracker tests.
- `test_metrics.py` — `DecisionMetricsCollector`, `LLMCallTracker`,
  `MemoryMetricsCollector`, `ConflictMetricsCollector`, precision/recall helpers.
- `test_coverage_boost.py` — `AgentabilityScorer`, `PolicyEvaluator`,
  `TraceSampler`, `ImportanceScorer`, `VersionTracker`, `CostAnalyzer`,
  `LineageTracer`, `ProvenanceAnalyzer`.
- `test_integrations.py` — mock-based tests for all five framework integrations
  (Anthropic SDK, CrewAI, AutoGen, LangChain, LlamaIndex).
- `[tool.ruff.lint.isort]` section in `pyproject.toml`; `known-first-party`
  declares `agentability` so I001 import-sort errors stay clean.
- `.flake8` config: `max-line-length = 88`, `extend-ignore = E203,E501,W503`.

### Fixed
- `tracer.py` — `record_decision()` no longer overwrites confidence or reasoning
  set via `ctx.set_confidence()` / `ctx.add_reasoning_step()`.
- `storage/sqlite_store.py` — added `threading.Lock` to all four write methods;
  eliminates `sqlite3.OperationalError: cannot start a transaction within a
  transaction` under concurrent thread use.
- `integrations/llamaindex.py` — `top_k=0` replaced with `top_k=None` when
  no source nodes are present; satisfies `MemoryMetrics.top_k` `ge=1` constraint.
- `integrations/autogen.py` — removed stale `# type: ignore[return-value]`;
  `generate_reply` now returns `str | None` cleanly.
- `storage/sqlite_store.py` — removed stale `# type: ignore[name-defined]`
  on `_row_to_decision`.
- `analyzers/cost_analyzer.py` — `get_total_cost` sum wrapped in `float()`
  to satisfy mypy `no-any-return`.

### Changed
- `pyproject.toml` — `fail_under` raised from 80 → 85 (Google OSS standard).
- Version bumped `0.1.0` → `0.2.0a1`.
- All 149 ruff lint errors from prior sessions fully resolved; 39 source files
  pass `ruff`, `flake8`, `mypy` with zero errors.

### Coverage
- Total: **94.27 %** (threshold: 85 %)

## [0.1.0] - 2026-02-08

### Added
- Python SDK core: `Tracer`, `Decision`, `MemoryMetrics`, `LLMMetrics`,
  `AgentConflict` models.
- SQLite offline storage backend (`SQLiteStore`).
- Five memory subsystem trackers: vector, episodic, semantic, working,
  procedural.
- Causal graph builder (`CausalGraphBuilder`).
- Confidence drift detector (`DriftDetector`).
- Multi-agent conflict analyser (`ConflictAnalyzer`).
- Decision provenance analyser (`ProvenanceAnalyzer`).
- LLM cost analyser with provider pricing tables (`CostAnalyzer`).
- Version snapshot tracker (`VersionTracker`).
- Policy evaluator with PII and cost rules (`PolicyEvaluator`).
- Sampling system for cost-controlled tracing (`TraceSampler`).
- Framework integration stubs: LangChain, CrewAI, AutoGen, LlamaIndex,
  Anthropic SDK.
- Dashboard scaffold: Vite + React 18 + TypeScript + Tailwind CSS.
- `pyproject.toml` with PEP 517/518 build, nine optional extras, full mypy
  and black configuration.

[Unreleased]: https://github.com/inteleion-ai/Agentability/compare/v0.2.0a1...HEAD
[0.2.0a1]: https://github.com/inteleion-ai/Agentability/compare/v0.1.0...v0.2.0a1
[0.1.0]: https://github.com/inteleion-ai/Agentability/releases/tag/v0.1.0

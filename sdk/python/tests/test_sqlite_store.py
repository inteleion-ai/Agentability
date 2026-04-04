"""Tests for the SQLite storage backend.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from uuid import uuid4

import pytest

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


@pytest.fixture()
def store(tmp_path: Path) -> Generator[SQLiteStore, None, None]:
    """Fresh SQLiteStore backed by a temporary file."""
    s = SQLiteStore(str(tmp_path / "test.db"))
    yield s
    s.close()


def _make_decision(
    agent_id: str = "agent_1",
    decision_type: DecisionType = DecisionType.CLASSIFICATION,
    session_id: str | None = None,
    parent_decision_id: object = None,
    reasoning: list[str] | None = None,
    confidence: float | None = None,
    tags: list[str] | None = None,
) -> Decision:
    return Decision(
        agent_id=agent_id,
        decision_type=decision_type,
        session_id=session_id,
        output_data={"result": "ok"},
        confidence=confidence,
        reasoning=reasoning or [],
        tags=tags or [],
        parent_decision_id=parent_decision_id,  # type: ignore[arg-type]
    )


class TestSchemaInit:
    def test_tables_exist_after_init(self, tmp_path: Path) -> None:
        import sqlite3

        db_path = str(tmp_path / "schema.db")
        SQLiteStore(db_path).close()
        conn = sqlite3.connect(db_path)
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        conn.close()
        assert "decisions" in tables
        assert "memory_metrics" in tables
        assert "llm_metrics" in tables
        assert "conflicts" in tables


class TestDecisionStorage:
    def test_save_and_retrieve_by_id(self, store: SQLiteStore) -> None:
        d = _make_decision()
        store.save_decision(d)
        retrieved = store.get_decision(d.decision_id)
        assert retrieved is not None
        assert retrieved.decision_id == d.decision_id

    def test_missing_id_returns_none(self, store: SQLiteStore) -> None:
        assert store.get_decision(uuid4()) is None

    def test_agent_id_round_trip(self, store: SQLiteStore) -> None:
        d = _make_decision(agent_id="specific_agent")
        store.save_decision(d)
        retrieved = store.get_decision(d.decision_id)
        assert retrieved is not None
        assert retrieved.agent_id == "specific_agent"

    def test_reasoning_round_trip(self, store: SQLiteStore) -> None:
        steps = ["First step", "Second step", "Third step"]
        d = _make_decision(reasoning=steps)
        store.save_decision(d)
        retrieved = store.get_decision(d.decision_id)
        assert retrieved is not None
        assert retrieved.reasoning == steps

    def test_confidence_round_trip(self, store: SQLiteStore) -> None:
        d = _make_decision(confidence=0.74)
        store.save_decision(d)
        retrieved = store.get_decision(d.decision_id)
        assert retrieved is not None
        assert retrieved.confidence == pytest.approx(0.74)

    def test_tags_round_trip(self, store: SQLiteStore) -> None:
        d = _make_decision(tags=["production", "risk"])
        store.save_decision(d)
        retrieved = store.get_decision(d.decision_id)
        assert retrieved is not None
        assert set(retrieved.tags) == {"production", "risk"}

    def test_query_by_agent_id(self, store: SQLiteStore) -> None:
        store.save_decision(_make_decision(agent_id="alice"))
        store.save_decision(_make_decision(agent_id="alice"))
        store.save_decision(_make_decision(agent_id="bob"))
        results = store.query_decisions(agent_id="alice")
        assert len(results) == 2
        assert all(d.agent_id == "alice" for d in results)

    def test_query_by_session_id(self, store: SQLiteStore) -> None:
        store.save_decision(_make_decision(session_id="sess_x"))
        store.save_decision(_make_decision(session_id="sess_y"))
        assert len(store.query_decisions(session_id="sess_x")) == 1

    def test_query_by_decision_type(self, store: SQLiteStore) -> None:
        store.save_decision(_make_decision(decision_type=DecisionType.PLANNING))
        store.save_decision(_make_decision(decision_type=DecisionType.GENERATION))
        results = store.query_decisions(decision_type=DecisionType.PLANNING)
        assert len(results) == 1
        assert results[0].decision_type == DecisionType.PLANNING

    def test_query_limit(self, store: SQLiteStore) -> None:
        for _ in range(10):
            store.save_decision(_make_decision())
        assert len(store.query_decisions(limit=4)) == 4

    def test_parent_decision_id_round_trip(self, store: SQLiteStore) -> None:
        parent = _make_decision()
        store.save_decision(parent)
        child = _make_decision(parent_decision_id=parent.decision_id)
        store.save_decision(child)
        retrieved = store.get_decision(child.decision_id)
        assert retrieved is not None
        assert retrieved.parent_decision_id == parent.decision_id


class TestMemoryMetricsStorage:
    def test_returns_uuid(self, store: SQLiteStore) -> None:
        from uuid import UUID

        m = MemoryMetrics(
            agent_id="rag",
            memory_type=MemoryType.VECTOR,
            operation=MemoryOperation.RETRIEVE,
            latency_ms=30.0,
            items_processed=5,
        )
        op_id = store.save_memory_metrics(m)
        assert isinstance(op_id, UUID)

    def test_vector_metrics_stored_without_error(self, store: SQLiteStore) -> None:
        m = MemoryMetrics(
            agent_id="rag",
            memory_type=MemoryType.VECTOR,
            operation=MemoryOperation.RETRIEVE,
            latency_ms=38.5,
            items_processed=10,
            avg_similarity=0.82,
            retrieval_precision=0.85,
            retrieval_recall=0.78,
            top_k=10,
            vector_dimension=1536,
        )
        store.save_memory_metrics(m)


class TestLLMMetricsStorage:
    def test_returns_uuid(self, store: SQLiteStore) -> None:
        from uuid import UUID

        m = LLMMetrics(
            agent_id="llm_a",
            provider="anthropic",
            model="claude-sonnet-4",
            prompt_tokens=500,
            completion_tokens=200,
            total_tokens=700,
            latency_ms=900.0,
            cost_usd=0.005,
        )
        assert isinstance(store.save_llm_metrics(m), UUID)

    def test_streaming_fields_stored(self, store: SQLiteStore) -> None:
        m = LLMMetrics(
            agent_id="llm_b",
            provider="openai",
            model="gpt-4",
            prompt_tokens=1000,
            completion_tokens=400,
            total_tokens=1400,
            latency_ms=1500.0,
            cost_usd=0.06,
            is_streaming=True,
            time_to_first_token_ms=250.0,
            chunks_received=32,
        )
        store.save_llm_metrics(m)


class TestConflictStorage:
    def test_returns_uuid(self, store: SQLiteStore) -> None:
        from uuid import UUID

        c = AgentConflict(
            session_id="sess_1",
            conflict_type=ConflictType.GOAL_CONFLICT,
            involved_agents=["risk", "sales"],
            agent_positions={"risk": {"v": 0}, "sales": {"v": 1}},
            severity=0.6,
        )
        assert isinstance(store.save_conflict(c), UUID)

    def test_conflict_with_metadata_stored(self, store: SQLiteStore) -> None:
        c = AgentConflict(
            session_id="sess_2",
            conflict_type=ConflictType.PRIORITY_CONFLICT,
            involved_agents=["a", "b"],
            agent_positions={"a": {}, "b": {}},
            severity=0.4,
            nash_equilibrium={"strategy": "compromise"},
            pareto_optimal=True,
        )
        store.save_conflict(c)

"""SQLite storage backend for offline mode.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import contextlib
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from uuid import UUID

from agentability.models import (
    AgentConflict,
    Decision,
    DecisionType,
    LLMMetrics,
    MemoryMetrics,
)
from agentability.utils.logger import get_logger
from agentability.utils.serialization import deserialize_data, serialize_data

logger = get_logger(__name__)

_CREATE_DECISIONS = """
CREATE TABLE IF NOT EXISTS decisions (
    decision_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    session_id TEXT,
    timestamp TEXT NOT NULL,
    latency_ms REAL,
    decision_type TEXT NOT NULL,
    input_data TEXT,
    output_data TEXT,
    reasoning TEXT,
    uncertainties TEXT,
    assumptions TEXT,
    constraints_checked TEXT,
    constraints_violated TEXT,
    confidence REAL,
    quality_score REAL,
    parent_decision_id TEXT,
    child_decision_ids TEXT,
    data_sources TEXT,
    memory_operations TEXT,
    llm_calls INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    total_cost_usd REAL DEFAULT 0.0,
    tags TEXT,
    metadata TEXT,
    FOREIGN KEY (parent_decision_id) REFERENCES decisions(decision_id)
)
"""

_CREATE_MEMORY = """
CREATE TABLE IF NOT EXISTS memory_metrics (
    operation_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    memory_type TEXT NOT NULL,
    operation TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    latency_ms REAL NOT NULL,
    items_processed INTEGER NOT NULL,
    bytes_processed INTEGER,
    vector_dimension INTEGER,
    similarity_threshold REAL,
    top_k INTEGER,
    avg_similarity REAL,
    min_similarity REAL,
    max_similarity REAL,
    retrieval_precision REAL,
    retrieval_recall REAL,
    time_range_start TEXT,
    time_range_end TEXT,
    episodes_retrieved INTEGER,
    temporal_coherence REAL,
    context_tokens_used INTEGER,
    context_tokens_limit INTEGER,
    knowledge_graph_nodes INTEGER,
    relationships_traversed INTEGER,
    max_hop_distance INTEGER,
    graph_density REAL,
    oldest_item_age_hours REAL,
    average_item_age_hours REAL,
    cache_hit_rate REAL,
    metadata TEXT
)
"""

_CREATE_LLM = """
CREATE TABLE IF NOT EXISTS llm_metrics (
    call_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    decision_id TEXT,
    timestamp TEXT NOT NULL,
    latency_ms REAL NOT NULL,
    time_to_first_token_ms REAL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_tokens INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    cost_usd REAL NOT NULL,
    finish_reason TEXT,
    is_streaming INTEGER DEFAULT 0,
    chunks_received INTEGER,
    rate_limited INTEGER DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    temperature REAL,
    max_tokens INTEGER,
    metadata TEXT,
    FOREIGN KEY (decision_id) REFERENCES decisions(decision_id)
)
"""

_CREATE_CONFLICTS = """
CREATE TABLE IF NOT EXISTS conflicts (
    conflict_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    conflict_type TEXT NOT NULL,
    involved_agents TEXT NOT NULL,
    agent_positions TEXT NOT NULL,
    severity REAL NOT NULL,
    resolution_strategy TEXT,
    resolution_outcome TEXT,
    nash_equilibrium TEXT,
    pareto_optimal INTEGER,
    resolved INTEGER DEFAULT 0,
    resolution_time_ms REAL,
    metadata TEXT
)
"""


class SQLiteStore:
    """SQLite storage backend.

    All data is persisted to a single local ``.db`` file. Safe for
    concurrent access within a single process.

    Args:
        database_path: Path to the SQLite database file.
    """

    def __init__(self, database_path: str = "agentability.db") -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

        self.conn = sqlite3.connect(
            str(self.database_path),
            check_same_thread=False,
        )
        self.conn.row_factory = sqlite3.Row
        self._initialize_schema()
        logger.info("SQLite storage initialised: %s", self.database_path)

    def _initialize_schema(self) -> None:
        cursor = self.conn.cursor()
        cursor.execute(_CREATE_DECISIONS)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_decisions_agent "
            "ON decisions(agent_id, timestamp DESC)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_decisions_session "
            "ON decisions(session_id, timestamp DESC)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_decisions_type "
            "ON decisions(decision_type, timestamp DESC)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_decisions_timestamp "
            "ON decisions(timestamp DESC)"
        )
        cursor.execute(_CREATE_MEMORY)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_memory_agent "
            "ON memory_metrics(agent_id, timestamp DESC)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_memory_type "
            "ON memory_metrics(memory_type, timestamp DESC)"
        )
        cursor.execute(_CREATE_LLM)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_llm_agent "
            "ON llm_metrics(agent_id, timestamp DESC)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_llm_model "
            "ON llm_metrics(model, timestamp DESC)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_llm_decision "
            "ON llm_metrics(decision_id)"
        )
        cursor.execute(_CREATE_CONFLICTS)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_conflicts_session "
            "ON conflicts(session_id, timestamp DESC)"
        )
        self.conn.commit()
        logger.debug("Database schema initialised.")

    def save_decision(self, decision: Decision) -> UUID:
        """Persist a decision record."""
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO decisions (
                    decision_id, agent_id, session_id, timestamp, latency_ms,
                    decision_type, input_data, output_data, reasoning, uncertainties,
                    assumptions, constraints_checked, constraints_violated,
                    confidence, quality_score, parent_decision_id, child_decision_ids,
                    data_sources, memory_operations, llm_calls, total_tokens,
                    total_cost_usd, tags, metadata
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    str(decision.decision_id),
                    decision.agent_id,
                    decision.session_id,
                    decision.timestamp.isoformat(),
                    decision.latency_ms,
                    decision.decision_type.value,
                    serialize_data(decision.input_data),
                    serialize_data(decision.output_data),
                    serialize_data(decision.reasoning),
                    serialize_data(decision.uncertainties),
                    serialize_data(decision.assumptions),
                    serialize_data(decision.constraints_checked),
                    serialize_data(decision.constraints_violated),
                    decision.confidence,
                    decision.quality_score,
                    str(decision.parent_decision_id) if decision.parent_decision_id else None,
                    serialize_data([str(c) for c in decision.child_decision_ids]),
                    serialize_data(decision.data_sources),
                    serialize_data([str(m) for m in decision.memory_operations]),
                    decision.llm_calls,
                    decision.total_tokens,
                    decision.total_cost_usd,
                    serialize_data(decision.tags),
                    serialize_data(decision.metadata),
                ),
            )
            self.conn.commit()
        logger.debug("Decision saved: %s", decision.decision_id)
        return decision.decision_id

    def get_decision(self, decision_id: UUID) -> Decision | None:
        """Return a decision by ID, or ``None``."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM decisions WHERE decision_id = ?",
            (str(decision_id),),
        )
        row = cursor.fetchone()
        return self._row_to_decision(row) if row else None

    def query_decisions(
        self,
        agent_id: str | None = None,
        session_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        decision_type: DecisionType | None = None,
        limit: int = 100,
    ) -> list[Decision]:
        """Return decisions matching the given filters, newest first."""
        sql = "SELECT * FROM decisions WHERE 1=1"
        params: list[str] = []

        if agent_id:
            sql += " AND agent_id = ?"
            params.append(agent_id)
        if session_id:
            sql += " AND session_id = ?"
            params.append(session_id)
        if start_time:
            sql += " AND timestamp >= ?"
            params.append(start_time.isoformat())
        if end_time:
            sql += " AND timestamp <= ?"
            params.append(end_time.isoformat())
        if decision_type:
            sql += " AND decision_type = ?"
            params.append(decision_type.value)

        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(str(limit))

        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        return [self._row_to_decision(row) for row in cursor.fetchall()]

    def save_memory_metrics(self, metrics: MemoryMetrics) -> UUID:
        """Persist a memory-operation record."""
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO memory_metrics (
                    operation_id, agent_id, memory_type, operation, timestamp,
                    latency_ms, items_processed, bytes_processed, vector_dimension,
                    similarity_threshold, top_k, avg_similarity, min_similarity,
                    max_similarity, retrieval_precision, retrieval_recall,
                    time_range_start, time_range_end, episodes_retrieved,
                    temporal_coherence, context_tokens_used, context_tokens_limit,
                    knowledge_graph_nodes, relationships_traversed, max_hop_distance,
                    graph_density, oldest_item_age_hours, average_item_age_hours,
                    cache_hit_rate, metadata
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    str(metrics.operation_id),
                    metrics.agent_id,
                    metrics.memory_type.value,
                    metrics.operation.value,
                    metrics.timestamp.isoformat(),
                    metrics.latency_ms,
                    metrics.items_processed,
                    metrics.bytes_processed,
                    metrics.vector_dimension,
                    metrics.similarity_threshold,
                    metrics.top_k,
                    metrics.avg_similarity,
                    metrics.min_similarity,
                    metrics.max_similarity,
                    metrics.retrieval_precision,
                    metrics.retrieval_recall,
                    metrics.time_range_start.isoformat() if metrics.time_range_start else None,
                    metrics.time_range_end.isoformat() if metrics.time_range_end else None,
                    metrics.episodes_retrieved,
                    metrics.temporal_coherence,
                    metrics.context_tokens_used,
                    metrics.context_tokens_limit,
                    metrics.knowledge_graph_nodes,
                    metrics.relationships_traversed,
                    metrics.max_hop_distance,
                    metrics.graph_density,
                    metrics.oldest_item_age_hours,
                    metrics.average_item_age_hours,
                    metrics.cache_hit_rate,
                    serialize_data(metrics.metadata),
                ),
            )
            self.conn.commit()
        logger.debug("Memory metrics saved: %s", metrics.operation_id)
        return metrics.operation_id

    def save_llm_metrics(self, metrics: LLMMetrics) -> UUID:
        """Persist an LLM-call record."""
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO llm_metrics (
                    call_id, agent_id, decision_id, timestamp, latency_ms,
                    time_to_first_token_ms, provider, model, prompt_tokens,
                    completion_tokens, total_tokens, cost_usd, finish_reason,
                    is_streaming, chunks_received, rate_limited, retry_count,
                    temperature, max_tokens, metadata
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    str(metrics.call_id),
                    metrics.agent_id,
                    str(metrics.decision_id) if metrics.decision_id else None,
                    metrics.timestamp.isoformat(),
                    metrics.latency_ms,
                    metrics.time_to_first_token_ms,
                    metrics.provider,
                    metrics.model,
                    metrics.prompt_tokens,
                    metrics.completion_tokens,
                    metrics.total_tokens,
                    metrics.cost_usd,
                    metrics.finish_reason,
                    1 if metrics.is_streaming else 0,
                    metrics.chunks_received,
                    1 if metrics.rate_limited else 0,
                    metrics.retry_count,
                    metrics.temperature,
                    metrics.max_tokens,
                    serialize_data(metrics.metadata),
                ),
            )
            self.conn.commit()
        logger.debug("LLM metrics saved: %s", metrics.call_id)
        return metrics.call_id

    def save_conflict(self, conflict: AgentConflict) -> UUID:
        """Persist a conflict record."""
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO conflicts (
                    conflict_id, session_id, timestamp, conflict_type,
                    involved_agents, agent_positions, severity, resolution_strategy,
                    resolution_outcome, nash_equilibrium, pareto_optimal,
                    resolved, resolution_time_ms, metadata
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    str(conflict.conflict_id),
                    conflict.session_id,
                    conflict.timestamp.isoformat(),
                    conflict.conflict_type.value,
                    serialize_data(conflict.involved_agents),
                    serialize_data(conflict.agent_positions),
                    conflict.severity,
                    conflict.resolution_strategy,
                    conflict.resolution_outcome,
                    serialize_data(conflict.nash_equilibrium),
                    (
                        1
                        if conflict.pareto_optimal is True
                        else (0 if conflict.pareto_optimal is False else None)
                    ),
                    1 if conflict.resolved else 0,
                    conflict.resolution_time_ms,
                    serialize_data(conflict.metadata),
                ),
            )
            self.conn.commit()
        logger.debug("Conflict saved: %s", conflict.conflict_id)
        return conflict.conflict_id

    def _row_to_decision(self, row: sqlite3.Row) -> Decision:
        return Decision(
            decision_id=UUID(row["decision_id"]),
            agent_id=row["agent_id"],
            session_id=row["session_id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            latency_ms=row["latency_ms"],
            decision_type=DecisionType(row["decision_type"]),
            input_data=deserialize_data(row["input_data"]) if row["input_data"] else {},
            output_data=deserialize_data(row["output_data"]) if row["output_data"] else {},
            reasoning=deserialize_data(row["reasoning"]) if row["reasoning"] else [],
            uncertainties=deserialize_data(row["uncertainties"]) if row["uncertainties"] else [],
            assumptions=deserialize_data(row["assumptions"]) if row["assumptions"] else [],
            constraints_checked=deserialize_data(row["constraints_checked"]) if row["constraints_checked"] else [],
            constraints_violated=deserialize_data(row["constraints_violated"]) if row["constraints_violated"] else [],
            confidence=row["confidence"],
            quality_score=row["quality_score"],
            parent_decision_id=UUID(row["parent_decision_id"]) if row["parent_decision_id"] else None,
            child_decision_ids=[UUID(c) for c in deserialize_data(row["child_decision_ids"])] if row["child_decision_ids"] else [],
            data_sources=deserialize_data(row["data_sources"]) if row["data_sources"] else [],
            memory_operations=[UUID(m) for m in deserialize_data(row["memory_operations"])] if row["memory_operations"] else [],
            llm_calls=row["llm_calls"],
            total_tokens=row["total_tokens"],
            total_cost_usd=row["total_cost_usd"],
            tags=deserialize_data(row["tags"]) if row["tags"] else [],
            metadata=deserialize_data(row["metadata"]) if row["metadata"] else {},
        )

    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()
        logger.info("SQLite connection closed.")

    def __del__(self) -> None:
        if hasattr(self, "conn"):
            with contextlib.suppress(Exception):
                self.conn.close()

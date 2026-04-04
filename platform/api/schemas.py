"""Pydantic response schemas for the Agentability REST API.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared primitives
# ---------------------------------------------------------------------------


class PageMeta(BaseModel):
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Decisions
# ---------------------------------------------------------------------------


class DecisionOut(BaseModel):
    decision_id: UUID
    agent_id: str
    session_id: str | None
    timestamp: datetime
    latency_ms: float | None
    decision_type: str
    confidence: float | None
    quality_score: float | None
    llm_calls: int
    total_tokens: int
    total_cost_usd: float
    reasoning: list[str]
    uncertainties: list[str]
    assumptions: list[str]
    constraints_checked: list[str]
    constraints_violated: list[str]
    data_sources: list[str]
    tags: list[str]
    output_data: dict[str, Any]
    metadata: dict[str, Any]

    model_config = {"from_attributes": True}


class DecisionListOut(BaseModel):
    items: list[DecisionOut]
    meta: PageMeta


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------


class AgentSummaryOut(BaseModel):
    agent_id: str
    total_decisions: int
    avg_confidence: float | None
    avg_latency_ms: float | None
    success_rate: float | None
    total_cost_usd: float
    total_tokens: int
    total_llm_calls: int


class DriftResultOut(BaseModel):
    drift_detected: bool
    severity: str
    agent_id: str
    current_confidence: float | None = None
    baseline_confidence: float | None = None
    drift_magnitude: float | None = None
    current_stddev: float | None = None
    baseline_stddev: float | None = None
    recent_samples: int | None = None
    baseline_samples: int | None = None
    recommendation: str | None = None
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None


# ---------------------------------------------------------------------------
# LLM / Cost
# ---------------------------------------------------------------------------


class LLMCallOut(BaseModel):
    call_id: UUID
    agent_id: str
    decision_id: UUID | None
    timestamp: datetime
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    cost_usd: float
    finish_reason: str | None
    is_streaming: bool

    model_config = {"from_attributes": True}


class CostSummaryOut(BaseModel):
    total_cost_usd: float
    total_tokens: int
    total_calls: int
    by_model: dict[str, float]
    by_provider: dict[str, float]
    cost_per_decision: float


# ---------------------------------------------------------------------------
# Conflicts
# ---------------------------------------------------------------------------


class ConflictOut(BaseModel):
    conflict_id: UUID
    session_id: str
    timestamp: datetime
    conflict_type: str
    involved_agents: list[str]
    severity: float
    resolved: bool
    resolution_strategy: str | None
    resolution_outcome: str | None
    resolution_time_ms: float | None

    model_config = {"from_attributes": True}


class ConflictHotspotOut(BaseModel):
    agents: list[str]
    conflict_count: int
    avg_severity: float
    win_rates: dict[str, float]


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------


class MemoryOpOut(BaseModel):
    operation_id: UUID
    agent_id: str
    memory_type: str
    operation: str
    timestamp: datetime
    latency_ms: float
    items_processed: int
    avg_similarity: float | None
    retrieval_precision: float | None
    retrieval_recall: float | None
    cache_hit_rate: float | None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Health / Meta
# ---------------------------------------------------------------------------


class HealthOut(BaseModel):
    status: str
    version: str
    db_path: str
    total_decisions: int
    total_conflicts: int
    uptime_seconds: float

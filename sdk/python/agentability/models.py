"""Core data models for Agentability.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class DecisionType(str, Enum):
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    GENERATION = "generation"
    RETRIEVAL = "retrieval"
    PLANNING = "planning"
    EXECUTION = "execution"
    DELEGATION = "delegation"
    COORDINATION = "coordination"
    ROUTING = "routing"
    TOOL_SELECTION = "tool_selection"


class MemoryType(str, Enum):
    VECTOR = "vector"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    WORKING = "working"
    PROCEDURAL = "procedural"


class MemoryOperation(str, Enum):
    RETRIEVE = "retrieve"
    STORE = "store"
    UPDATE = "update"
    DELETE = "delete"
    QUERY = "query"


class ConflictType(str, Enum):
    GOAL_CONFLICT = "goal_conflict"
    RESOURCE_CONFLICT = "resource_conflict"
    BELIEF_CONFLICT = "belief_conflict"
    PRIORITY_CONFLICT = "priority_conflict"
    STRATEGY_CONFLICT = "strategy_conflict"


class CapabilityDimension(str, Enum):
    REASONING = "reasoning"
    MEMORY = "memory"
    TOOL_USE = "tool_use"
    AUTONOMY = "autonomy"
    ROBUSTNESS = "robustness"
    SAFETY = "safety"
    EFFICIENCY = "efficiency"
    COLLABORATION = "collaboration"


class PolicyType(str, Enum):
    CONTENT = "content"
    COST = "cost"
    LATENCY = "latency"
    SAFETY = "safety"
    COMPLIANCE = "compliance"


class ViolationSeverity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Decision(BaseModel):
    """A single agent decision with complete provenance."""

    decision_id: UUID = Field(default_factory=uuid4)
    agent_id: str
    session_id: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    latency_ms: float | None = None
    decision_type: DecisionType
    input_data: dict[str, Any] = Field(default_factory=dict)
    output_data: dict[str, Any] = Field(default_factory=dict)
    reasoning: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    constraints_checked: list[str] = Field(default_factory=list)
    constraints_violated: list[str] = Field(default_factory=list)
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    quality_score: float | None = Field(None, ge=0.0, le=1.0)
    parent_decision_id: UUID | None = None
    child_decision_ids: list[UUID] = Field(default_factory=list)
    data_sources: list[str] = Field(default_factory=list)
    memory_operations: list[UUID] = Field(default_factory=list)
    llm_calls: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    total_cost_usd: float = Field(default=0.0, ge=0.0)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {
        "json_encoders": {datetime: lambda v: v.isoformat(), UUID: str}
    }


class MemoryMetrics(BaseModel):
    """Metrics for a memory subsystem operation."""

    operation_id: UUID = Field(default_factory=uuid4)
    agent_id: str
    memory_type: MemoryType
    operation: MemoryOperation
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    latency_ms: float
    items_processed: int = Field(ge=0)
    bytes_processed: int | None = Field(None, ge=0)
    vector_dimension: int | None = Field(None, ge=0)
    similarity_threshold: float | None = Field(None, ge=0.0, le=1.0)
    top_k: int | None = Field(None, ge=1)
    avg_similarity: float | None = Field(None, ge=0.0, le=1.0)
    min_similarity: float | None = Field(None, ge=0.0, le=1.0)
    max_similarity: float | None = Field(None, ge=0.0, le=1.0)
    retrieval_precision: float | None = Field(None, ge=0.0, le=1.0)
    retrieval_recall: float | None = Field(None, ge=0.0, le=1.0)
    time_range_start: datetime | None = None
    time_range_end: datetime | None = None
    episodes_retrieved: int | None = Field(None, ge=0)
    temporal_coherence: float | None = Field(None, ge=0.0, le=1.0)
    context_tokens_used: int | None = Field(None, ge=0)
    context_tokens_limit: int | None = Field(None, ge=0)
    knowledge_graph_nodes: int | None = Field(None, ge=0)
    relationships_traversed: int | None = Field(None, ge=0)
    max_hop_distance: int | None = Field(None, ge=0)
    graph_density: float | None = Field(None, ge=0.0, le=1.0)
    oldest_item_age_hours: float | None = Field(None, ge=0.0)
    average_item_age_hours: float | None = Field(None, ge=0.0)
    cache_hit_rate: float | None = Field(None, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {
        "json_encoders": {datetime: lambda v: v.isoformat(), UUID: str}
    }


class LLMMetrics(BaseModel):
    """Metrics for a single LLM API call."""

    call_id: UUID = Field(default_factory=uuid4)
    agent_id: str
    decision_id: UUID | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    latency_ms: float
    time_to_first_token_ms: float | None = None
    provider: str
    model: str
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    cost_usd: float = Field(ge=0.0)
    finish_reason: str | None = None
    is_streaming: bool = False
    chunks_received: int | None = Field(None, ge=0)
    rate_limited: bool = False
    retry_count: int = Field(default=0, ge=0)
    temperature: float | None = None
    max_tokens: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {
        "json_encoders": {datetime: lambda v: v.isoformat(), UUID: str}
    }


class AgentConflict(BaseModel):
    """A recorded multi-agent conflict event."""

    conflict_id: UUID = Field(default_factory=uuid4)
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    conflict_type: ConflictType
    involved_agents: list[str] = Field(min_length=2)
    agent_positions: dict[str, dict[str, Any]]
    severity: float = Field(ge=0.0, le=1.0)
    resolution_strategy: str | None = None
    resolution_outcome: str | None = None
    nash_equilibrium: dict[str, Any] | None = None
    pareto_optimal: bool | None = None
    resolved: bool = False
    resolution_time_ms: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {
        "json_encoders": {datetime: lambda v: v.isoformat(), UUID: str}
    }


class AgentMetrics(BaseModel):
    """Aggregate metrics for one agent over a time window."""

    agent_id: str
    time_window_start: datetime
    time_window_end: datetime
    total_decisions: int = Field(default=0, ge=0)
    avg_confidence: float | None = Field(None, ge=0.0, le=1.0)
    avg_latency_ms: float | None = Field(None, ge=0.0)
    success_rate: float | None = Field(None, ge=0.0, le=1.0)
    avg_quality_score: float | None = Field(None, ge=0.0, le=1.0)
    total_llm_calls: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    total_cost_usd: float = Field(default=0.0, ge=0.0)
    total_memory_operations: int = Field(default=0, ge=0)
    avg_memory_latency_ms: float | None = Field(None, ge=0.0)
    conflicts_initiated: int = Field(default=0, ge=0)
    conflicts_involved: int = Field(default=0, ge=0)

    model_config = {"json_encoders": {datetime: lambda v: v.isoformat()}}


class CausalRelationship(BaseModel):
    """A directed causal link between two decisions."""

    source_decision_id: UUID
    target_decision_id: UUID
    relationship_type: str
    strength: float = Field(ge=0.0, le=1.0)
    time_delta_ms: float
    evidence: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)

    model_config = {"json_encoders": {UUID: str}}


class CapabilityScore(BaseModel):
    """Score for a single capability dimension."""

    dimension: CapabilityDimension
    score: float = Field(ge=0.0, le=100.0)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_count: int = Field(ge=0)


class PolicyViolation(BaseModel):
    """A single policy rule violation."""

    rule_id: str
    rule_description: str
    severity: ViolationSeverity
    agent_id: str
    decision_id: UUID | None = None
    violation_details: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "json_encoders": {datetime: lambda v: v.isoformat(), UUID: str}
    }


class VersionSnapshot(BaseModel):
    """Complete version state at decision time."""

    snapshot_id: UUID = Field(default_factory=uuid4)
    model_name: str
    model_version: str
    model_hash: str | None = None
    prompt_template: str
    prompt_hash: str
    prompt_variables: dict[str, Any] = Field(default_factory=dict)
    tools_available: list[str] = Field(default_factory=list)
    tool_versions: dict[str, str] = Field(default_factory=dict)
    system_config: dict[str, Any] = Field(default_factory=dict)
    dataset_version: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "json_encoders": {datetime: lambda v: v.isoformat(), UUID: str}
    }

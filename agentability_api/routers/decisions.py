"""Decisions router — full implementation wired to SQLiteStore.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from agentability.models import DecisionType
from agentability.storage.sqlite_store import SQLiteStore

from ..dependencies import get_store
from ..schemas import DecisionListOut, DecisionOut, PageMeta

router = APIRouter(prefix="/api/decisions", tags=["decisions"])

Store = Annotated[SQLiteStore, Depends(get_store)]


def _decision_to_out(d: object) -> DecisionOut:
    return DecisionOut(
        decision_id=d.decision_id,  # type: ignore[attr-defined]
        agent_id=d.agent_id,  # type: ignore[attr-defined]
        session_id=d.session_id,  # type: ignore[attr-defined]
        timestamp=d.timestamp,  # type: ignore[attr-defined]
        latency_ms=d.latency_ms,  # type: ignore[attr-defined]
        decision_type=d.decision_type.value,  # type: ignore[attr-defined]
        confidence=d.confidence,  # type: ignore[attr-defined]
        quality_score=d.quality_score,  # type: ignore[attr-defined]
        llm_calls=d.llm_calls,  # type: ignore[attr-defined]
        total_tokens=d.total_tokens,  # type: ignore[attr-defined]
        total_cost_usd=d.total_cost_usd,  # type: ignore[attr-defined]
        reasoning=d.reasoning,  # type: ignore[attr-defined]
        uncertainties=d.uncertainties,  # type: ignore[attr-defined]
        assumptions=d.assumptions,  # type: ignore[attr-defined]
        constraints_checked=d.constraints_checked,  # type: ignore[attr-defined]
        constraints_violated=d.constraints_violated,  # type: ignore[attr-defined]
        data_sources=d.data_sources,  # type: ignore[attr-defined]
        tags=d.tags,  # type: ignore[attr-defined]
        output_data=d.output_data,  # type: ignore[attr-defined]
        metadata=d.metadata,  # type: ignore[attr-defined]
    )


@router.get("", response_model=DecisionListOut)
async def list_decisions(
    store: Store,
    agent_id: str | None = Query(None),
    session_id: str | None = Query(None),
    decision_type: str | None = Query(None),
    start_time: datetime | None = Query(None),
    end_time: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> DecisionListOut:
    """List decisions with filtering, pagination, newest first."""
    dt = DecisionType(decision_type) if decision_type else None
    decisions = store.query_decisions(
        agent_id=agent_id,
        session_id=session_id,
        start_time=start_time,
        end_time=end_time,
        decision_type=dt,
        limit=limit + offset,
    )
    page = decisions[offset : offset + limit]
    return DecisionListOut(
        items=[_decision_to_out(d) for d in page],
        meta=PageMeta(total=len(decisions), limit=limit, offset=offset),
    )


@router.get("/{decision_id}", response_model=DecisionOut)
async def get_decision(decision_id: UUID, store: Store) -> DecisionOut:
    """Get a single decision by UUID."""
    d = store.get_decision(decision_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    return _decision_to_out(d)


@router.get("/{decision_id}/reasoning")
async def get_reasoning(decision_id: UUID, store: Store) -> dict:
    """Return the reasoning chain, uncertainties, and assumptions."""
    d = store.get_decision(decision_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    return {
        "decision_id": str(decision_id),
        "agent_id": d.agent_id,
        "confidence": d.confidence,
        "reasoning": d.reasoning,
        "uncertainties": d.uncertainties,
        "assumptions": d.assumptions,
        "constraints_checked": d.constraints_checked,
        "constraints_violated": d.constraints_violated,
        "data_sources": d.data_sources,
    }

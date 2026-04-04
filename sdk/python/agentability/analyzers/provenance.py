"""Decision provenance analyser — answers "WHY did this happen?"

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ProvenanceType(Enum):
    """Types of provenance relationships."""

    INPUT_DATA = "input_data"
    REASONING_STEP = "reasoning_step"
    MEMORY_RETRIEVAL = "memory_retrieval"
    TOOL_CALL = "tool_call"
    CONSTRAINT = "constraint"
    DEPENDENCY = "dependency"
    ASSUMPTION = "assumption"
    UNCERTAINTY = "uncertainty"


@dataclass
class ProvenanceRecord:
    """A single provenance record tracking one influence on a decision."""

    record_id: str
    provenance_type: ProvenanceType
    source: str
    content: Any
    confidence: float
    timestamp: datetime
    impact: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionProvenance:
    """Complete provenance for a single decision."""

    decision_id: str
    agent_id: str
    output: Any
    output_confidence: float
    records: list[ProvenanceRecord] = field(default_factory=list)
    critical_points: list[dict[str, Any]] = field(default_factory=list)
    alternatives_considered: list[dict[str, Any]] = field(default_factory=list)
    bottleneck_records: list[str] = field(default_factory=list)


class ProvenanceAnalyzer:
    """Analyse decision provenance to answer "WHY did this happen?"

    Example:
        >>> analyzer = ProvenanceAnalyzer()
        >>> analyzer.create_provenance("dec_1", "risk_agent", {"decision": "DENY"}, 0.42)
        >>> analyzer.add_record("dec_1", "input_data", "income_api",
        ...                     {"income": 75000}, confidence=0.50, impact=0.9)
        >>> explanation = analyzer.explain_decision("dec_1")
    """

    def __init__(self) -> None:
        self._provenances: dict[str, DecisionProvenance] = {}

    @property
    def provenances(self) -> dict[str, DecisionProvenance]:
        return self._provenances

    def create_provenance(
        self,
        decision_id: str,
        agent_id: str,
        output: Any,
        output_confidence: float,
    ) -> DecisionProvenance:
        """Create and register provenance for a decision."""
        prov = DecisionProvenance(
            decision_id=decision_id,
            agent_id=agent_id,
            output=output,
            output_confidence=output_confidence,
        )
        self._provenances[decision_id] = prov
        return prov

    def add_record(
        self,
        decision_id: str,
        provenance_type: str,
        source: str,
        content: Any,
        confidence: float,
        impact: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ProvenanceRecord | None:
        """Add a provenance record to an existing decision."""
        if decision_id not in self._provenances:
            return None
        prov = self._provenances[decision_id]
        record = ProvenanceRecord(
            record_id=f"{decision_id}_rec_{len(prov.records)}",
            provenance_type=ProvenanceType(provenance_type),
            source=source,
            content=content,
            confidence=confidence,
            timestamp=datetime.now(),
            impact=impact,
            metadata=metadata or {},
        )
        prov.records.append(record)
        return record

    def get_provenance(self, decision_id: str) -> DecisionProvenance | None:
        """Return provenance for *decision_id*, or ``None``."""
        return self._provenances.get(decision_id)

    def explain_decision(self, decision_id: str) -> dict[str, Any]:
        """Generate a human-readable explanation of a decision."""
        prov = self._provenances.get(decision_id)
        if not prov:
            return {"error": "Decision not found"}

        bottlenecks = self._identify_bottlenecks(prov)
        critical_points = self._identify_critical_points(prov)
        summary = self._generate_summary(prov, bottlenecks)
        timeline = sorted(prov.records, key=lambda r: r.timestamp)

        return {
            "summary": summary,
            "decision": prov.output,
            "confidence": prov.output_confidence,
            "agent_id": prov.agent_id,
            "critical_points": critical_points,
            "bottlenecks": bottlenecks,
            "alternatives": prov.alternatives_considered,
            "timeline": [
                {
                    "type": rec.provenance_type.value,
                    "source": rec.source,
                    "content": str(rec.content)[:200],
                    "confidence": rec.confidence,
                    "impact": rec.impact,
                    "timestamp": rec.timestamp.isoformat(),
                }
                for rec in timeline
            ],
        }

    def find_confidence_bottleneck(
        self, decision_id: str
    ) -> dict[str, Any] | None:
        """Return the main confidence bottleneck, or ``None``."""
        prov = self._provenances.get(decision_id)
        if not prov or prov.output_confidence >= 0.7:
            return None

        bottleneck: ProvenanceRecord | None = None
        min_score = 1.0
        for record in prov.records:
            if (
                record.impact is not None
                and record.impact >= 0.5
                and record.confidence < min_score
            ):
                min_score = record.confidence
                bottleneck = record

        if bottleneck is None:
            return None

        return {
            "type": bottleneck.provenance_type.value,
            "source": bottleneck.source,
            "content": bottleneck.content,
            "confidence": bottleneck.confidence,
            "impact": bottleneck.impact,
            "explanation": self._explain_bottleneck(bottleneck),
        }

    def trace_information_lineage(
        self, decision_id: str, information_key: str
    ) -> list[dict[str, Any]]:
        """Trace how *information_key* flowed through a decision."""
        prov = self._provenances.get(decision_id)
        if not prov:
            return []

        flow: list[dict[str, Any]] = []
        for record in prov.records:
            if isinstance(record.content, dict) and information_key in record.content:
                flow.append(
                    {
                        "type": record.provenance_type.value,
                        "source": record.source,
                        "value": record.content[information_key],
                        "confidence": record.confidence,
                        "timestamp": record.timestamp.isoformat(),
                    }
                )
            elif information_key.lower() in str(record.content).lower():
                flow.append(
                    {
                        "type": record.provenance_type.value,
                        "source": record.source,
                        "mention": str(record.content)[:200],
                        "confidence": record.confidence,
                        "timestamp": record.timestamp.isoformat(),
                    }
                )
        return flow

    def trace_information_flow(
        self, decision_id: str, information_key: str
    ) -> list[dict[str, Any]]:
        """Alias for :meth:`trace_information_lineage`."""
        return self.trace_information_lineage(decision_id, information_key)

    def compare_decisions(
        self, decision_id_1: str, decision_id_2: str
    ) -> dict[str, Any]:
        """Diff the provenance of two decisions."""
        prov1 = self._provenances.get(decision_id_1)
        prov2 = self._provenances.get(decision_id_2)
        if not prov1 or not prov2:
            return {"error": "One or both decisions not found"}

        types1 = {r.provenance_type for r in prov1.records}
        types2 = {r.provenance_type for r in prov2.records}
        sources1 = {r.source for r in prov1.records}
        sources2 = {r.source for r in prov2.records}

        return {
            "decision_1": {
                "id": decision_id_1,
                "output": prov1.output,
                "confidence": prov1.output_confidence,
            },
            "decision_2": {
                "id": decision_id_2,
                "output": prov2.output,
                "confidence": prov2.output_confidence,
            },
            "differences": {
                "provenance_types_only_in_1": [t.value for t in types1 - types2],
                "provenance_types_only_in_2": [t.value for t in types2 - types1],
                "sources_only_in_1": list(sources1 - sources2),
                "sources_only_in_2": list(sources2 - sources1),
                "confidence_delta": prov2.output_confidence - prov1.output_confidence,
            },
        }

    def get_dependency_chain(self, decision_id: str) -> list[str]:
        """Return decision IDs this decision depends on."""
        prov = self._provenances.get(decision_id)
        if not prov:
            return []
        deps: list[str] = []
        for record in prov.records:
            if record.provenance_type == ProvenanceType.DEPENDENCY:
                if isinstance(record.content, str):
                    deps.append(record.content)
                elif (
                    isinstance(record.content, dict)
                    and "decision_id" in record.content
                ):
                    deps.append(str(record.content["decision_id"]))
        return deps

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _identify_bottlenecks(
        self, prov: DecisionProvenance
    ) -> list[dict[str, Any]]:
        bottlenecks: list[dict[str, Any]] = []
        for record in prov.records:
            if (
                record.confidence < 0.6
                and record.impact is not None
                and record.impact >= 0.5
            ):
                bottlenecks.append(
                    {
                        "type": record.provenance_type.value,
                        "source": record.source,
                        "confidence": record.confidence,
                        "impact": record.impact,
                        "content": str(record.content)[:200],
                    }
                )
        bottlenecks.sort(
            key=lambda b: float(b["impact"]) * (1.0 - float(b["confidence"])),
            reverse=True,
        )
        return bottlenecks

    def _identify_critical_points(
        self, prov: DecisionProvenance
    ) -> list[dict[str, Any]]:
        critical: list[dict[str, Any]] = []
        for record in prov.records:
            if record.impact is not None and record.impact >= 0.7:
                critical.append(
                    {
                        "type": record.provenance_type.value,
                        "source": record.source,
                        "confidence": record.confidence,
                        "impact": record.impact,
                        "content": str(record.content)[:200],
                    }
                )
        critical.sort(key=lambda c: float(c["impact"]), reverse=True)
        return critical

    def _generate_summary(
        self,
        prov: DecisionProvenance,
        bottlenecks: list[dict[str, Any]],
    ) -> str:
        output_str = str(prov.output)[:50]
        if prov.output_confidence >= 0.8:
            return (
                f"Decision: {output_str}. "
                f"High confidence ({prov.output_confidence:.0%})"
            )
        if bottlenecks:
            bn = bottlenecks[0]
            return (
                f"Decision: {output_str}. "
                f"Confidence reduced to {prov.output_confidence:.0%} due to "
                f"{bn['source']} ({float(bn['confidence']):.0%} confidence)"
            )
        return f"Decision: {output_str}. Confidence: {prov.output_confidence:.0%}"

    def _explain_bottleneck(self, record: ProvenanceRecord) -> str:
        impact_str = f"{record.impact:.0%}" if record.impact is not None else "unknown"
        return (
            f"This {record.provenance_type.value} from {record.source} had "
            f"low confidence ({record.confidence:.0%}) but high impact "
            f"({impact_str}), limiting overall decision confidence."
        )

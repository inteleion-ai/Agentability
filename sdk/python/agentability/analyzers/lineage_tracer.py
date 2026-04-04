"""Information lineage tracing.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class InformationLineage:
    """A recorded lineage path for a piece of information."""

    lineage_id: str
    source: str
    destination: str
    path: list[str]
    transformations: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


class LineageTracer:
    """Trace information lineage through an agent system."""

    def __init__(self) -> None:
        self._lineages: list[InformationLineage] = []
        self._graph: dict[str, set[str]] = {}

    def record_lineage(
        self,
        source: str,
        destination: str,
        path: list[str],
        transformations: list[str] | None = None,
    ) -> InformationLineage:
        """Record a lineage path."""
        lineage = InformationLineage(
            lineage_id=f"lineage_{len(self._lineages)}",
            source=source,
            destination=destination,
            path=path,
            transformations=transformations or [],
        )
        self._lineages.append(lineage)
        for i in range(len(path) - 1):
            self._graph.setdefault(path[i], set()).add(path[i + 1])
        return lineage

    def trace_back(self, destination: str) -> list[InformationLineage]:
        """Return all lineages ending at *destination*."""
        return [rec for rec in self._lineages if rec.destination == destination]

    def trace_forward(self, source: str) -> list[InformationLineage]:
        """Return all lineages originating from *source*."""
        return [rec for rec in self._lineages if rec.source == source]

    def get_all_sources_for(self, destination: str) -> list[str]:
        """Return unique source nodes for *destination*."""
        return list({rec.source for rec in self.trace_back(destination)})

    @property
    def lineages(self) -> list[InformationLineage]:
        return list(self._lineages)

"""Causal graph builder for temporal causality analysis.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class CausalRelationType(Enum):
    """Types of causal relationships between decisions."""

    DIRECT = "direct"
    INDIRECT = "indirect"
    CONTRIBUTORY = "contributory"
    PREVENTIVE = "preventive"
    CORRELATION = "correlation"


@dataclass
class CausalNode:
    """A node in the causal graph."""

    node_id: str
    node_type: str
    label: str
    timestamp: datetime
    agent_id: str | None = None
    confidence: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CausalEdge:
    """A directed causal relationship between two nodes."""

    edge_id: str
    source_id: str
    target_id: str
    relation_type: CausalRelationType
    strength: float
    time_delta_seconds: float
    confidence: float
    evidence: list[str] = field(default_factory=list)
    mechanism: str | None = None


class CausalGraphBuilder:
    """Build and analyse temporal causal graphs for agent decisions.

    Example:
        >>> builder = CausalGraphBuilder()
        >>> builder.add_node("dec_001", "decision", "Risk Assessment",
        ...                  confidence=0.42)
        >>> builder.add_node("dec_002", "decision", "Loan Approval",
        ...                  confidence=0.85)
        >>> builder.add_causal_edge("dec_001", "dec_002", "direct",
        ...                         strength=0.9)
        >>> bottlenecks = builder.find_bottlenecks()
    """

    def __init__(self) -> None:
        self.nodes: dict[str, CausalNode] = {}
        self.edges: list[CausalEdge] = []
        self._adjacency: dict[str, list[str]] = {}
        self._reverse_adjacency: dict[str, list[str]] = {}
        # O(1) edge lookup keyed by (source_id, target_id) — fixes O(n) scan
        self._edge_index: dict[tuple[str, str], CausalEdge] = {}

    def add_node(
        self,
        node_id: str,
        node_type: str,
        label: str,
        timestamp: datetime | None = None,
        agent_id: str | None = None,
        confidence: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CausalNode:
        """Add a node to the graph and return it."""
        node = CausalNode(
            node_id=node_id,
            node_type=node_type,
            label=label,
            timestamp=timestamp or datetime.now(),
            agent_id=agent_id,
            confidence=confidence,
            metadata=metadata or {},
        )
        self.nodes[node_id] = node
        self._adjacency[node_id] = []
        self._reverse_adjacency[node_id] = []
        return node

    def add_causal_edge(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        strength: float,
        confidence: float = 1.0,
        evidence: list[str] | None = None,
        mechanism: str | None = None,
    ) -> CausalEdge | None:
        """Add a causal edge between two existing nodes."""
        if source_id not in self.nodes or target_id not in self.nodes:
            return None

        time_delta = (
            self.nodes[target_id].timestamp - self.nodes[source_id].timestamp
        ).total_seconds()

        edge = CausalEdge(
            edge_id=f"{source_id}_to_{target_id}",
            source_id=source_id,
            target_id=target_id,
            relation_type=CausalRelationType(relation_type),
            strength=strength,
            time_delta_seconds=time_delta,
            confidence=confidence,
            evidence=evidence or [],
            mechanism=mechanism,
        )
        self.edges.append(edge)
        self._adjacency[source_id].append(target_id)
        self._reverse_adjacency[target_id].append(source_id)
        self._edge_index[(source_id, target_id)] = edge  # O(1) lookup
        return edge

    def get_causal_chain(
        self,
        from_node_id: str,
        to_node_id: str,
        max_depth: int = 10,
    ) -> list[list[str]]:
        """Return all paths from *from_node_id* to *to_node_id*."""
        paths: list[list[str]] = []

        def _dfs(
            current: str,
            target: str,
            path: list[str],
            visited: set[str],
            depth: int,
        ) -> None:
            if depth > max_depth:
                return
            if current == target:
                paths.append(path.copy())
                return
            visited.add(current)
            for neighbour in self._adjacency.get(current, []):
                if neighbour not in visited:
                    path.append(neighbour)
                    _dfs(neighbour, target, path, visited, depth + 1)
                    path.pop()
            visited.remove(current)

        _dfs(from_node_id, to_node_id, [from_node_id], set(), 0)
        return paths

    def get_root_causes(self, node_id: str) -> list[str]:
        """Return root-cause node IDs for *node_id* (nodes with no parents)."""
        root_causes: list[str] = []
        visited: set[str] = set()

        def _find(current: str) -> None:
            if current in visited:
                return
            visited.add(current)
            sources = self._reverse_adjacency.get(current, [])
            if not sources:
                root_causes.append(current)
            else:
                for src in sources:
                    _find(src)

        _find(node_id)
        return root_causes

    def get_downstream_effects(
        self, node_id: str, max_depth: int = 10
    ) -> list[str]:
        """Return all node IDs causally downstream of *node_id*."""
        affected: set[str] = set()

        def _dfs(current: str, depth: int) -> None:
            if depth >= max_depth:
                return
            for target in self._adjacency.get(current, []):
                if target not in affected:
                    affected.add(target)
                    _dfs(target, depth + 1)

        _dfs(node_id, 0)
        return list(affected)

    def find_bottlenecks(self) -> list[dict[str, Any]]:
        """Identify low-confidence nodes with high downstream impact."""
        bottlenecks: list[dict[str, Any]] = []
        for node_id, node in self.nodes.items():
            if node.confidence is None or node.confidence >= 0.5:
                continue
            affected = self.get_downstream_effects(node_id)
            if len(affected) >= 2:
                bottlenecks.append(
                    {
                        "node_id": node_id,
                        "label": node.label,
                        "confidence": node.confidence,
                        "affected_count": len(affected),
                        "affected_nodes": affected,
                        "agent_id": node.agent_id,
                        "impact": "high" if len(affected) >= 5 else "medium",
                    }
                )
        bottlenecks.sort(
            key=lambda b: b["affected_count"] * (1 - float(b["confidence"])),
            reverse=True,
        )
        return bottlenecks

    def analyze_causal_strength(
        self, from_node_id: str, to_node_id: str
    ) -> dict[str, Any]:
        """Analyse causal strength between two nodes."""
        paths = self.get_causal_chain(from_node_id, to_node_id)
        if not paths:
            return {
                "has_causal_relationship": False,
                "paths_count": 0,
                "strongest_path_strength": 0.0,
                "average_path_strength": 0.0,
            }

        path_strengths: list[float] = []
        path_details: list[dict[str, Any]] = []

        for path in paths:
            path_strength = 1.0
            path_edges: list[dict[str, Any]] = []
            for i in range(len(path) - 1):
                edge = self._get_edge(path[i], path[i + 1])
                if edge:
                    path_strength *= edge.strength
                    path_edges.append(
                        {
                            "from": path[i],
                            "to": path[i + 1],
                            "strength": edge.strength,
                            "mechanism": edge.mechanism,
                        }
                    )
            path_strengths.append(path_strength)
            path_details.append(
                {"path": path, "strength": path_strength, "edges": path_edges}
            )

        return {
            "has_causal_relationship": True,
            "paths_count": len(paths),
            "strongest_path_strength": max(path_strengths),
            "average_path_strength": sum(path_strengths) / len(path_strengths),
            "paths": path_details,
        }

    def detect_causal_loops(self) -> list[list[str]]:
        """Return all feedback loops in the graph."""
        loops: list[list[str]] = []
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def _dfs(node: str, path: list[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            for neighbour in self._adjacency.get(node, []):
                if neighbour not in visited:
                    _dfs(neighbour, path)
                elif neighbour in rec_stack:
                    loop_start = path.index(neighbour)
                    loops.append(path[loop_start:])
            path.pop()
            rec_stack.remove(node)

        for node_id in self.nodes:
            if node_id not in visited:
                _dfs(node_id, [])
        return loops

    def get_temporal_analysis(self) -> dict[str, Any]:
        """Return temporal statistics over all edges."""
        deltas = [e.time_delta_seconds for e in self.edges]
        if not deltas:
            return {}
        return {
            "total_edges": len(deltas),
            "avg_time_delta_seconds": sum(deltas) / len(deltas),
            "min_time_delta_seconds": min(deltas),
            "max_time_delta_seconds": max(deltas),
            "instant_causations": sum(1 for d in deltas if d < 1.0),
            "delayed_causations": sum(1 for d in deltas if d >= 60.0),
            "median_time_delta_seconds": sorted(deltas)[len(deltas) // 2],
        }

    def build_graph(self) -> dict[str, Any]:
        """Return a D3.js-compatible graph dictionary."""
        return {
            "nodes": [
                {
                    "id": n.node_id,
                    "type": n.node_type,
                    "label": n.label,
                    "timestamp": n.timestamp.isoformat(),
                    "agent_id": n.agent_id,
                    "confidence": n.confidence,
                    "metadata": n.metadata,
                }
                for n in self.nodes.values()
            ],
            "edges": [
                {
                    "id": e.edge_id,
                    "source": e.source_id,
                    "target": e.target_id,
                    "type": e.relation_type.value,
                    "strength": e.strength,
                    "confidence": e.confidence,
                    "time_delta": e.time_delta_seconds,
                    "mechanism": e.mechanism,
                    "evidence": e.evidence,
                }
                for e in self.edges
            ],
            "metadata": {
                "total_nodes": len(self.nodes),
                "total_edges": len(self.edges),
                "temporal_stats": self.get_temporal_analysis(),
            },
        }

    def export_to_json(self, filepath: str) -> None:
        """Export graph to a JSON file."""
        with open(filepath, "w") as fh:
            json.dump(self.build_graph(), fh, indent=2, default=str)

    def _get_edge(self, source_id: str, target_id: str) -> CausalEdge | None:
        """O(1) edge lookup via pre-built index."""
        return self._edge_index.get((source_id, target_id))

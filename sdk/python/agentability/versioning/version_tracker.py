"""Version tracking system for root-cause analysis.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import hashlib
from typing import Any

from agentability.models import VersionSnapshot


class VersionTracker:
    """Track all versions that affect agent behaviour."""

    def __init__(self) -> None:
        self._snapshots: dict[str, VersionSnapshot] = {}

    def capture_snapshot(
        self,
        model_name: str,
        model_version: str,
        prompt_template: str,
        prompt_variables: dict[str, Any],
        tools_available: list[str],
        tool_versions: dict[str, str],
        system_config: dict[str, Any],
        model_hash: str | None = None,
        dataset_version: str | None = None,
    ) -> VersionSnapshot:
        """Capture a version snapshot at the current point in time."""
        prompt_hash = hashlib.sha256(
            prompt_template.encode("utf-8")
        ).hexdigest()[:16]
        snapshot = VersionSnapshot(
            model_name=model_name,
            model_version=model_version,
            model_hash=model_hash,
            prompt_template=prompt_template,
            prompt_hash=prompt_hash,
            prompt_variables=prompt_variables,
            tools_available=tools_available,
            tool_versions=tool_versions,
            system_config=system_config,
            dataset_version=dataset_version,
        )
        self._snapshots[str(snapshot.snapshot_id)] = snapshot
        return snapshot

    def compare_snapshots(
        self, snapshot_id_1: str, snapshot_id_2: str
    ) -> dict[str, Any]:
        """Return a diff of two snapshots."""
        snap1 = self._snapshots.get(snapshot_id_1)
        snap2 = self._snapshots.get(snapshot_id_2)
        if snap1 is None or snap2 is None:
            return {"error": "Snapshot not found"}

        differences: dict[str, Any] = {}
        if snap1.model_version != snap2.model_version:
            differences["model_version"] = {
                "old": snap1.model_version, "new": snap2.model_version
            }
        if snap1.prompt_hash != snap2.prompt_hash:
            differences["prompt"] = {
                "changed": True,
                "old_hash": snap1.prompt_hash,
                "new_hash": snap2.prompt_hash,
            }
        old_tools = set(snap1.tools_available)
        new_tools = set(snap2.tools_available)
        added = new_tools - old_tools
        removed = old_tools - new_tools
        if added or removed:
            differences["tools"] = {
                "added": sorted(added), "removed": sorted(removed)
            }
        tool_ver_changes: dict[str, Any] = {}
        for tool in old_tools & new_tools:
            ov = snap1.tool_versions.get(tool)
            nv = snap2.tool_versions.get(tool)
            if ov != nv:
                tool_ver_changes[tool] = {"old": ov, "new": nv}
        if tool_ver_changes:
            differences["tool_versions"] = tool_ver_changes
        return differences

    def get_snapshot(self, snapshot_id: str) -> VersionSnapshot | None:
        """Return a snapshot by ID."""
        return self._snapshots.get(snapshot_id)

    def list_snapshots(self) -> list[VersionSnapshot]:
        """Return all snapshots, newest first."""
        return sorted(
            self._snapshots.values(), key=lambda s: s.timestamp, reverse=True
        )

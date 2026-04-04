"""Data serialisation utilities.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID


class _AgentabilityJSONEncoder(json.JSONEncoder):
    """JSON encoder that handles ``datetime``, ``UUID``, and Pydantic models."""

    def default(self, obj: Any) -> Any:  # noqa: ANN401
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, UUID):
            return str(obj)
        # Pydantic v2
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        # Pydantic v1 fallback
        if hasattr(obj, "dict"):
            return obj.dict()
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        return super().default(obj)


def serialize_data(data: Any) -> str:
    """Serialise *data* to a JSON string.

    Handles ``datetime``, ``UUID``, and Pydantic models transparently.

    Args:
        data: Any JSON-serialisable value (including nested Pydantic models).

    Returns:
        A compact JSON string.
    """
    return json.dumps(data, cls=_AgentabilityJSONEncoder)


def deserialize_data(json_str: str) -> Any:
    """Deserialise a JSON string back to a Python object.

    Args:
        json_str: A valid JSON string.

    Returns:
        The deserialised Python object (dict, list, str, int, float, etc.).
    """
    return json.loads(json_str)


def safe_json_dumps(data: Any) -> str:
    """Serialise *data* to JSON, returning an error envelope on failure.

    Designed for use in storage code where serialisation must never raise.

    Args:
        data: Value to serialise.

    Returns:
        A JSON string. If serialisation fails, returns a JSON object
        describing the error rather than raising an exception.
    """
    try:
        return serialize_data(data)
    except (TypeError, ValueError) as exc:
        return json.dumps(
            {
                "error": "serialisation_failed",
                "message": str(exc),
                "data_type": type(data).__name__,
            }
        )

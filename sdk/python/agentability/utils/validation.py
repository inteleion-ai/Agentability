"""Input validation helpers.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from uuid import UUID


def validate_uuid(value: object) -> UUID:
    """Parse *value* as a UUID, raising ``ValueError`` on bad input."""
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(f"Invalid UUID: {value!r}") from exc


def validate_float_range(
    value: float,
    min_value: float | None = None,
    max_value: float | None = None,
    name: str = "value",
) -> float:
    """Assert *value* is in [*min_value*, *max_value*]."""
    if min_value is not None and value < min_value:
        raise ValueError(f"{name} must be >= {min_value}, got {value}")
    if max_value is not None and value > max_value:
        raise ValueError(f"{name} must be <= {max_value}, got {value}")
    return value


def validate_positive_int(value: int, name: str = "value") -> int:
    """Assert *value* is non-negative."""
    if value < 0:
        raise ValueError(f"{name} must be >= 0, got {value}")
    return value


def validate_non_empty_string(value: str, name: str = "value") -> str:
    """Assert *value* is a non-empty, non-whitespace-only string."""
    if not value or not value.strip():
        raise ValueError(f"{name} must be a non-empty string, got {value!r}")
    return value

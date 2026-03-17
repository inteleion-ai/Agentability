"""Tests for utility modules: serialization and validation.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

import pytest

from agentability.utils.serialization import (
    _AgentabilityJSONEncoder,
    deserialize_data,
    safe_json_dumps,
    serialize_data,
)
from agentability.utils.validation import (
    validate_float_range,
    validate_non_empty_string,
    validate_positive_int,
    validate_uuid,
)


# ===========================================================================
# serialization
# ===========================================================================


class TestSerializeData:
    def test_plain_dict(self) -> None:
        result = serialize_data({"a": 1, "b": "two"})
        assert '"a": 1' in result
        assert '"b": "two"' in result

    def test_list(self) -> None:
        result = serialize_data([1, 2, 3])
        assert result == "[1, 2, 3]"

    def test_datetime_is_isoformat(self) -> None:
        dt = datetime(2026, 3, 17, 12, 0, 0)
        result = serialize_data({"ts": dt})
        assert "2026-03-17T12:00:00" in result

    def test_uuid_is_string(self) -> None:
        uid = UUID("12345678-1234-5678-1234-567812345678")
        result = serialize_data({"id": uid})
        assert "12345678-1234-5678-1234-567812345678" in result

    def test_none_serializes(self) -> None:
        assert serialize_data(None) == "null"

    def test_nested_structure(self) -> None:
        data = {"items": [{"id": uuid4(), "ts": datetime.now()}]}
        result = serialize_data(data)
        assert "items" in result

    def test_pydantic_v2_model(self) -> None:
        from agentability.models import Decision, DecisionType

        d = Decision(agent_id="a", decision_type=DecisionType.CLASSIFICATION)
        result = serialize_data(d)
        assert "agent_id" in result

    def test_object_with_dict_attr(self) -> None:
        class SimpleObj:
            def __init__(self) -> None:
                self.x = 42

        result = serialize_data(SimpleObj())
        assert "42" in result


class TestDeserializeData:
    def test_dict_round_trip(self) -> None:
        original = {"a": 1, "b": [1, 2, 3]}
        assert deserialize_data(serialize_data(original)) == original

    def test_list_round_trip(self) -> None:
        original = ["x", "y", "z"]
        assert deserialize_data(serialize_data(original)) == original

    def test_none_round_trip(self) -> None:
        assert deserialize_data("null") is None

    def test_string_round_trip(self) -> None:
        assert deserialize_data('"hello"') == "hello"

    def test_number_round_trip(self) -> None:
        assert deserialize_data("3.14") == pytest.approx(3.14)


class TestSafeJsonDumps:
    def test_normal_data_works(self) -> None:
        result = safe_json_dumps({"key": "value"})
        assert "key" in result

    def test_unserializable_returns_error_envelope(self) -> None:
        class Unserializable:
            pass

        result = safe_json_dumps(Unserializable())
        import json

        parsed = json.loads(result)
        # Either an error envelope or fell back via __dict__
        assert isinstance(parsed, dict)

    def test_datetime_works(self) -> None:
        result = safe_json_dumps({"ts": datetime(2026, 1, 1)})
        assert "2026" in result


class TestAgentabilityJSONEncoder:
    def test_unknown_type_raises(self) -> None:
        import json

        encoder = _AgentabilityJSONEncoder()
        with pytest.raises(TypeError):
            encoder.default(object())

    def test_uuid_returns_string(self) -> None:
        encoder = _AgentabilityJSONEncoder()
        uid = uuid4()
        assert encoder.default(uid) == str(uid)

    def test_datetime_returns_isoformat(self) -> None:
        encoder = _AgentabilityJSONEncoder()
        dt = datetime(2026, 6, 1, 0, 0, 0)
        assert encoder.default(dt) == "2026-06-01T00:00:00"


# ===========================================================================
# validation
# ===========================================================================


class TestValidateUuid:
    def test_uuid_object_passthrough(self) -> None:
        uid = uuid4()
        assert validate_uuid(uid) == uid

    def test_string_uuid_parsed(self) -> None:
        s = "12345678-1234-5678-1234-567812345678"
        result = validate_uuid(s)
        assert str(result) == s

    def test_invalid_string_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid UUID"):
            validate_uuid("not-a-uuid")

    def test_none_raises(self) -> None:
        with pytest.raises(ValueError):
            validate_uuid(None)

    def test_int_raises(self) -> None:
        with pytest.raises(ValueError):
            validate_uuid(12345)


class TestValidateFloatRange:
    def test_within_range_passes(self) -> None:
        assert validate_float_range(0.5, 0.0, 1.0) == pytest.approx(0.5)

    def test_at_min_boundary_passes(self) -> None:
        assert validate_float_range(0.0, 0.0, 1.0) == 0.0

    def test_at_max_boundary_passes(self) -> None:
        assert validate_float_range(1.0, 0.0, 1.0) == 1.0

    def test_below_min_raises(self) -> None:
        with pytest.raises(ValueError, match=">= 0.0"):
            validate_float_range(-0.1, 0.0, 1.0, name="confidence")

    def test_above_max_raises(self) -> None:
        with pytest.raises(ValueError, match="<= 1.0"):
            validate_float_range(1.1, 0.0, 1.0, name="confidence")

    def test_no_bounds_passes(self) -> None:
        assert validate_float_range(999.9) == pytest.approx(999.9)

    def test_min_only(self) -> None:
        with pytest.raises(ValueError):
            validate_float_range(-1.0, min_value=0.0)

    def test_max_only(self) -> None:
        with pytest.raises(ValueError):
            validate_float_range(10.0, max_value=5.0)


class TestValidatePositiveInt:
    def test_zero_passes(self) -> None:
        assert validate_positive_int(0) == 0

    def test_positive_passes(self) -> None:
        assert validate_positive_int(42) == 42

    def test_negative_raises(self) -> None:
        with pytest.raises(ValueError, match=">= 0"):
            validate_positive_int(-1, name="count")


class TestValidateNonEmptyString:
    def test_normal_string_passes(self) -> None:
        assert validate_non_empty_string("hello") == "hello"

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError):
            validate_non_empty_string("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(ValueError):
            validate_non_empty_string("   ")

    def test_name_appears_in_error(self) -> None:
        with pytest.raises(ValueError, match="agent_id"):
            validate_non_empty_string("", name="agent_id")

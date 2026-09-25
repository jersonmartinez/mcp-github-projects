"""Unit tests for parse_json_items and parse_json_array in hardening.py."""

from __future__ import annotations

import pytest

from core.hardening import parse_json_array, parse_json_items


class TestParseJsonItems:
    """Tests for the dual-format parser (array or {items:[]} envelope)."""

    def test_parse_json_items_with_array(self) -> None:
        result = parse_json_items('[{"id": 1}]', context="test")
        assert result == [{"id": 1}]

    def test_parse_json_items_with_envelope(self) -> None:
        result = parse_json_items('{"items": [{"id": 1}]}', context="test")
        assert result == [{"id": 1}]

    def test_parse_json_items_empty_array(self) -> None:
        result = parse_json_items("[]", context="test")
        assert result == []

    def test_parse_json_items_empty_envelope(self) -> None:
        result = parse_json_items('{"items": []}', context="test")
        assert result == []

    def test_parse_json_items_invalid_json(self) -> None:
        with pytest.raises(ValueError, match="Invalid JSON from test"):
            parse_json_items("not json", context="test")

    def test_parse_json_items_wrong_type(self) -> None:
        with pytest.raises(ValueError, match="Expected a JSON array or items envelope"):
            parse_json_items('"string"', context="test")


class TestParseJsonArray:
    """Tests confirming parse_json_array rejects envelope format."""

    def test_parse_json_array_rejects_envelope(self) -> None:
        with pytest.raises(ValueError, match="Expected a JSON array"):
            parse_json_array('{"items": []}', context="test")

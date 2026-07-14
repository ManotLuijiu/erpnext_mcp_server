"""Tests for analytics result formatter module."""

from datetime import date, datetime, time
from decimal import Decimal

from erpnext_mcp_server.analytics.result_formatter import (
    ResultFormatter,
    _to_json_compatible,
    format_query_result,
)


class TestToJsonCompatible:
    """Tests for _to_json_compatible()."""

    def test_none_returns_none(self):
        """None returns None."""
        assert _to_json_compatible(None) is None

    def test_string_passes_through(self):
        """String returns unchanged."""
        assert _to_json_compatible("hello") == "hello"

    def test_int_passes_through(self):
        """int returns unchanged."""
        assert _to_json_compatible(42) == 42

    def test_float_passes_through(self):
        """float returns unchanged."""
        assert _to_json_compatible(3.14) == 3.14

    def test_datetime_to_iso(self):
        """datetime becomes ISO 8601 string."""
        dt = datetime(2026, 6, 30, 14, 30, 0)
        assert _to_json_compatible(dt) == "2026-06-30T14:30:00"

    def test_date_to_iso(self):
        """date becomes ISO 8601 string."""
        d = date(2026, 6, 30)
        assert _to_json_compatible(d) == "2026-06-30"

    def test_time_to_iso(self):
        """time becomes ISO 8601 string."""
        t = time(10, 30, 45)
        assert _to_json_compatible(t) == "10:30:45"

    def test_decimal_to_float(self):
        """Decimal becomes float."""
        result = _to_json_compatible(Decimal("1234.56"))
        assert isinstance(result, float)
        assert result == 1234.56

    def test_decimal_edge_cases(self):
        """Decimal conversion handles edge cases."""
        # Zero
        assert _to_json_compatible(Decimal("0")) == 0.0
        # Large number
        result = _to_json_compatible(Decimal("9999999999.99"))
        assert isinstance(result, float)

    def test_bytes_to_base64(self):
        """bytes becomes base64 string."""
        result = _to_json_compatible(b"hello")
        assert isinstance(result, str)
        assert result == "aGVsbG8="  # base64 of "hello"

    def test_list_passes_through(self):
        """list returns unchanged."""
        assert _to_json_compatible([1, 2, 3]) == [1, 2, 3]

    def test_dict_passes_through(self):
        """dict returns unchanged."""
        d = {"a": 1, "b": 2}
        assert _to_json_compatible(d) == d


class TestFormatQueryResult:
    """Tests for format_query_result()."""

    def test_basic_format(self):
        """Basic result is formatted correctly."""
        description = [("dimension",), ("metric_value",)]
        rows = [("ACME Corp", 150000.0), ("Beta Ltd", 80000.0)]
        result = format_query_result(description, rows, 23.5, max_rows=500)

        assert result.columns == ["dimension", "metric_value"]
        assert result.row_count == 2
        assert result.duration_ms == 23.5
        assert result.truncated is False
        assert result.rows[0] == {"dimension": "ACME Corp", "metric_value": 150000.0}
        assert result.rows[1] == {"dimension": "Beta Ltd", "metric_value": 80000.0}

    def test_truncation(self):
        """Rows beyond max_rows are truncated."""
        description = [("col",)]
        rows = [(1,), (2,), (3,), (4,), (5,)]
        result = format_query_result(description, rows, 10.0, max_rows=3)

        assert result.row_count == 3
        assert result.truncated is True
        assert [r["col"] for r in result.rows] == [1, 2, 3]

    def test_datetime_conversion(self):
        """datetime in rows becomes ISO strings."""
        description = [("dimension",), ("posting_date",)]
        dt = datetime(2026, 1, 15, 0, 0, 0)
        rows = [("ACME Corp", dt)]
        result = format_query_result(description, rows, 5.0, max_rows=500)

        assert result.rows[0]["posting_date"] == "2026-01-15T00:00:00"

    def test_decimal_conversion(self):
        """Decimal in rows becomes float."""
        description = [("col",)]
        rows = [(Decimal("1234.56"),)]
        result = format_query_result(description, rows, 5.0, max_rows=500)

        assert result.rows[0]["col"] == 1234.56
        assert isinstance(result.rows[0]["col"], float)

    def test_empty_rows(self):
        """Empty rows are handled correctly."""
        description = [("col",)]
        rows = []
        result = format_query_result(description, rows, 1.0, max_rows=500)

        assert result.columns == ["col"]
        assert result.row_count == 0
        assert result.rows == []

    def test_to_dict(self):
        """to_dict() produces JSON-serializable dict."""
        description = [("col",)]
        rows = [(42,)]
        result = format_query_result(description, rows, 5.0, max_rows=500)
        d = result.to_dict()
        # Should be JSON-serializable
        import json

        json.dumps(d)  # raises if not serializable


class TestResultFormatter:
    """Tests for ResultFormatter class."""

    def test_init_validates_max_rows(self):
        """max_rows < 1 raises ValueError."""
        import pytest

        with pytest.raises(ValueError):
            ResultFormatter(0)
        with pytest.raises(ValueError):
            ResultFormatter(-1)

    def test_max_rows_property(self):
        """max_rows property returns configured value."""
        f = ResultFormatter(max_rows=200)
        assert f.max_rows == 200

    def test_format_delegates_to_format_query_result(self):
        """format() calls format_query_result correctly."""
        f = ResultFormatter(max_rows=100)
        description = [("col",)]
        rows = [(1,)]
        result = f.format(description, rows, 10.0)

        assert result.row_count == 1
        assert result.duration_ms == 10.0
        assert result.truncated is False

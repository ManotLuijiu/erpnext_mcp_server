"""Tests for analytics query guard module."""

import pytest

from erpnext_mcp_server.analytics.exceptions import AnalyticsValidationError
from erpnext_mcp_server.analytics.query_guard import (
    GL_GROUP_BY_EXPRESSIONS,
    SALES_GROUP_BY_EXPRESSIONS,
    SALES_METRIC_EXPRESSIONS,
    QueryValidator,
)


class TestQueryValidatorDataset:
    """Tests for dataset validation."""

    def test_valid_dataset(self):
        """Valid datasets resolve to table names."""
        v = QueryValidator()
        assert v.validate_dataset("sales_invoice") == "tabSales Invoice"
        assert v.validate_dataset("general_ledger") == "tabGL Entry"
        assert v.validate_dataset("company") == "tabCompany"

    def test_invalid_dataset_raises(self):
        """Unknown dataset raises AnalyticsValidationError."""
        v = QueryValidator()
        with pytest.raises(AnalyticsValidationError) as exc_info:
            v.validate_dataset("malicious_table")
        assert "malicious_table" in str(exc_info.value)
        assert "Allowed:" in str(exc_info.value)


class TestQueryValidatorGroupBy:
    """Tests for group-by resolution."""

    def test_sales_valid_group_by(self):
        """Valid sales group-by expressions are resolved."""
        v = QueryValidator()
        assert v.resolve_group_by("customer", SALES_GROUP_BY_EXPRESSIONS) == "customer"
        assert (
            v.resolve_group_by("month", SALES_GROUP_BY_EXPRESSIONS)
            == "DATE_TRUNC('month', posting_date)"
        )
        assert (
            v.resolve_group_by("year", SALES_GROUP_BY_EXPRESSIONS)
            == "DATE_TRUNC('year', posting_date)"
        )

    def test_sales_invalid_group_by_raises(self):
        """Invalid sales group-by raises AnalyticsValidationError."""
        v = QueryValidator()
        with pytest.raises(AnalyticsValidationError) as exc_info:
            v.resolve_group_by("dangerous_col", SALES_GROUP_BY_EXPRESSIONS)
        assert "dangerous_col" in str(exc_info.value)

    def test_gl_valid_group_by(self):
        """Valid GL group-by expressions are resolved."""
        v = QueryValidator()
        assert v.resolve_group_by("account", GL_GROUP_BY_EXPRESSIONS) == "account"
        assert (
            v.resolve_group_by("month", GL_GROUP_BY_EXPRESSIONS)
            == "DATE_TRUNC('month', posting_date)"
        )

    def test_gl_invalid_group_by_raises(self):
        """Invalid GL group-by raises AnalyticsValidationError."""
        v = QueryValidator()
        with pytest.raises(AnalyticsValidationError):
            v.resolve_group_by("exec(", GL_GROUP_BY_EXPRESSIONS)


class TestQueryValidatorMetrics:
    """Tests for metric resolution."""

    def test_valid_metrics(self):
        """Valid metrics are resolved."""
        v = QueryValidator()
        assert (
            v.resolve_metric("net_sales", SALES_METRIC_EXPRESSIONS)
            == "SUM(base_net_amount)"
        )
        assert (
            v.resolve_metric("invoice_count", SALES_METRIC_EXPRESSIONS)
            == "COUNT(DISTINCT name)"
        )

    def test_invalid_metric_raises(self):
        """Invalid metric raises AnalyticsValidationError."""
        v = QueryValidator()
        with pytest.raises(AnalyticsValidationError):
            v.resolve_metric("DROP TABLE", SALES_METRIC_EXPRESSIONS)


class TestQueryValidatorIdentifier:
    """Tests for SQL identifier validation."""

    def test_valid_identifier(self):
        """Valid identifiers pass."""
        v = QueryValidator()
        v.validate_identifier("company", "field")
        v.validate_identifier("posting_date", "field")
        v.validate_identifier("_private_col", "field")

    def test_empty_identifier_raises(self):
        """Empty identifier raises."""
        v = QueryValidator()
        with pytest.raises(AnalyticsValidationError):
            v.validate_identifier("", "field")

    def test_sql_injection_identifier_raises(self):
        """Dangerous identifier raises."""
        v = QueryValidator()
        with pytest.raises(AnalyticsValidationError):
            v.validate_identifier("DROP", "field")
        with pytest.raises(AnalyticsValidationError):
            v.validate_identifier("DELETE", "field")


class TestQueryValidatorDateRange:
    """Tests for date range validation."""

    def test_valid_range(self):
        """Valid date range passes."""
        v = QueryValidator()
        v.validate_date_range("2026-01-01", "2026-06-30")

    def test_invalid_date_format_raises(self):
        """Invalid date format raises."""
        v = QueryValidator()
        with pytest.raises(AnalyticsValidationError):
            v.validate_date_range("01-01-2026", "2026-06-30")

    def test_from_after_to_raises(self):
        """from_date after to_date raises."""
        v = QueryValidator()
        with pytest.raises(AnalyticsValidationError):
            v.validate_date_range("2026-06-30", "2026-01-01")


class TestQueryValidatorCompany:
    """Tests for company validation."""

    def test_valid_company(self):
        """Non-empty company passes."""
        v = QueryValidator()
        assert v.validate_company("Example Company Ltd.") == "Example Company Ltd."

    def test_empty_company_raises(self):
        """Empty company raises."""
        v = QueryValidator()
        with pytest.raises(AnalyticsValidationError):
            v.validate_company("")

    def test_whitespace_only_company_raises(self):
        """Whitespace-only company raises."""
        v = QueryValidator()
        with pytest.raises(AnalyticsValidationError):
            v.validate_company("   ")


class TestQueryValidatorLimit:
    """Tests for limit validation."""

    def test_valid_limit(self):
        """Valid limit passes and is bounded."""
        v = QueryValidator()
        assert v.validate_limit(50, 500) == 50
        assert v.validate_limit(1000, 500) == 500  # bounded

    def test_limit_below_one_raises(self):
        """limit < 1 raises."""
        v = QueryValidator()
        with pytest.raises(AnalyticsValidationError):
            v.validate_limit(0, 500)

    def test_limit_non_integer_raises(self):
        """Non-integer limit raises."""
        v = QueryValidator()
        with pytest.raises(AnalyticsValidationError):
            v.validate_limit("abc", 500)


class TestQuerySafety:
    """Tests for query safety checks."""

    def test_safe_select_query_passes(self):
        """Simple SELECT query passes safety check."""
        v = QueryValidator()
        v.check_no_raw_identifiers_in_query(
            "SELECT * FROM tabSales Invoice WHERE company = ?"
        )

    def test_dangerous_keywords_blocked(self):
        """Queries with dangerous keywords are blocked."""
        v = QueryValidator()
        with pytest.raises(AnalyticsValidationError):
            v.check_no_raw_identifiers_in_query(
                "SELECT * FROM tabSales Invoice; DROP TABLE tabCompany;--"
            )
        with pytest.raises(AnalyticsValidationError):
            v.check_no_raw_identifiers_in_query(
                "SELECT * FROM tabSales Invoice WHERE company = ?; DELETE FROM tabGL Entry"
            )

    def test_string_literals_stripped(self):
        """String literals are stripped before keyword check."""
        v = QueryValidator()
        # "DROP" in a string literal should not be blocked
        v.check_no_raw_identifiers_in_query(
            "SELECT * FROM tabSales Invoice WHERE description = 'DROP dangerous'"
        )

    def test_quoted_identifiers_stripped(self):
        """Quoted identifiers are stripped before keyword check."""
        v = QueryValidator()
        v.check_no_raw_identifiers_in_query(
            'SELECT "DROP", company FROM tabSales Invoice'
        )

"""Tests for sales analytics query builder."""

import pytest

from erpnext_mcp_server.analytics.exceptions import AnalyticsValidationError
from erpnext_mcp_server.analytics.queries.sales import (
    SalesQuerySpec,
    build_sales_query,
    validate_sales_params,
)


class TestValidateSalesParams:
    """Tests for validate_sales_params()."""

    def test_valid_params(self):
        """Valid parameters produce SalesQuerySpec."""
        spec = validate_sales_params(
            company="ACME Corp",
            from_date="2026-01-01",
            to_date="2026-06-30",
            group_by="month",
            metric="net_sales",
            limit=100,
            max_rows=500,
        )
        assert isinstance(spec, SalesQuerySpec)
        assert spec.company == "ACME Corp"
        assert spec.group_by == "month"
        assert spec.metric == "net_sales"
        assert spec.limit == 100

    def test_limit_bounded_by_max_rows(self):
        """limit is bounded to max_rows."""
        spec = validate_sales_params(
            company="ACME Corp",
            from_date="2026-01-01",
            to_date="2026-06-30",
            group_by="month",
            metric="net_sales",
            limit=9999,
            max_rows=500,
        )
        assert spec.limit == 500

    def test_invalid_date_range_raises(self):
        """from_date > to_date raises."""
        with pytest.raises(AnalyticsValidationError):
            validate_sales_params(
                company="ACME Corp",
                from_date="2026-06-30",
                to_date="2026-01-01",
                group_by="month",
                metric="net_sales",
                limit=100,
                max_rows=500,
            )

    def test_invalid_date_format_raises(self):
        """Invalid date format raises."""
        with pytest.raises(AnalyticsValidationError):
            validate_sales_params(
                company="ACME Corp",
                from_date="30/06/2026",
                to_date="2026-06-30",
                group_by="month",
                metric="net_sales",
                limit=100,
                max_rows=500,
            )

    def test_empty_company_raises(self):
        """Empty company raises."""
        with pytest.raises(AnalyticsValidationError):
            validate_sales_params(
                company="",
                from_date="2026-01-01",
                to_date="2026-06-30",
                group_by="month",
                metric="net_sales",
                limit=100,
                max_rows=500,
            )

    def test_invalid_group_by_raises(self):
        """Invalid group_by raises."""
        with pytest.raises(AnalyticsValidationError):
            validate_sales_params(
                company="ACME Corp",
                from_date="2026-01-01",
                to_date="2026-06-30",
                group_by="DROP TABLE",
                metric="net_sales",
                limit=100,
                max_rows=500,
            )

    def test_invalid_metric_raises(self):
        """Invalid metric raises."""
        with pytest.raises(AnalyticsValidationError):
            validate_sales_params(
                company="ACME Corp",
                from_date="2026-01-01",
                to_date="2026-06-30",
                group_by="month",
                metric="DELETE FROM",
                limit=100,
                max_rows=500,
            )

    def test_limit_zero_raises(self):
        """limit < 1 raises."""
        with pytest.raises(AnalyticsValidationError):
            validate_sales_params(
                company="ACME Corp",
                from_date="2026-01-01",
                to_date="2026-06-30",
                group_by="month",
                metric="net_sales",
                limit=0,
                max_rows=500,
            )


class TestBuildSalesQuery:
    """Tests for build_sales_query()."""

    def test_month_group_by_query(self):
        """Monthly grouping produces correct SQL."""
        spec = SalesQuerySpec(
            company="ACME Corp",
            from_date="2026-01-01",
            to_date="2026-06-30",
            group_by="month",
            metric="net_sales",
            limit=100,
        )
        query, params = build_sales_query(spec)
        assert "SELECT" in query
        assert "DATE_TRUNC('month', posting_date)" in query
        assert "SUM(base_net_amount)" in query
        assert "GROUP BY" in query
        assert "ORDER BY metric_value DESC" in query
        assert "LIMIT ?" in query
        # Check params
        assert params == ("ACME Corp", "2026-01-01", "2026-06-30", 100)

    def test_customer_group_by_query(self):
        """Customer grouping produces correct SQL."""
        spec = SalesQuerySpec(
            company="ACME Corp",
            from_date="2026-01-01",
            to_date="2026-06-30",
            group_by="customer",
            metric="invoice_count",
            limit=50,
        )
        query, params = build_sales_query(spec)
        assert "customer" in query
        assert "COUNT(DISTINCT name)" in query
        assert params == ("ACME Corp", "2026-01-01", "2026-06-30", 50)

    def test_invoice_count_metric(self):
        """invoice_count metric works correctly."""
        spec = SalesQuerySpec(
            company="ACME Corp",
            from_date="2026-01-01",
            to_date="2026-06-30",
            group_by="customer_group",
            metric="invoice_count",
            limit=100,
        )
        query, params = build_sales_query(spec)
        assert "COUNT(DISTINCT name)" in query

    def test_territory_group_by(self):
        """Territory grouping works."""
        spec = SalesQuerySpec(
            company="ACME Corp",
            from_date="2026-01-01",
            to_date="2026-06-30",
            group_by="territory",
            metric="gross_sales",
            limit=100,
        )
        query, params = build_sales_query(spec)
        assert "territory" in query

    def test_year_group_by(self):
        """Year grouping works."""
        spec = SalesQuerySpec(
            company="ACME Corp",
            from_date="2025-01-01",
            to_date="2026-12-31",
            group_by="year",
            metric="net_sales",
            limit=100,
        )
        query, params = build_sales_query(spec)
        assert "DATE_TRUNC('year', posting_date)" in query

    def test_qty_metric(self):
        """qty metric works."""
        spec = SalesQuerySpec(
            company="ACME Corp",
            from_date="2026-01-01",
            to_date="2026-06-30",
            group_by="month",
            metric="qty",
            limit=100,
        )
        query, params = build_sales_query(spec)
        assert "SUM(qty)" in query

    def test_avg_net_rate_metric(self):
        """avg_net_rate metric works."""
        spec = SalesQuerySpec(
            company="ACME Corp",
            from_date="2026-01-01",
            to_date="2026-06-30",
            group_by="month",
            metric="avg_net_rate",
            limit=100,
        )
        query, params = build_sales_query(spec)
        assert "AVG(base_net_amount" in query

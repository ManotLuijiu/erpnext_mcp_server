"""Tests for General Ledger analytics query builder."""

import pytest

from erpnext_mcp_server.analytics.exceptions import AnalyticsValidationError
from erpnext_mcp_server.analytics.queries.general_ledger import (
    GLQuerySpec,
    build_gl_query,
    validate_gl_params,
)


class TestValidateGLParams:
    """Tests for validate_gl_params()."""

    def test_valid_params(self):
        """Valid parameters produce GLQuerySpec."""
        spec = validate_gl_params(
            company="ACME Corp",
            from_date="2026-01-01",
            to_date="2026-06-30",
            group_by="account",
            account=None,
            cost_center=None,
            limit=100,
            max_rows=500,
        )
        assert isinstance(spec, GLQuerySpec)
        assert spec.company == "ACME Corp"
        assert spec.group_by == "account"
        assert spec.account is None
        assert spec.cost_center is None
        assert spec.limit == 100

    def test_limit_bounded(self):
        """limit is bounded to max_rows."""
        spec = validate_gl_params(
            company="ACME Corp",
            from_date="2026-01-01",
            to_date="2026-06-30",
            group_by="account",
            account=None,
            cost_center=None,
            limit=9999,
            max_rows=500,
        )
        assert spec.limit == 500

    def test_optional_account_filter(self):
        """Optional account filter is preserved."""
        spec = validate_gl_params(
            company="ACME Corp",
            from_date="2026-01-01",
            to_date="2026-06-30",
            group_by="account",
            account="Sales - EC",
            cost_center=None,
            limit=100,
            max_rows=500,
        )
        assert spec.account == "Sales - EC"

    def test_whitespace_account_stripped(self):
        """Account filter whitespace is stripped."""
        spec = validate_gl_params(
            company="ACME Corp",
            from_date="2026-01-01",
            to_date="2026-06-30",
            group_by="account",
            account="  Sales - EC  ",
            cost_center=None,
            limit=100,
            max_rows=500,
        )
        assert spec.account == "Sales - EC"

    def test_empty_optional_filters_become_none(self):
        """Empty account/cost_center become None."""
        spec = validate_gl_params(
            company="ACME Corp",
            from_date="2026-01-01",
            to_date="2026-06-30",
            group_by="account",
            account="",
            cost_center="",
            limit=100,
            max_rows=500,
        )
        assert spec.account is None
        assert spec.cost_center is None

    def test_invalid_date_range_raises(self):
        """from_date > to_date raises."""
        with pytest.raises(AnalyticsValidationError):
            validate_gl_params(
                company="ACME Corp",
                from_date="2026-06-30",
                to_date="2026-01-01",
                group_by="account",
                account=None,
                cost_center=None,
                limit=100,
                max_rows=500,
            )

    def test_empty_company_raises(self):
        """Empty company raises."""
        with pytest.raises(AnalyticsValidationError):
            validate_gl_params(
                company="",
                from_date="2026-01-01",
                to_date="2026-06-30",
                group_by="account",
                account=None,
                cost_center=None,
                limit=100,
                max_rows=500,
            )

    def test_invalid_group_by_raises(self):
        """Invalid group_by raises."""
        with pytest.raises(AnalyticsValidationError):
            validate_gl_params(
                company="ACME Corp",
                from_date="2026-01-01",
                to_date="2026-06-30",
                group_by="DROP TABLE",
                account=None,
                cost_center=None,
                limit=100,
                max_rows=500,
            )


class TestBuildGLQuery:
    """Tests for build_gl_query()."""

    def test_basic_gl_query(self):
        """Basic GL query structure is correct."""
        spec = GLQuerySpec(
            company="ACME Corp",
            from_date="2026-01-01",
            to_date="2026-06-30",
            group_by="account",
            account=None,
            cost_center=None,
            limit=100,
        )
        query, params = build_gl_query(spec)
        assert "SELECT" in query
        assert "account AS dimension" in query
        assert "SUM(debit_in_account_currency)" in query
        assert "SUM(credit_in_account_currency)" in query
        assert "net_balance" in query
        assert "entry_count" in query
        assert "GROUP BY account" in query
        assert "ORDER BY ABS" in query
        assert "LIMIT ?" in query
        # Params: company, from_date, to_date, limit
        assert params == ("ACME Corp", "2026-01-01", "2026-06-30", 100)

    def test_cost_center_filter(self):
        """Optional cost_center filter is parameterized."""
        spec = GLQuerySpec(
            company="ACME Corp",
            from_date="2026-01-01",
            to_date="2026-06-30",
            group_by="account",
            account=None,
            cost_center="Main CC",
            limit=100,
        )
        query, params = build_gl_query(spec)
        assert "cost_center = ?" in query
        assert params == ("ACME Corp", "2026-01-01", "2026-06-30", "Main CC", 100)

    def test_account_filter(self):
        """Optional account filter is parameterized."""
        spec = GLQuerySpec(
            company="ACME Corp",
            from_date="2026-01-01",
            to_date="2026-06-30",
            group_by="cost_center",
            account="Sales - EC",
            cost_center=None,
            limit=100,
        )
        query, params = build_gl_query(spec)
        assert "account = ?" in query
        assert params == ("ACME Corp", "2026-01-01", "2026-06-30", "Sales - EC", 100)

    def test_both_filters(self):
        """Both account and cost_center filters are parameterized."""
        spec = GLQuerySpec(
            company="ACME Corp",
            from_date="2026-01-01",
            to_date="2026-06-30",
            group_by="month",
            account="Sales - EC",
            cost_center="Main CC",
            limit=100,
        )
        query, params = build_gl_query(spec)
        assert "account = ?" in query
        assert "cost_center = ?" in query
        assert params == (
            "ACME Corp",
            "2026-01-01",
            "2026-06-30",
            "Sales - EC",
            "Main CC",
            100,
        )

    def test_month_group_by(self):
        """Month grouping works."""
        spec = GLQuerySpec(
            company="ACME Corp",
            from_date="2026-01-01",
            to_date="2026-06-30",
            group_by="month",
            account=None,
            cost_center=None,
            limit=100,
        )
        query, params = build_gl_query(spec)
        assert "DATE_TRUNC('month', posting_date)" in query
        assert "GROUP BY DATE_TRUNC('month', posting_date)" in query

    def test_voucher_type_group_by(self):
        """voucher_type grouping works."""
        spec = GLQuerySpec(
            company="ACME Corp",
            from_date="2026-01-01",
            to_date="2026-06-30",
            group_by="voucher_type",
            account=None,
            cost_center=None,
            limit=100,
        )
        query, params = build_gl_query(spec)
        assert "voucher_type AS dimension" in query

    def test_net_balance_calculation(self):
        """Net balance is calculated as debit - credit."""
        spec = GLQuerySpec(
            company="ACME Corp",
            from_date="2026-01-01",
            to_date="2026-06-30",
            group_by="account",
            account=None,
            cost_center=None,
            limit=100,
        )
        query, params = build_gl_query(spec)
        # net_balance = debit - credit
        assert (
            "debit_in_account_currency) - SUM(credit_in_account_currency) AS net_balance"
            in query
        )

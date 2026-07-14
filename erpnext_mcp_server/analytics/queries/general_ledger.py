"""General Ledger analytics query builder.

Provides pre-approved, parameterized GL analytics queries
against the DuckDB frappe_db (MariaDB) attachment.

All table and column identifiers are resolved through internal
allowlists; all values are parameterized.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Literal

from erpnext_mcp_server.analytics.query_guard import (
    GL_GROUP_BY_EXPRESSIONS,
    QueryValidator,
)

logger = logging.getLogger("erpnext_mcp_server.analytics")

# Physical table (from allowlist — safe to use directly in SQL)
_TABLE = "frappe_db.tabGL Entry"


@dataclass(frozen=True)
class GLQuerySpec:
    """Specification for a validated GL query."""

    company: str
    from_date: str
    to_date: str
    group_by: Literal["account", "cost_center", "voucher_type", "month", "week", "year"]
    account: str | None
    cost_center: str | None
    limit: int


def build_gl_query(spec: GLQuerySpec) -> tuple[str, tuple[Any, ...]]:
    """Build a parameterized GL analytics query.

    Args:
        spec: Validated GL query specification.

    Returns:
        A tuple of (SQL query string, query parameters).
    """
    # Resolve group-by expression
    group_expr = GL_GROUP_BY_EXPRESSIONS[spec.group_by]

    # SELECT clause
    if spec.group_by in ("month", "week", "year"):
        select_clause = f"  {group_expr} AS dimension"
    else:
        select_clause = f"  {group_expr} AS dimension"

    select_clause += (
        ",\n  SUM(debit_in_account_currency) AS total_debit,\n"
        "  SUM(credit_in_account_currency) AS total_credit,\n"
        "  SUM(debit_in_account_currency) - SUM(credit_in_account_currency) AS net_balance,\n"
        "  COUNT(*) AS entry_count"
    )

    # WHERE clause (always include these)
    where_parts = [
        "company = ?",
        "posting_date >= ?",
        "posting_date <= ?",
        "docstatus = 1",
    ]
    params: list[Any] = [spec.company, spec.from_date, spec.to_date]

    # Optional account filter (parameterized)
    if spec.account:
        where_parts.append("account = ?")
        params.append(spec.account)

    # Optional cost_center filter (parameterized)
    if spec.cost_center:
        where_parts.append("cost_center = ?")
        params.append(spec.cost_center)

    where_clause = "\n  " + "\n  AND ".join(where_parts)

    # ORDER BY absolute net balance descending
    order_clause = "ORDER BY ABS(SUM(debit_in_account_currency) - SUM(credit_in_account_currency)) DESC"

    # LIMIT
    limit_clause = "LIMIT ?"
    params.append(spec.limit)

    query = f"""\
SELECT
{select_clause}
FROM {_TABLE}
WHERE{where_clause}
GROUP BY {group_expr}
{order_clause}
{limit_clause}
"""

    logger.debug(
        "GL query built: group_by=%s account=%s cost_center=%s limit=%d",
        spec.group_by,
        spec.account,
        spec.cost_center,
        spec.limit,
    )

    return query, tuple(params)


def validate_gl_params(
    company: str,
    from_date: str,
    to_date: str,
    group_by: str,
    account: str | None,
    cost_center: str | None,
    limit: int,
    max_rows: int,
) -> GLQuerySpec:
    """Validate and build a GLQuerySpec.

    Args:
        company: Company name.
        from_date: Start date (YYYY-MM-DD).
        to_date: End date (YYYY-MM-DD).
        group_by: Grouping dimension key.
        account: Optional account filter.
        cost_center: Optional cost centre filter.
        limit: Requested row limit.
        max_rows: Configured maximum rows.

    Returns:
        Validated GLQuerySpec.

    Raises:
        AnalyticsValidationError: On validation failure.
    """
    from erpnext_mcp_server.analytics.exceptions import AnalyticsValidationError

    validator = QueryValidator()

    safe_company = validator.validate_company(company)
    validator.validate_date_range(from_date, to_date)

    # Validate group_by
    group_by_values: tuple[str, ...] = (
        "account",
        "cost_center",
        "voucher_type",
        "month",
        "week",
        "year",
    )
    if group_by not in group_by_values:
        raise AnalyticsValidationError(
            f"Invalid group_by '{group_by}'. Allowed: {', '.join(group_by_values)}",
            field="group_by",
        )

    # Validate optional filters (non-empty strings only)
    safe_account: str | None = account.strip() if account else None
    safe_cost_center: str | None = cost_center.strip() if cost_center else None

    safe_limit = validator.validate_limit(limit, max_rows)

    return GLQuerySpec(
        company=safe_company,
        from_date=from_date,
        to_date=to_date,
        group_by=group_by,  # type: ignore[arg-type]
        account=safe_account,
        cost_center=safe_cost_center,
        limit=safe_limit,
    )

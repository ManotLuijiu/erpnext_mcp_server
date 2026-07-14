"""Sales analytics query builder.

Provides pre-approved, parameterized sales analytics queries
against the DuckDB frappe_db (MariaDB) attachment.

All table and column identifiers are resolved through internal
allowlists; all values are parameterized.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Literal

from erpnext_mcp_server.analytics.query_guard import (
    SALES_GROUP_BY_EXPRESSIONS,
    SALES_METRIC_EXPRESSIONS,
    QueryValidator,
)

logger = logging.getLogger("erpnext_mcp_server.analytics")

# Physical table (from allowlist — safe to use directly in SQL)
_TABLE = "frappe_db.tabSales Invoice"


@dataclass(frozen=True)
class SalesQuerySpec:
    """Specification for a validated sales query."""

    company: str
    from_date: str
    to_date: str
    group_by: Literal[
        "customer", "customer_group", "territory", "month", "week", "year"
    ]
    metric: Literal["net_sales", "gross_sales", "invoice_count", "qty", "avg_net_rate"]
    limit: int


def build_sales_query(spec: SalesQuerySpec) -> tuple[str, tuple[Any, ...]]:
    """Build a parameterized sales analytics query.

    Args:
        spec: Validated query specification.

    Returns:
        A tuple of (SQL query string, query parameters).
    """
    # Resolve group-by expression
    group_expr = SALES_GROUP_BY_EXPRESSIONS[spec.group_by]

    # Resolve metric expression(s)
    metric_expr = SALES_METRIC_EXPRESSIONS[spec.metric]

    # SELECT clause
    if spec.group_by in ("month", "week", "year"):
        # Date-based grouping: show ISO date label
        select_clause = f"  {group_expr} AS dimension"
    else:
        select_clause = f"  {group_expr} AS dimension"

    select_clause += f",\n  {metric_expr} AS metric_value"

    # Add invoice_count for non-count queries
    if spec.metric != "invoice_count":
        select_clause += ",\n  COUNT(DISTINCT name) AS invoice_count"

    # FROM / WHERE
    where_clause = "\n  company = ?\n  AND posting_date >= ?\n  AND posting_date <= ?\n  AND docstatus = 1"

    params: tuple[Any, ...] = (spec.company, spec.from_date, spec.to_date)

    # ORDER BY
    order_clause = "ORDER BY metric_value DESC"

    # LIMIT (applied via parameters at executor level)
    limit_clause = "LIMIT ?"
    params += (spec.limit,)

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
        "Sales query built: group_by=%s metric=%s limit=%d",
        spec.group_by,
        spec.metric,
        spec.limit,
    )

    return query, params


def validate_sales_params(
    company: str,
    from_date: str,
    to_date: str,
    group_by: str,
    metric: str,
    limit: int,
    max_rows: int,
) -> SalesQuerySpec:
    """Validate and build a SalesQuerySpec.

    Args:
        company: Company name.
        from_date: Start date (YYYY-MM-DD).
        to_date: End date (YYYY-MM-DD).
        group_by: Grouping dimension key.
        metric: Metric key.
        limit: Requested row limit.
        max_rows: Configured maximum rows.

    Returns:
        Validated SalesQuerySpec.

    Raises:
        AnalyticsValidationError: On validation failure.
    """
    from erpnext_mcp_server.analytics.exceptions import AnalyticsValidationError

    validator = QueryValidator()

    validator.validate_company(company)
    validator.validate_date_range(from_date, to_date)
    safe_company = validator.validate_company(company)  # type: ignore[assignment]

    # Validate group_by
    group_by_values: tuple[str, ...] = (
        "customer",
        "customer_group",
        "territory",
        "month",
        "week",
        "year",
    )
    if group_by not in group_by_values:
        raise AnalyticsValidationError(
            f"Invalid group_by '{group_by}'. Allowed: {', '.join(group_by_values)}",
            field="group_by",
        )

    # Validate metric
    metric_values: tuple[str, ...] = (
        "net_sales",
        "gross_sales",
        "invoice_count",
        "qty",
        "avg_net_rate",
    )
    if metric not in metric_values:
        raise AnalyticsValidationError(
            f"Invalid metric '{metric}'. Allowed: {', '.join(metric_values)}",
            field="metric",
        )

    safe_limit = validator.validate_limit(limit, max_rows)

    return SalesQuerySpec(
        company=safe_company,
        from_date=from_date,
        to_date=to_date,
        group_by=group_by,  # type: ignore[arg-type]
        metric=metric,  # type: ignore[arg-type]
        limit=safe_limit,
    )

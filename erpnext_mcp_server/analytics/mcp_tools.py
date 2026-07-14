"""DuckDB analytics MCP tools.

These tools are registered with the FastMCP server and provide
read-only analytical access to ERPNext data via DuckDB + MariaDB.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from erpnext_mcp_server.analytics.configuration import get_configuration
from erpnext_mcp_server.analytics.connection import DuckDBAnalyticsConnection
from erpnext_mcp_server.analytics.exceptions import (
    AnalyticsConfigurationError,
    AnalyticsConnectionError,
    AnalyticsDisabledError,
    AnalyticsError,
    AnalyticsQueryError,
    AnalyticsValidationError,
)
from erpnext_mcp_server.analytics.queries.general_ledger import (
    build_gl_query,
    validate_gl_params,
)
from erpnext_mcp_server.analytics.queries.sales import (
    build_sales_query,
    validate_sales_params,
)
from erpnext_mcp_server.analytics.result_formatter import ResultFormatter
from erpnext_mcp_server.analytics.schema_registry import get_schema_registry

logger = logging.getLogger("erpnext_mcp_server.analytics")


# ---------------------------------------------------------------------------
# Module-level connection (lazy, per-server-instance)
# ---------------------------------------------------------------------------

_connection: DuckDBAnalyticsConnection | None = None
_configured: bool = False


def _get_connection() -> DuckDBAnalyticsConnection:
    """Get or create the analytics connection."""
    global _connection
    if _connection is None:
        config = get_configuration()
        _connection = DuckDBAnalyticsConnection(config)
    return _connection


# ---------------------------------------------------------------------------
# Safe JSON response helpers
# ---------------------------------------------------------------------------


def _safe_error(exc: AnalyticsError) -> dict[str, Any]:
    """Return a safe JSON-compatible error structure."""
    return {"error": {"code": exc.code, "message": exc.message}}


# ---------------------------------------------------------------------------
# MCP Tool 1: analytics_status
# ---------------------------------------------------------------------------


def get_analytics_status() -> str:
    """Return DuckDB analytics status (read-only tool).

    Returns JSON with engine info, attachment status, and connection health.
    No credentials or passwords are exposed.
    """
    try:
        config = get_configuration()
    except AnalyticsConfigurationError as e:
        return json.dumps({"enabled": False, "connected": False, "message": str(e)})

    if not config.enabled:
        return json.dumps(
            {
                "enabled": False,
                "connected": False,
                "message": "DuckDB analytics is disabled",
            }
        )

    try:
        conn = _get_connection()
        health = conn.health_check()
        return json.dumps(health)
    except AnalyticsDisabledError:
        return json.dumps(
            {
                "enabled": False,
                "connected": False,
                "message": "DuckDB analytics is disabled",
            }
        )
    except AnalyticsConnectionError as e:
        logger.error("Analytics connection error: %s", e)
        return json.dumps(
            {
                "enabled": True,
                "connected": False,
                "message": "Failed to connect to DuckDB analytics",
            }
        )
    except Exception as e:
        logger.exception("Unexpected error in analytics_status: %s", e)
        return json.dumps(
            {
                "enabled": True,
                "connected": False,
                "message": "Unexpected error checking analytics status",
            }
        )


# ---------------------------------------------------------------------------
# MCP Tool 2: describe_analytics_schema
# ---------------------------------------------------------------------------


def describe_analytics_schema(dataset: str | None = None) -> str:
    """Return schema metadata for analytics datasets (read-only tool).

    Without a dataset argument, returns all approved datasets.
    With a dataset argument, returns its fields, dimensions, metrics,
    and default conditions.

    Args:
        dataset: Optional logical dataset key (e.g., "sales_invoice").

    Returns:
        JSON string with schema metadata.
    """
    try:
        registry = get_schema_registry()

        if dataset:
            desc = registry.describe_dataset(dataset)
            if desc is None:
                return json.dumps(
                    {
                        "error": {
                            "code": "ANALYTICS_VALIDATION_ERROR",
                            "message": f"Unknown dataset '{dataset}'",
                        }
                    }
                )
            return json.dumps(desc, indent=2)

        return json.dumps({"datasets": registry.describe_all()}, indent=2)

    except Exception as e:
        logger.exception("Unexpected error in describe_analytics_schema: %s", e)
        return json.dumps(
            {
                "error": {
                    "code": "ANALYTICS_ERROR",
                    "message": "Failed to describe analytics schema",
                }
            }
        )


# ---------------------------------------------------------------------------
# MCP Tool 3: analyze_sales
# ---------------------------------------------------------------------------


def analyze_sales(
    company: str,
    from_date: str,
    to_date: str,
    group_by: str = "month",
    metric: str = "net_sales",
    limit: int = 100,
) -> str:
    """Analyze sales data (read-only tool).

    Queries submitted sales invoices grouped by the specified dimension
    and aggregated by the specified metric.

    Args:
        company: Company name (required).
        from_date: Start date YYYY-MM-DD (required).
        to_date: End date YYYY-MM-DD (required).
        group_by: Grouping dimension (customer|customer_group|territory|month|week|year).
        metric: Metric to aggregate (net_sales|gross_sales|invoice_count|qty|avg_net_rate).
        limit: Max rows returned (bounded by config max_rows).

    Returns:
        JSON string with analysis results.
    """
    try:
        config = get_configuration()
    except AnalyticsConfigurationError as e:
        return json.dumps(_safe_error(e))

    if not config.enabled:
        return json.dumps(
            _safe_error(AnalyticsDisabledError("DuckDB analytics is disabled"))
        )

    # Validate parameters
    try:
        spec = validate_sales_params(
            company=company,
            from_date=from_date,
            to_date=to_date,
            group_by=group_by,
            metric=metric,
            limit=limit,
            max_rows=config.max_rows,
        )
    except AnalyticsValidationError as e:
        return json.dumps(_safe_error(e))

    # Build and execute query
    try:
        conn = _get_connection()
        formatter = ResultFormatter(config.max_rows)
        query, params = build_sales_query(spec)

        start = time.perf_counter()
        cursor = conn.execute(query, params)  # noqa: S
        rows = cursor.fetchall()
        description = cursor.description
        elapsed_ms = (time.perf_counter() - start) * 1000

        result = formatter.format(description, rows, elapsed_ms)

        logger.info(
            "sales_analysis company=%s group_by=%s metric=%s rows=%d duration_ms=%.1f",
            spec.company,
            spec.group_by,
            spec.metric,
            result.row_count,
            result.duration_ms,
        )

        output = {
            "analysis": "sales",
            "company": spec.company,
            "from_date": spec.from_date,
            "to_date": spec.to_date,
            "group_by": spec.group_by,
            "metric": spec.metric,
            "row_count": result.row_count,
            "duration_ms": result.duration_ms,
            "truncated": result.truncated,
            "data": result.rows,
        }
        return json.dumps(output, indent=2)

    except (AnalyticsConnectionError, AnalyticsQueryError) as e:
        logger.error("Sales analysis failed: %s", e)
        return json.dumps(_safe_error(e))
    except Exception as e:
        logger.exception("Unexpected error in analyze_sales: %s", e)
        return json.dumps(
            {
                "error": {
                    "code": "ANALYTICS_ERROR",
                    "message": "An unexpected error occurred during sales analysis",
                }
            }
        )


# ---------------------------------------------------------------------------
# MCP Tool 4: analyze_general_ledger
# ---------------------------------------------------------------------------


def analyze_general_ledger(
    company: str,
    from_date: str,
    to_date: str,
    group_by: str = "account",
    account: str | None = None,
    cost_center: str | None = None,
    limit: int = 100,
) -> str:
    """Analyze General Ledger entries (read-only tool).

    Queries submitted GL entries grouped by the specified dimension,
    calculating total debit, credit, and net balance.

    Args:
        company: Company name (required).
        from_date: Start date YYYY-MM-DD (required).
        to_date: End date YYYY-MM-DD (required).
        group_by: Grouping dimension (account|cost_center|voucher_type|month|week|year).
        account: Optional account filter.
        cost_center: Optional cost centre filter.
        limit: Max rows returned (bounded by config max_rows).

    Returns:
        JSON string with GL analysis results.
    """
    try:
        config = get_configuration()
    except AnalyticsConfigurationError as e:
        return json.dumps(_safe_error(e))

    if not config.enabled:
        return json.dumps(
            _safe_error(AnalyticsDisabledError("DuckDB analytics is disabled"))
        )

    # Validate parameters
    try:
        spec = validate_gl_params(
            company=company,
            from_date=from_date,
            to_date=to_date,
            group_by=group_by,
            account=account,
            cost_center=cost_center,
            limit=limit,
            max_rows=config.max_rows,
        )
    except AnalyticsValidationError as e:
        return json.dumps(_safe_error(e))

    # Build and execute query
    try:
        conn = _get_connection()
        formatter = ResultFormatter(config.max_rows)
        query, params = build_gl_query(spec)

        start = time.perf_counter()
        cursor = conn.execute(query, params)  # noqa: S
        rows = cursor.fetchall()
        description = cursor.description
        elapsed_ms = (time.perf_counter() - start) * 1000

        result = formatter.format(description, rows, elapsed_ms)

        logger.info(
            "gl_analysis company=%s group_by=%s account=%s cost_center=%s rows=%d duration_ms=%.1f",
            spec.company,
            spec.group_by,
            spec.account,
            spec.cost_center,
            result.row_count,
            result.duration_ms,
        )

        output = {
            "analysis": "general_ledger",
            "company": spec.company,
            "from_date": spec.from_date,
            "to_date": spec.to_date,
            "group_by": spec.group_by,
            "account_filter": spec.account,
            "cost_center_filter": spec.cost_center,
            "row_count": result.row_count,
            "duration_ms": result.duration_ms,
            "truncated": result.truncated,
            "data": result.rows,
        }
        return json.dumps(output, indent=2)

    except (AnalyticsConnectionError, AnalyticsQueryError) as e:
        logger.error("GL analysis failed: %s", e)
        return json.dumps(_safe_error(e))
    except Exception as e:
        logger.exception("Unexpected error in analyze_general_ledger: %s", e)
        return json.dumps(
            {
                "error": {
                    "code": "ANALYTICS_ERROR",
                    "message": "An unexpected error occurred during GL analysis",
                }
            }
        )


# ---------------------------------------------------------------------------
# Tool registration helpers
# ---------------------------------------------------------------------------


def register_analytics_tools(server: Any) -> None:
    """Register analytics tools with a FastMCP server.

    Args:
        server: A FastMCP server instance.
    """
    # Dynamically import to avoid circular imports at module level
    import mcp.types as types

    server.add_tool(
        types.Tool(
            name="analytics_status",
            description=(
                "Return DuckDB analytics engine status, connection health, "
                "and configuration. Does not expose credentials."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        handler=lambda: get_analytics_status(),
    )

    server.add_tool(
        types.Tool(
            name="describe_analytics_schema",
            description=(
                "Return metadata for DuckDB analytics datasets. "
                "Without arguments, returns all approved datasets. "
                "With a dataset name, returns its fields, dimensions, "
                "metrics, and default conditions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset": {
                        "type": "string",
                        "description": (
                            "Logical dataset name. "
                            "Options: sales_invoice, sales_invoice_item, "
                            "general_ledger, company, customer, item, "
                            "account, cost_center"
                        ),
                    }
                },
                "required": [],
            },
        ),
        handler=lambda args: describe_analytics_schema(
            args.get("dataset") if args else None
        ),
    )

    server.add_tool(
        types.Tool(
            name="analyze_sales",
            description=(
                "Analyze sales data from submitted sales invoices. "
                "Groups by a dimension and aggregates by a metric. "
                "Always uses docstatus = 1 (submitted invoices only)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "company": {
                        "type": "string",
                        "description": "Company name (required)",
                    },
                    "from_date": {
                        "type": "string",
                        "description": "Start date YYYY-MM-DD (required)",
                    },
                    "to_date": {
                        "type": "string",
                        "description": "End date YYYY-MM-DD (required)",
                    },
                    "group_by": {
                        "type": "string",
                        "enum": [
                            "customer",
                            "customer_group",
                            "territory",
                            "month",
                            "week",
                            "year",
                        ],
                        "description": "Grouping dimension",
                        "default": "month",
                    },
                    "metric": {
                        "type": "string",
                        "enum": [
                            "net_sales",
                            "gross_sales",
                            "invoice_count",
                            "qty",
                            "avg_net_rate",
                        ],
                        "description": "Metric to aggregate",
                        "default": "net_sales",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum rows returned (default 100)",
                        "default": 100,
                    },
                },
                "required": ["company", "from_date", "to_date"],
            },
        ),
        handler=lambda args: analyze_sales(
            company=args["company"],
            from_date=args["from_date"],
            to_date=args["to_date"],
            group_by=args.get("group_by", "month"),
            metric=args.get("metric", "net_sales"),
            limit=args.get("limit", 100),
        ),
    )

    server.add_tool(
        types.Tool(
            name="analyze_general_ledger",
            description=(
                "Analyze General Ledger entries from submitted GL entries. "
                "Groups by a dimension and calculates debit, credit, and net balance. "
                "Always uses docstatus = 1 (submitted entries only)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "company": {
                        "type": "string",
                        "description": "Company name (required)",
                    },
                    "from_date": {
                        "type": "string",
                        "description": "Start date YYYY-MM-DD (required)",
                    },
                    "to_date": {
                        "type": "string",
                        "description": "End date YYYY-MM-DD (required)",
                    },
                    "group_by": {
                        "type": "string",
                        "enum": [
                            "account",
                            "cost_center",
                            "voucher_type",
                            "month",
                            "week",
                            "year",
                        ],
                        "description": "Grouping dimension",
                        "default": "account",
                    },
                    "account": {
                        "type": "string",
                        "description": "Optional account name filter",
                    },
                    "cost_center": {
                        "type": "string",
                        "description": "Optional cost centre filter",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum rows returned (default 100)",
                        "default": 100,
                    },
                },
                "required": ["company", "from_date", "to_date"],
            },
        ),
        handler=lambda args: analyze_general_ledger(
            company=args["company"],
            from_date=args["from_date"],
            to_date=args["to_date"],
            group_by=args.get("group_by", "account"),
            account=args.get("account"),
            cost_center=args.get("cost_center"),
            limit=args.get("limit", 100),
        ),
    )

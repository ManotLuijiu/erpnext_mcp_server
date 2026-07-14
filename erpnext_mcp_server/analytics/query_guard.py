"""Analytics query guard module.

Provides validation of analytics queries and parameters
before execution against DuckDB.

Security model:
- SQL identifiers (table/column names) come ONLY from internal allowlists
- Query values are ALWAYS parameterized
- No arbitrary SQL is accepted
"""

from __future__ import annotations

import logging
import re

from erpnext_mcp_server.analytics.exceptions import AnalyticsValidationError

logger = logging.getLogger("erpnext_mcp_server.analytics")

# ---------------------------------------------------------------------------
# Allowlists
# ---------------------------------------------------------------------------

ALLOWED_TABLE_NAMES: frozenset[str] = frozenset(
    {
        "tabSales Invoice",
        "tabSales Invoice Item",
        "tabGL Entry",
        "tabCompany",
        "tabCustomer",
        "tabItem",
        "tabAccount",
        "tabCost Center",
    }
)

# Mapping from logical dataset name to physical Frappe table
DATASET_TABLE_MAP: dict[str, str] = {
    "sales_invoice": "tabSales Invoice",
    "sales_invoice_item": "tabSales Invoice Item",
    "general_ledger": "tabGL Entry",
    "company": "tabCompany",
    "customer": "tabCustomer",
    "item": "tabItem",
    "account": "tabAccount",
    "cost_center": "tabCost Center",
}

# Approved sales grouping dimensions
SALES_GROUP_BY_EXPRESSIONS: dict[str, str] = {
    "customer": "customer",
    "customer_group": "customer_group",
    "territory": "territory",
    "month": "DATE_TRUNC('month', posting_date)",
    "week": "DATE_TRUNC('week', posting_date)",
    "year": "DATE_TRUNC('year', posting_date)",
}

# Approved sales metrics
SALES_METRIC_EXPRESSIONS: dict[str, str] = {
    "net_sales": "SUM(base_net_amount)",
    "gross_sales": "SUM(baseGrossAmount)",
    "invoice_count": "COUNT(DISTINCT name)",
    "qty": "SUM(qty)",
    "avg_net_rate": "AVG(base_net_amount / NULLIF(qty, 0))",
}

# Approved GL grouping dimensions
GL_GROUP_BY_EXPRESSIONS: dict[str, str] = {
    "account": "account",
    "cost_center": "cost_center",
    "voucher_type": "voucher_type",
    "month": "DATE_TRUNC('month', posting_date)",
    "week": "DATE_TRUNC('week', posting_date)",
    "year": "DATE_TRUNC('year', posting_date)",
}

# ---------------------------------------------------------------------------
# QueryValidator
# ---------------------------------------------------------------------------


class QueryValidator:
    """Validates analytics query parameters before execution.

    Ensures that only allowlisted identifiers are used and that
    all values are passed as parameters.
    """

    # Matches any unquoted SQL identifier (table, column, alias)
    _IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

    # Matches a parameter placeholder
    _PARAM_RE = re.compile(r"\?\d*|\$\d+")

    def __init__(self) -> None:
        """Initialize the validator."""
        pass

    # -------------------------------------------------------------------------
    # Table / dataset validation
    # -------------------------------------------------------------------------

    def validate_dataset(self, dataset: str) -> str:
        """Validate and resolve a logical dataset name to a table name.

        Args:
            dataset: Logical dataset name (e.g., "sales_invoice").

        Returns:
            Physical Frappe table name (e.g., "tabSales Invoice").

        Raises:
            AnalyticsValidationError: If the dataset is not registered.
        """
        table = DATASET_TABLE_MAP.get(dataset)
        if table is None:
            allowed = ", ".join(sorted(DATASET_TABLE_MAP.keys()))
            raise AnalyticsValidationError(
                f"Unknown dataset '{dataset}'. Allowed: {allowed}", field="dataset"
            )
        if table not in ALLOWED_TABLE_NAMES:
            raise AnalyticsValidationError(
                f"Dataset '{dataset}' resolves to unregistered table '{table}'",
                field="dataset",
            )
        return table

    # -------------------------------------------------------------------------
    # SQL identifier validation
    # -------------------------------------------------------------------------

    def validate_identifier(self, identifier: str, field: str) -> None:
        """Validate a SQL identifier (column name, alias, etc.).

        Args:
            identifier: The identifier string to validate.
            field: Human-readable field name for error messages.

        Raises:
            AnalyticsValidationError: If the identifier is unsafe.
        """
        if not identifier or not identifier.strip():
            raise AnalyticsValidationError(f"{field} cannot be empty", field=field)

        # Must match simple identifier pattern
        if not self._IDENTIFIER_RE.match(identifier):
            raise AnalyticsValidationError(
                f"Invalid {field}: '{identifier}' — must be alphanumeric/underscore only",
                field=field,
            )

        # Block obviously dangerous identifiers
        dangerous = {"DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE"}
        if identifier.upper() in dangerous:
            raise AnalyticsValidationError(
                f"Dangerous {field}: '{identifier}'", field=field
            )

    def resolve_group_by(self, group_by: str, mapping: dict[str, str]) -> str:
        """Resolve a group-by dimension through an allowlist mapping.

        Args:
            group_by: Dimension key (e.g., "customer", "month").
            mapping: Approved dimension → SQL expression mapping.

        Returns:
            SQL expression for the grouping.

        Raises:
            AnalyticsValidationError: If the dimension is not allowlisted.
        """
        expr = mapping.get(group_by)
        if expr is None:
            allowed = ", ".join(sorted(mapping.keys()))
            raise AnalyticsValidationError(
                f"Invalid group_by '{group_by}'. Allowed: {allowed}", field="group_by"
            )
        return expr

    def resolve_metric(self, metric: str, mapping: dict[str, str]) -> str:
        """Resolve a metric through an allowlist mapping.

        Args:
            metric: Metric key (e.g., "net_sales").
            mapping: Approved metric → SQL expression mapping.

        Returns:
            SQL expression for the metric.

        Raises:
            AnalyticsValidationError: If the metric is not allowlisted.
        """
        expr = mapping.get(metric)
        if expr is None:
            allowed = ", ".join(sorted(mapping.keys()))
            raise AnalyticsValidationError(
                f"Invalid metric '{metric}'. Allowed: {allowed}", field="metric"
            )
        return expr

    # -------------------------------------------------------------------------
    # Parameter safety
    # -------------------------------------------------------------------------

    def check_no_raw_identifiers_in_query(
        self,
        query: str,
        reserved_keywords: tuple[str, ...] = (
            "DROP",
            "DELETE",
            "INSERT",
            "UPDATE",
            "ALTER",
            "CREATE",
            "TRUNCATE",
            "GRANT",
            "REVOKE",
            "EXECUTE",
        ),
    ) -> None:
        """Check that a query string does not contain dangerous raw identifiers.

        This is a defence-in-depth check. Identifiers should already be
        resolved through allowlist mappings. This catches accidental or
        malicious injection of table/column names into query strings.

        Args:
            query: The SQL query string to check.
            reserved_keywords: Keywords that must not appear unquoted.

        Raises:
            AnalyticsValidationError: If dangerous content is detected.
        """
        import re

        # Find quoted and unquoted segments
        # Remove single-line and multi-line comments
        safe_query = re.sub(r"--[^\n]*", "", query)
        safe_query = re.sub(r"/\*.*?\*/", "", safe_query, flags=re.DOTALL)
        # Remove string literals
        safe_query = re.sub(r"'[^']*'", "''", safe_query)
        # Remove double-quoted identifiers
        safe_query = re.sub(r'"[^"]*"', '""', safe_query)

        upper = safe_query.upper()

        for keyword in reserved_keywords:
            pattern = rf"\b{keyword}\b"
            if re.search(pattern, upper):
                raise AnalyticsValidationError(
                    f"Dangerous keyword '{keyword}' found in query"
                )

    # -------------------------------------------------------------------------
    # Date / range validation
    # -------------------------------------------------------------------------

    def validate_date_range(self, from_date: str, to_date: str) -> None:
        """Validate a date range.

        Args:
            from_date: Start date in YYYY-MM-DD format.
            to_date: End date in YYYY-MM-DD format.

        Raises:
            AnalyticsValidationError: If the range is invalid.
        """
        import datetime

        def parse_date(s: str) -> datetime.date:
            try:
                return datetime.date.fromisoformat(s)
            except ValueError:
                raise AnalyticsValidationError(
                    f"Invalid date format: '{s}'. Use YYYY-MM-DD.", field="date"
                )

        start = parse_date(from_date)
        end = parse_date(to_date)
        if start > end:
            raise AnalyticsValidationError(
                "from_date must not be after to_date", field="date_range"
            )

    def validate_company(self, company: str) -> str:
        """Validate company name.

        Args:
            company: Company name string.

        Returns:
            Stripped company name.

        Raises:
            AnalyticsValidationError: If empty.
        """
        stripped = company.strip()
        if not stripped:
            raise AnalyticsValidationError("company cannot be empty", field="company")
        return stripped

    def validate_limit(self, limit: int, max_rows: int) -> int:
        """Validate and bound the result limit.

        Args:
            limit: Requested limit.
            max_rows: Configured maximum rows.

        Returns:
            Safe bounded limit.
        """
        try:
            bound = int(limit)
        except (TypeError, ValueError):
            raise AnalyticsValidationError(
                f"Invalid limit: {limit!r}. Must be an integer.", field="limit"
            )
        if bound < 1:
            raise AnalyticsValidationError("limit must be at least 1", field="limit")
        return min(bound, max_rows)

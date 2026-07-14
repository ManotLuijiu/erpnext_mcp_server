"""Analytics result formatter module.

Converts DuckDB query results to JSON-compatible structures
for safe MCP responses.
"""

from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from erpnext_mcp_server.analytics.exceptions import AnalyticsQueryError


@dataclass(frozen=True)
class AnalyticsQueryResult:
    """Immutable result of an analytics query.

    Attributes:
        columns: Column names from the query result.
        rows: List of row dictionaries with column names as keys.
        row_count: Number of rows returned.
        duration_ms: Query execution duration in milliseconds.
        truncated: Whether the result was truncated due to row limit.
    """

    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    duration_ms: float
    truncated: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to a plain dictionary for JSON serialization."""
        return {
            "columns": self.columns,
            "rows": self.rows,
            "row_count": self.row_count,
            "duration_ms": self.duration_ms,
            "truncated": self.truncated,
        }


def _to_json_compatible(value: Any) -> Any:
    """Convert a DuckDB value to a JSON-compatible type.

    - datetime → ISO 8601 string
    - date     → ISO 8601 string
    - Decimal  → float (loss of precision is acceptable for analytics)
    - bytes   → base64-encoded string (rare, for binary fields)
    - None    → None
    - Other   → unchanged

    Args:
        value: Any value returned from DuckDB.

    Returns:
        A JSON-compatible representation of the value.
    """
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, date) and not isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, time):
        return value.isoformat()

    if isinstance(value, Decimal):
        # Convert Decimal to float; analytics precision is acceptable
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    if isinstance(value, bytes):
        # Encode binary as base64; rarely needed for Phase 1 analytics
        import base64

        return base64.b64encode(value).decode("ascii")

    # Primitives pass through unchanged
    return value


def format_query_result(
    cursor_description: list[tuple[str, ...]],
    cursor_rows: list[tuple[Any, ...]],
    duration_ms: float,
    max_rows: int,
) -> AnalyticsQueryResult:
    """Format a DuckDB cursor result into an AnalyticsQueryResult.

    Args:
        cursor_description: The ``cursor.description`` tuple list.
        cursor_rows: The ``cursor.fetchall()`` rows.
        duration_ms: Elapsed time in milliseconds.
        max_rows: Maximum allowed rows (used to detect truncation).

    Returns:
        An immutable AnalyticsQueryResult.

    Raises:
        AnalyticsQueryError: If the result cannot be formatted.
    """
    try:
        columns = [desc[0] for desc in cursor_description]
    except Exception as e:
        raise AnalyticsQueryError(f"Failed to read cursor description: {e}")

    try:
        truncated = len(cursor_rows) > max_rows
        capped_rows = cursor_rows[:max_rows]

        rows = [
            {col: _to_json_compatible(val) for col, val in zip(columns, db_row)}
            for db_row in capped_rows
        ]
    except Exception as e:
        raise AnalyticsQueryError(f"Failed to format query rows: {e}")

    return AnalyticsQueryResult(
        columns=columns,
        rows=rows,
        row_count=len(rows),
        duration_ms=round(duration_ms, 2),
        truncated=truncated,
    )


class ResultFormatter:
    """Formatter for analytics query results.

    Provides a configurable formatter that respects the
    configured maximum row limit.
    """

    def __init__(self, max_rows: int) -> None:
        """Initialize the formatter.

        Args:
            max_rows: Maximum rows per result.
        """
        if max_rows < 1:
            raise ValueError("max_rows must be at least 1")
        self._max_rows = max_rows

    @property
    def max_rows(self) -> int:
        """Configured maximum rows."""
        return self._max_rows

    def format(
        self,
        cursor_description: list[tuple[str, ...]],
        cursor_rows: list[tuple[Any, ...]],
        duration_ms: float,
    ) -> AnalyticsQueryResult:
        """Format cursor result.

        Args:
            cursor_description: DuckDB cursor description.
            cursor_rows: DuckDB fetched rows.
            duration_ms: Elapsed time in milliseconds.

        Returns:
            Formatted AnalyticsQueryResult.
        """
        return format_query_result(
            cursor_description, cursor_rows, duration_ms, self._max_rows
        )

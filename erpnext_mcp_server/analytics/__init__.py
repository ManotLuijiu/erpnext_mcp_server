"""DuckDB Analytics Layer for ERPNext MCP Server.

This module provides a read-only analytical layer using DuckDB to query
MariaDB data. It is strictly for analytical queries (aggregations, KPIs,
GL analysis, sales analysis, inventory analysis) and does not replace
the transactional MariaDB database.

Security model:
- DuckDB is read-only
- MariaDB is attached with SELECT-only user
- No arbitrary SQL execution
- All queries use parameterized values
- SQL identifiers come from internal allowlists
"""

from erpnext_mcp_server.analytics.configuration import AnalyticsConfiguration
from erpnext_mcp_server.analytics.exceptions import (
    AnalyticsConfigurationError,
    AnalyticsConnectionError,
    AnalyticsDisabledError,
    AnalyticsError,
    AnalyticsQueryError,
    AnalyticsValidationError,
)

__all__ = [
    "AnalyticsConfiguration",
    "AnalyticsError",
    "AnalyticsConfigurationError",
    "AnalyticsConnectionError",
    "AnalyticsDisabledError",
    "AnalyticsQueryError",
    "AnalyticsValidationError",
]

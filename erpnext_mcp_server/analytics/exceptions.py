"""Analytics exceptions module.

Defines specific exception types for the analytics layer to enable
precise error handling and safe error responses to MCP clients.
"""


class AnalyticsError(Exception):
    """Base exception for all analytics errors."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code or "ANALYTICS_ERROR"
        self.message = message


class AnalyticsDisabledError(AnalyticsError):
    """Raised when DuckDB analytics is disabled."""

    def __init__(self, message: str = "DuckDB analytics is disabled") -> None:
        super().__init__(message, code="ANALYTICS_DISABLED")


class AnalyticsConfigurationError(AnalyticsError):
    """Raised when analytics configuration is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="ANALYTICS_CONFIG_ERROR")


class AnalyticsConnectionError(AnalyticsError):
    """Raised when connection to DuckDB or MariaDB fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="ANALYTICS_CONNECTION_ERROR")


class AnalyticsValidationError(AnalyticsError):
    """Raised when query parameters or validation fails."""

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message, code="ANALYTICS_VALIDATION_ERROR")
        self.field = field


class AnalyticsQueryError(AnalyticsError):
    """Raised when a query execution fails."""

    def __init__(self, message: str, query_type: str | None = None) -> None:
        super().__init__(message, code="ANALYTICS_QUERY_ERROR")
        self.query_type = query_type

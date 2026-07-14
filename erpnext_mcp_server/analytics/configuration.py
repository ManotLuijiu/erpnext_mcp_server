"""Analytics configuration module.

Provides typed configuration for DuckDB analytics using environment variables.
All configuration values are validated before use.
"""

from dataclasses import dataclass
from typing import Final

from erpnext_mcp_server.analytics.exceptions import AnalyticsConfigurationError

# Environment variable names
ENV_ENABLED: Final[str] = "MCP_ANALYTICS_ENABLED"
ENV_DB_HOST: Final[str] = "MCP_ANALYTICS_DB_HOST"
ENV_DB_PORT: Final[str] = "MCP_ANALYTICS_DB_PORT"
ENV_DB_NAME: Final[str] = "MCP_ANALYTICS_DB_NAME"
ENV_DB_USER: Final[str] = "MCP_ANALYTICS_DB_USER"
ENV_DB_PASSWORD: Final[str] = "MCP_ANALYTICS_DB_PASSWORD"
ENV_MAX_ROWS: Final[str] = "MCP_ANALYTICS_MAX_ROWS"
ENV_QUERY_TIMEOUT: Final[str] = "MCP_ANALYTICS_QUERY_TIMEOUT_SECONDS"
ENV_MEMORY_LIMIT: Final[str] = "MCP_ANALYTICS_MEMORY_LIMIT"
ENV_THREADS: Final[str] = "MCP_ANALYTICS_THREADS"

# Default values
DEFAULT_ENABLED: Final[bool] = False
DEFAULT_DB_HOST: Final[str] = "127.0.0.1"
DEFAULT_DB_PORT: Final[int] = 3306
DEFAULT_MAX_ROWS: Final[int] = 500
DEFAULT_QUERY_TIMEOUT: Final[int] = 30
DEFAULT_MEMORY_LIMIT: Final[str] = "1GB"
DEFAULT_THREADS: Final[int] = 2

# Limits
MIN_PORT: Final[int] = 1
MAX_PORT: Final[int] = 65535
MIN_MAX_ROWS: Final[int] = 1
MAX_MAX_ROWS: Final[int] = 10000
MIN_TIMEOUT: Final[int] = 1
MAX_TIMEOUT: Final[int] = 300
MIN_THREADS: Final[int] = 1
MAX_THREADS: Final[int] = 32


@dataclass(frozen=True)
class AnalyticsConfiguration:
    """Immutable configuration for DuckDB analytics.

    Attributes:
        enabled: Whether analytics is enabled.
        host: MariaDB host address.
        port: MariaDB port number.
        database: MariaDB database name.
        user: MariaDB username (must have SELECT-only privileges).
        password: MariaDB password.
        max_rows: Maximum rows to return per query.
        query_timeout_seconds: Query timeout in seconds.
        memory_limit: DuckDB memory limit (e.g., "1GB", "2GB").
        threads: Number of DuckDB threads.
    """

    enabled: bool
    host: str
    port: int
    database: str
    user: str
    password: str
    max_rows: int
    query_timeout_seconds: int
    memory_limit: str
    threads: int


def load_configuration() -> AnalyticsConfiguration:
    """Load and validate analytics configuration from environment variables.

    Returns:
        Validated AnalyticsConfiguration instance.

    Raises:
        AnalyticsConfigurationError: If configuration is invalid.

    Note:
        Password is not included in error messages for security.
    """
    import os

    # Parse enabled flag
    enabled_str = os.environ.get(ENV_ENABLED, "").lower().strip()
    enabled = DEFAULT_ENABLED
    if enabled_str in ("true", "1", "yes"):
        enabled = True
    elif enabled_str in ("false", "0", "no", ""):
        enabled = False
    else:
        raise AnalyticsConfigurationError(
            f"Invalid value for {ENV_ENABLED}: must be true/false/1/0/yes/no"
        )

    # Parse host
    host = os.environ.get(ENV_DB_HOST, DEFAULT_DB_HOST).strip()
    if not host:
        host = DEFAULT_DB_HOST

    # Parse port
    port_str = os.environ.get(ENV_DB_PORT, str(DEFAULT_DB_PORT)).strip()
    try:
        port = int(port_str)
    except ValueError:
        raise AnalyticsConfigurationError(
            f"Invalid port for {ENV_DB_PORT}: must be an integer"
        )
    if not (MIN_PORT <= port <= MAX_PORT):
        raise AnalyticsConfigurationError(
            f"Port must be between {MIN_PORT} and {MAX_PORT}"
        )

    # Parse database name (required when enabled)
    database = os.environ.get(ENV_DB_NAME, "").strip()
    if enabled and not database:
        raise AnalyticsConfigurationError(
            f"{ENV_DB_NAME} is required when analytics is enabled"
        )

    # Parse username (required when enabled)
    user = os.environ.get(ENV_DB_USER, "").strip()
    if enabled and not user:
        raise AnalyticsConfigurationError(
            f"{ENV_DB_USER} is required when analytics is enabled"
        )

    # Parse password (required when enabled)
    password = os.environ.get(ENV_DB_PASSWORD, "").strip()
    if enabled and not password:
        raise AnalyticsConfigurationError(
            f"{ENV_DB_PASSWORD} is required when analytics is enabled"
        )

    # Parse max_rows
    max_rows_str = os.environ.get(ENV_MAX_ROWS, str(DEFAULT_MAX_ROWS)).strip()
    try:
        max_rows = int(max_rows_str)
    except ValueError:
        raise AnalyticsConfigurationError(
            f"Invalid value for {ENV_MAX_ROWS}: must be an integer"
        )
    if not (MIN_MAX_ROWS <= max_rows <= MAX_MAX_ROWS):
        raise AnalyticsConfigurationError(
            f"max_rows must be between {MIN_MAX_ROWS} and {MAX_MAX_ROWS}"
        )

    # Parse query timeout
    timeout_str = os.environ.get(ENV_QUERY_TIMEOUT, str(DEFAULT_QUERY_TIMEOUT)).strip()
    try:
        query_timeout = int(timeout_str)
    except ValueError:
        raise AnalyticsConfigurationError(
            f"Invalid value for {ENV_QUERY_TIMEOUT}: must be an integer"
        )
    if not (MIN_TIMEOUT <= query_timeout <= MAX_TIMEOUT):
        raise AnalyticsConfigurationError(
            f"query_timeout_seconds must be between {MIN_TIMEOUT} and {MAX_TIMEOUT}"
        )

    # Parse memory limit
    memory_limit = os.environ.get(ENV_MEMORY_LIMIT, DEFAULT_MEMORY_LIMIT).strip()
    if not memory_limit:
        memory_limit = DEFAULT_MEMORY_LIMIT

    # Parse threads
    threads_str = os.environ.get(ENV_THREADS, str(DEFAULT_THREADS)).strip()
    try:
        threads = int(threads_str)
    except ValueError:
        raise AnalyticsConfigurationError(
            f"Invalid value for {ENV_THREADS}: must be an integer"
        )
    if not (MIN_THREADS <= threads <= MAX_THREADS):
        raise AnalyticsConfigurationError(
            f"threads must be between {MIN_THREADS} and {MAX_THREADS}"
        )

    return AnalyticsConfiguration(
        enabled=enabled,
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
        max_rows=max_rows,
        query_timeout_seconds=query_timeout,
        memory_limit=memory_limit,
        threads=threads,
    )


# Global configuration instance (lazy loaded)
_config: AnalyticsConfiguration | None = None


def get_configuration() -> AnalyticsConfiguration:
    """Get the global analytics configuration.

    Loads configuration from environment on first call.

    Returns:
        Validated AnalyticsConfiguration instance.
    """
    global _config
    if _config is None:
        _config = load_configuration()
    return _config


def reset_configuration() -> None:
    """Reset the global configuration.

    Useful for testing.
    """
    global _config
    _config = None

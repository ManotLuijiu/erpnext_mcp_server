"""DuckDB analytics connection manager.

Provides a thread-safe connection to DuckDB with a MariaDB
read-only attachment for Phase 1 analytics.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import TYPE_CHECKING, Any

import duckdb

from erpnext_mcp_server.analytics.exceptions import (
    AnalyticsConnectionError,
    AnalyticsDisabledError,
)

if TYPE_CHECKING:
    from erpnext_mcp_server.analytics.configuration import AnalyticsConfiguration

logger = logging.getLogger("erpnext_mcp_server.analytics")


class DuckDBAnalyticsConnection:
    """Manages DuckDB in-memory connection with MariaDB attachment.

    Phase 1: In-memory DuckDB, MySQL extension, MariaDB attached READ_ONLY.

    Thread-safety: Uses a lock around connection creation and queries
    to avoid sharing a single connection across threads. A new connection
    is created per-thread on first use (thread-local).

    Attributes:
        config: The analytics configuration instance.
    """

    def __init__(self, config: "AnalyticsConfiguration") -> None:
        """Initialize the connection manager.

        Args:
            config: Validated analytics configuration.

        Raises:
            AnalyticsDisabledError: If analytics is disabled.
            AnalyticsConnectionError: If DuckDB cannot be imported.
        """
        self._config = config
        self._lock = threading.RLock()
        self._local = threading.local()
        self._closed = False

        if not config.enabled:
            raise AnalyticsDisabledError("DuckDB analytics is disabled")

        # Verify DuckDB is available
        try:
            duckdb.__version__  # type: ignore[unused-ignore]
        except Exception as e:
            raise AnalyticsConnectionError(f"DuckDB is not available: {e}") from e

        logger.info(
            "DuckDBAnalyticsConnection initialised for %s:%s/%s",
            config.host,
            config.port,
            config.database,
        )

    @property
    def config(self) -> "AnalyticsConfiguration":
        """Return the configuration (read-only)."""
        return self._config

    # -------------------------------------------------------------------------
    # Connection lifecycle
    # -------------------------------------------------------------------------

    def _create_connection(self) -> duckdb.DuckDBPyConnection:
        """Create a new DuckDB connection with MariaDB attachment.

        Returns:
            A configured DuckDBPyConnection.

        Raises:
            AnalyticsConnectionError: On failure.
        """
        try:
            conn = duckdb.connect(database=":memory:", read_only=False)
        except Exception as e:
            raise AnalyticsConnectionError(
                f"Failed to create DuckDB in-memory database: {e}"
            ) from e

        try:
            # Apply memory and thread settings
            conn.execute("SET memory_limit = ?", (f"{self._config.memory_limit}",))
            conn.execute("SET threads = ?", (self._config.threads,))

            # Load MySQL extension (install if not cached)
            try:
                conn.execute("INSTALL mysql_scanner")
            except Exception:
                logger.warning(
                    "INSTALL mysql_scanner failed; extension may already be installed"
                )

            try:
                conn.execute("LOAD mysql_scanner")
            except Exception as e:
                raise AnalyticsConnectionError(
                    f"Failed to LOAD mysql_scanner extension: {e}"
                ) from e

            # Attach MariaDB as frappe_db in READ_ONLY mode
            dsn = (
                f"mysql://{self._config.user}:{self._config.password}"
                f"@{self._config.host}:{self._config.port}/{self._config.database}"
            )

            try:
                conn.execute(
                    f"CREATE OR REPLACE DATABASE frappe_db "
                    f"AS (TYPE mysql, DSN '{dsn}') READ_ONLY"
                )
            except Exception as e:
                raise AnalyticsConnectionError(
                    f"Failed to attach MariaDB as frappe_db (READ_ONLY): {e}"
                ) from e

            logger.info(
                "MariaDB attached as frappe_db (READ_ONLY) for %s/%s",
                self._config.host,
                self._config.database,
            )

            return conn

        except AnalyticsConnectionError:
            conn.close()
            raise
        except Exception as e:
            try:
                conn.close()
            except Exception:
                pass
            raise AnalyticsConnectionError(
                f"Unexpected error during DuckDB setup: {e}"
            ) from e

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """Get a DuckDB connection for the current thread.

        Lazily creates a thread-local connection on first call.

        Returns:
            DuckDBPyConnection for the current thread.

        Raises:
            AnalyticsConnectionError: If the connection is closed or creation fails.
        """
        if self._closed:
            raise AnalyticsConnectionError("Connection manager is closed")

        with self._lock:
            conn = getattr(self._local, "conn", None)

        if conn is not None:
            return conn

        conn = self._create_connection()

        with self._lock:
            self._local.conn = conn

        return conn

    def close(self) -> None:
        """Close the connection for the current thread."""
        with self._lock:
            conn = getattr(self._local, "conn", None)

        if conn is not None:
            try:
                conn.close()
            except Exception as e:
                logger.warning("Error closing DuckDB connection: %s", e)

        with self._lock:
            self._local.conn = None  # type: ignore[attr-defined]
            self._closed = True

    # -------------------------------------------------------------------------
    # Query execution
    # -------------------------------------------------------------------------

    def execute(
        self, query: str, parameters: tuple[Any, ...] | None = None
    ) -> duckdb.DuckDBPyConnection:
        """Execute a query on DuckDB.

        Args:
            query: SQL query string.
            parameters: Optional query parameters.

        Returns:
            The connection (for cursor access).

        Raises:
            AnalyticsConnectionError: On query failure.
        """
        conn = self.get_connection()
        try:
            if parameters:
                conn.execute(query, parameters=parameters)
            else:
                conn.execute(query)
            return conn
        except Exception as e:
            raise AnalyticsConnectionError(f"Query execution failed: {e}") from e

    # -------------------------------------------------------------------------
    # Health check
    # -------------------------------------------------------------------------

    def health_check(self) -> dict[str, Any]:
        """Run a health check on DuckDB and MariaDB attachment.

        Returns:
            A dictionary with health status information.
            Does not expose credentials.
        """
        if self._closed:
            return {
                "enabled": False,
                "connected": False,
                "message": "Connection manager is closed",
            }

        try:
            conn = self.get_connection()
            start = time.perf_counter()
            # Simple health check: count tables in frappe_db schema
            result = conn.execute(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = 'frappe_db'"
            ).fetchone()
            elapsed = (time.perf_counter() - start) * 1000

            return {
                "enabled": True,
                "engine": "DuckDB",
                "duckdb_version": str(
                    next(
                        iter(
                            conn.execute("SELECT duckdb_version()").fetchone()
                            or ("unknown",)
                        )
                    )
                ),
                "source": "MariaDB",
                "attachment_mode": "read_only",
                "connected": True,
                "database_alias": "frappe_db",
                "max_rows": self._config.max_rows,
                "health_check_ms": round(elapsed, 2),
                "visible_tables_estimate": result[0] if result else 0,
            }
        except Exception as e:
            logger.error("Health check failed: %s", e)
            return {
                "enabled": True,
                "connected": False,
                "message": f"Health check failed: {e}",
            }

    # -------------------------------------------------------------------------
    # Context manager support
    # -------------------------------------------------------------------------

    def __enter__(self) -> "DuckDBAnalyticsConnection":
        """Enter context manager."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Exit context manager."""
        self.close()

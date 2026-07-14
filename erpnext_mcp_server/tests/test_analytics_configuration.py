"""Tests for analytics configuration module."""

import os
from unittest.mock import patch


def _reset_config():
    """Reset module-level config between tests."""
    # Clear any cached configuration by patching the module-level variable
    import erpnext_mcp_server.analytics.configuration as cfg

    cfg._config = None


class TestAnalyticsConfiguration:
    """Tests for AnalyticsConfiguration dataclass and load_configuration()."""

    def test_enabled_true_sets_flag(self):
        """MCP_ANALYTICS_ENABLED=true sets enabled=True."""
        _reset_config()
        with patch.dict(
            os.environ,
            {
                "MCP_ANALYTICS_ENABLED": "true",
                "MCP_ANALYTICS_DB_HOST": "127.0.0.1",
                "MCP_ANALYTICS_DB_PORT": "3306",
                "MCP_ANALYTICS_DB_NAME": "test_db",
                "MCP_ANALYTICS_DB_USER": "test_user",
                "MCP_ANALYTICS_DB_PASSWORD": "test_pass",
            },
            clear=False,
        ):
            from erpnext_mcp_server.analytics.configuration import load_configuration

            config = load_configuration()
            assert config.enabled is True

    def test_disabled_by_default(self):
        """When MCP_ANALYTICS_ENABLED is not set, analytics is disabled."""
        _reset_config()
        with patch.dict(os.environ, {}, clear=False):
            # Remove any existing env vars
            for key in [
                "MCP_ANALYTICS_ENABLED",
                "MCP_ANALYTICS_DB_HOST",
                "MCP_ANALYTICS_DB_PORT",
                "MCP_ANALYTICS_DB_NAME",
                "MCP_ANALYTICS_DB_USER",
                "MCP_ANALYTICS_DB_PASSWORD",
            ]:
                os.environ.pop(key, None)
            from erpnext_mcp_server.analytics.configuration import load_configuration

            config = load_configuration()
            assert config.enabled is False

    def test_enabled_requires_db_name(self):
        """When enabled, database name must be provided."""
        _reset_config()
        with patch.dict(
            os.environ,
            {
                "MCP_ANALYTICS_ENABLED": "true",
                "MCP_ANALYTICS_DB_HOST": "127.0.0.1",
                "MCP_ANALYTICS_DB_PORT": "3306",
                "MCP_ANALYTICS_DB_NAME": "",
                "MCP_ANALYTICS_DB_USER": "test_user",
                "MCP_ANALYTICS_DB_PASSWORD": "test_pass",
            },
            clear=False,
        ):
            from erpnext_mcp_server.analytics.configuration import load_configuration
            from erpnext_mcp_server.analytics.exceptions import (
                AnalyticsConfigurationError,
            )

            try:
                load_configuration()
                raise AssertionError("Expected AnalyticsConfigurationError")
            except AnalyticsConfigurationError as e:
                assert "MCP_ANALYTICS_DB_NAME" in str(e)

    def test_enabled_requires_user(self):
        """When enabled, user must be provided."""
        _reset_config()
        with patch.dict(
            os.environ,
            {
                "MCP_ANALYTICS_ENABLED": "true",
                "MCP_ANALYTICS_DB_HOST": "127.0.0.1",
                "MCP_ANALYTICS_DB_PORT": "3306",
                "MCP_ANALYTICS_DB_NAME": "test_db",
                "MCP_ANALYTICS_DB_USER": "",
                "MCP_ANALYTICS_DB_PASSWORD": "test_pass",
            },
            clear=False,
        ):
            from erpnext_mcp_server.analytics.configuration import load_configuration
            from erpnext_mcp_server.analytics.exceptions import (
                AnalyticsConfigurationError,
            )

            try:
                load_configuration()
                raise AssertionError("Expected AnalyticsConfigurationError")
            except AnalyticsConfigurationError as e:
                assert "MCP_ANALYTICS_DB_USER" in str(e)

    def test_enabled_requires_password(self):
        """When enabled, password must be provided."""
        _reset_config()
        with patch.dict(
            os.environ,
            {
                "MCP_ANALYTICS_ENABLED": "true",
                "MCP_ANALYTICS_DB_HOST": "127.0.0.1",
                "MCP_ANALYTICS_DB_PORT": "3306",
                "MCP_ANALYTICS_DB_NAME": "test_db",
                "MCP_ANALYTICS_DB_USER": "test_user",
                "MCP_ANALYTICS_DB_PASSWORD": "",
            },
            clear=False,
        ):
            from erpnext_mcp_server.analytics.configuration import load_configuration
            from erpnext_mcp_server.analytics.exceptions import (
                AnalyticsConfigurationError,
            )

            try:
                load_configuration()
                raise AssertionError("Expected AnalyticsConfigurationError")
            except AnalyticsConfigurationError as e:
                assert "MCP_ANALYTICS_DB_PASSWORD" in str(e)

    def test_invalid_port_raises(self):
        """Invalid port number raises AnalyticsConfigurationError."""
        _reset_config()
        with patch.dict(
            os.environ,
            {
                "MCP_ANALYTICS_ENABLED": "true",
                "MCP_ANALYTICS_DB_HOST": "127.0.0.1",
                "MCP_ANALYTICS_DB_PORT": "99999",
                "MCP_ANALYTICS_DB_NAME": "test_db",
                "MCP_ANALYTICS_DB_USER": "test_user",
                "MCP_ANALYTICS_DB_PASSWORD": "test_pass",
            },
            clear=False,
        ):
            from erpnext_mcp_server.analytics.configuration import load_configuration
            from erpnext_mcp_server.analytics.exceptions import (
                AnalyticsConfigurationError,
            )

            try:
                load_configuration()
                raise AssertionError("Expected AnalyticsConfigurationError")
            except AnalyticsConfigurationError as e:
                assert "Port" in str(e)

    def test_port_non_integer_raises(self):
        """Non-integer port raises AnalyticsConfigurationError."""
        _reset_config()
        with patch.dict(
            os.environ,
            {
                "MCP_ANALYTICS_ENABLED": "true",
                "MCP_ANALYTICS_DB_HOST": "127.0.0.1",
                "MCP_ANALYTICS_DB_PORT": "abc",
                "MCP_ANALYTICS_DB_NAME": "test_db",
                "MCP_ANALYTICS_DB_USER": "test_user",
                "MCP_ANALYTICS_DB_PASSWORD": "test_pass",
            },
            clear=False,
        ):
            from erpnext_mcp_server.analytics.configuration import load_configuration
            from erpnext_mcp_server.analytics.exceptions import (
                AnalyticsConfigurationError,
            )

            try:
                load_configuration()
                raise AssertionError("Expected AnalyticsConfigurationError")
            except AnalyticsConfigurationError as e:
                assert "port" in str(e).lower()

    def test_invalid_max_rows_raises(self):
        """max_rows outside 1-10000 range raises AnalyticsConfigurationError."""
        _reset_config()
        with patch.dict(
            os.environ,
            {
                "MCP_ANALYTICS_ENABLED": "true",
                "MCP_ANALYTICS_DB_HOST": "127.0.0.1",
                "MCP_ANALYTICS_DB_PORT": "3306",
                "MCP_ANALYTICS_DB_NAME": "test_db",
                "MCP_ANALYTICS_DB_USER": "test_user",
                "MCP_ANALYTICS_DB_PASSWORD": "test_pass",
                "MCP_ANALYTICS_MAX_ROWS": "99999",
            },
            clear=False,
        ):
            from erpnext_mcp_server.analytics.configuration import load_configuration
            from erpnext_mcp_server.analytics.exceptions import (
                AnalyticsConfigurationError,
            )

            try:
                load_configuration()
                raise AssertionError("Expected AnalyticsConfigurationError")
            except AnalyticsConfigurationError as e:
                assert "max_rows" in str(e).lower()

    def test_invalid_timeout_raises(self):
        """query_timeout outside 1-300 range raises AnalyticsConfigurationError."""
        _reset_config()
        with patch.dict(
            os.environ,
            {
                "MCP_ANALYTICS_ENABLED": "true",
                "MCP_ANALYTICS_DB_HOST": "127.0.0.1",
                "MCP_ANALYTICS_DB_PORT": "3306",
                "MCP_ANALYTICS_DB_NAME": "test_db",
                "MCP_ANALYTICS_DB_USER": "test_user",
                "MCP_ANALYTICS_DB_PASSWORD": "test_pass",
                "MCP_ANALYTICS_QUERY_TIMEOUT_SECONDS": "0",
            },
            clear=False,
        ):
            from erpnext_mcp_server.analytics.configuration import load_configuration
            from erpnext_mcp_server.analytics.exceptions import (
                AnalyticsConfigurationError,
            )

            try:
                load_configuration()
                raise AssertionError("Expected AnalyticsConfigurationError")
            except AnalyticsConfigurationError as e:
                assert "timeout" in str(e).lower()

    def test_invalid_threads_raises(self):
        """threads outside 1-32 range raises AnalyticsConfigurationError."""
        _reset_config()
        with patch.dict(
            os.environ,
            {
                "MCP_ANALYTICS_ENABLED": "true",
                "MCP_ANALYTICS_DB_HOST": "127.0.0.1",
                "MCP_ANALYTICS_DB_PORT": "3306",
                "MCP_ANALYTICS_DB_NAME": "test_db",
                "MCP_ANALYTICS_DB_USER": "test_user",
                "MCP_ANALYTICS_DB_PASSWORD": "test_pass",
                "MCP_ANALYTICS_THREADS": "99",
            },
            clear=False,
        ):
            from erpnext_mcp_server.analytics.configuration import load_configuration
            from erpnext_mcp_server.analytics.exceptions import (
                AnalyticsConfigurationError,
            )

            try:
                load_configuration()
                raise AssertionError("Expected AnalyticsConfigurationError")
            except AnalyticsConfigurationError as e:
                assert "threads" in str(e).lower()

    def test_password_not_in_exception_message(self):
        """Password is not included in exception messages."""
        _reset_config()
        with patch.dict(
            os.environ,
            {
                "MCP_ANALYTICS_ENABLED": "true",
                "MCP_ANALYTICS_DB_HOST": "127.0.0.1",
                "MCP_ANALYTICS_DB_PORT": "abc",
                "MCP_ANALYTICS_DB_NAME": "test_db",
                "MCP_ANALYTICS_DB_USER": "test_user",
                "MCP_ANALYTICS_DB_PASSWORD": "super_secret_password_123",
            },
            clear=False,
        ):
            from erpnext_mcp_server.analytics.configuration import load_configuration
            from erpnext_mcp_server.analytics.exceptions import (
                AnalyticsConfigurationError,
            )

            try:
                load_configuration()
            except AnalyticsConfigurationError as e:
                assert "super_secret_password_123" not in str(e)

    def test_valid_full_config(self):
        """Full valid configuration is parsed correctly."""
        _reset_config()
        with patch.dict(
            os.environ,
            {
                "MCP_ANALYTICS_ENABLED": "true",
                "MCP_ANALYTICS_DB_HOST": "db.example.com",
                "MCP_ANALYTICS_DB_PORT": "3307",
                "MCP_ANALYTICS_DB_NAME": "erpnext_prod",
                "MCP_ANALYTICS_DB_USER": "analytics_ro",
                "MCP_ANALYTICS_DB_PASSWORD": "readonly_pass",
                "MCP_ANALYTICS_MAX_ROWS": "1000",
                "MCP_ANALYTICS_QUERY_TIMEOUT_SECONDS": "60",
                "MCP_ANALYTICS_MEMORY_LIMIT": "4GB",
                "MCP_ANALYTICS_THREADS": "4",
            },
            clear=False,
        ):
            from erpnext_mcp_server.analytics.configuration import load_configuration

            config = load_configuration()
            assert config.enabled is True
            assert config.host == "db.example.com"
            assert config.port == 3307
            assert config.database == "erpnext_prod"
            assert config.user == "analytics_ro"
            assert config.password == "readonly_pass"
            assert config.max_rows == 1000
            assert config.query_timeout_seconds == 60
            assert config.memory_limit == "4GB"
            assert config.threads == 4

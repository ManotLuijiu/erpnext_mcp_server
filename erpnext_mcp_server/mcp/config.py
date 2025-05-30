"""
MCP Server Configuration and Setup
Configuration management and initialization for ERPNext MCP Server
"""

import os
import sys
import frappe
from pathlib import Path


class MCPConfig:
    """Configuration management for MCP server."""

    def __init__(self) -> None:
        self.app_name = "erpnext_mcp_server"
        self.server_name = "erpnext-mcp-server"
        self.server_version = "0.0.1"

        # Security settings
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.allowed_file_extensions = {
            ".txt",
            ".md",
            ".rst",
            ".json",
            ".yml",
            ".yaml",
            ".py",
            ".js",
            ".html",
            ".css",
            ".scss",
            ".xml",
            ".cfg",
            ".conf",
            ".ini",
            ".log",
            ".sql",
        }

        # Command timeouts
        self.command_timeout = 30  # seconds
        self.sql_query_limit = 100  # default row limit

        # Safe directories (relative to bench)
        self.safe_directories = [
            "sites",
            "apps",
            "logs",
            "config",
            "env",
            "public",
            "private",
            "backups",
            "archives",
        ]

        # Allowed bench commands
        self.allowed_bench_commands = {
            "version": "Show bench and app versions",
            "status": "Show process status",
            "list-apps": "List installed applications",
            "doctor": "Run system health check",
            "config": "Show configuration",
            "show-config": "Show site configuration",
        }

    def get_server_path(self) -> Path:
        """Get path to MCP server script."""
        return Path(frappe.get_app_path(self.app_name)) / "mcp" / "server.py"

    def get_safe_base_paths(self) -> list[str]:
        """Get list of safe base paths for file operations."""
        return [
            frappe.get_site_path(),  # Current site
            frappe.get_site_path(".."),  # Sites directory
            frappe.get_site_path("../.."),  # Bench directory
        ]

    def is_development_mode(self) -> bool:
        """Check if running in development mode."""
        return getattr(frappe.conf, "developer_mode", False)

    def get_environment_variables(self) -> dict[str, str]:
        """Get environment variables for MCP server process."""
        env = os.environ.copy()
        env.update(
            {
                "FRAPPE_SITE": frappe.local.site,
                "MCP_SERVER_NAME": self.server_name,
                "MCP_DEBUG": str(self.is_development_mode()),
            }
        )
        return env


def setup_mcp_server():
    """Initialize MCP server setup."""
    config = MCPConfig()

    # Verify server script exists
    server_path = config.get_server_path()
    if not server_path.exists():
        frappe.throw(f"MCP server script not found: {server_path}")

    # Check permissions
    if not frappe.has_permission("System Settings", "read"):
        frappe.throw("Insufficient permissions to access MCP server")

    return config


def validate_mcp_environment():
    """Validate that the environment is properly set up for MCP."""
    try:
        # Check if required Python packages are available
        import mcp.server.stdio
        import mcp.types
        from mcp.server.lowlevel import Server

        # Check Frappe environment
        if not frappe.db:
            frappe.throw("Database connection not available")

        # Check site access
        if not frappe.local.site:
            frappe.throw("Site context not available")

        return True

    except ImportError as e:
        frappe.throw(f"MCP dependencies not installed: {str(e)}")
    except Exception as e:
        frappe.throw(f"Environment validation failed: {str(e)}")


# Export configuration instance
mcp_config = MCPConfig()

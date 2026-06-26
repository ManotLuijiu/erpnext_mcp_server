"""
MCP Server Configuration for ERPNext
No Frappe imports at module level - pure Python config
"""

import os
from pathlib import Path
from typing import List


class MCPConfig:
    """Configuration management for MCP server - no Frappe dependency."""

    def __init__(self) -> None:
        self.app_name = "erpnext_mcp_server"
        self.server_name = "erpnext-mcp-server"
        self.server_version = "1.0.0"

        # Get default site from environment
        self.default_site = os.getenv("FRAPPE_SITE", "")

        # Security settings
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.sql_query_limit = 100
        self.command_timeout = 30  # seconds

        # Allowed file extensions
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
            ".csv",
            ".tsv",
            ".env",
            ".gitignore",
        }

        # Safe directories
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

        # Allowed bench commands (read-only operations)
        self.allowed_bench_commands = {
            "version": "Show bench and app versions",
            "status": "Show process status",
            "list-apps": "List installed applications",
            "doctor": "Run system health check",
            "config": "Show configuration",
            "show-config": "Show site configuration",
        }

    def get_default_site(self) -> str:
        """Get the default site from environment."""
        return self.default_site

    def set_default_site(self, site: str) -> None:
        """Set the default site."""
        self.default_site = site
        os.environ["FRAPPE_SITE"] = site

    def get_safe_base_paths(self, bench_path: str) -> List[str]:
        """Get list of safe base paths for file operations."""
        bench = Path(bench_path)
        return [
            str(bench / "sites"),
            str(bench / "apps"),
            str(bench / "logs"),
            str(bench / "config"),
        ]

    def is_safe_file_extension(self, filename: str) -> bool:
        """Check if file extension is allowed."""
        return Path(filename).suffix.lower() in self.allowed_file_extensions

    def is_safe_directory(self, path: str) -> bool:
        """Check if path is in safe directories."""
        parts = Path(path).parts
        if not parts:
            return False
        # Allow if first part is in safe_directories
        return parts[0] in self.safe_directories


# Global config instance
mcp_config = MCPConfig()

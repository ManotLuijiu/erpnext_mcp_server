"""
Claude Desktop Integration for ERPNext MCP Server

This module provides utilities for registering the ERPNext MCP server with
the Claude desktop app, making it available as a tool for Claude.

Usage:
    # Register the server with Claude
    python -m erpnext_mcp_server.claude_integration install

    # Unregister the server from Claude
    python -m erpnext_mcp_server.claude_integration uninstall
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Import Claude utilities if available
try:
    from mcp.cli.claude import get_claude_config_path, update_claude_config
except ImportError:
    # Provide fallback functions if not available
    def get_claude_config_path() -> Optional[Path]:
        """Get the Claude config directory based on platform."""
        if sys.platform == "win32":
            path = Path(Path.home(), "AppData", "Roaming", "Claude")
        elif sys.platform == "darwin":
            path = Path(Path.home(), "Library", "Application Support", "Claude")
        elif sys.platform.startswith("linux"):
            path = Path(
                os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"), "Claude"
            )
        else:
            return None

        if path.exists():
            return path
        return None

    def update_claude_config(
        file_spec: str,
        server_name: str,
        *,
        with_editable: Optional[Path] = None,
        with_packages: Optional[List[str]] = None,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Add or update a FastMCP server in Claude's configuration."""
        config_dir = get_claude_config_path()
        if not config_dir:
            print("Claude Desktop config directory not found.")
            return False

        config_file = config_dir / "claude_desktop_config.json"
        if not config_file.exists():
            try:
                config_file.write_text("{}")
            except Exception as e:
                print(f"Failed to create Claude config file: {e}")
                return False

        try:
            config = json.loads(config_file.read_text())
            if "mcpServers" not in config:
                config["mcpServers"] = {}

            # Always preserve existing env vars and merge with new ones
            if (
                server_name in config["mcpServers"]
                and "env" in config["mcpServers"][server_name]
            ):
                existing_env = config["mcpServers"][server_name]["env"]
                if env_vars:
                    # New vars take precedence over existing ones
                    env_vars = {**existing_env, **env_vars}
                else:
                    env_vars = existing_env

            # Build uv run command
            args = ["run"]

            # Collect all packages in a set to deduplicate
            packages = {"mcp[cli]"}
            if with_packages:
                packages.update(pkg for pkg in with_packages if pkg)

            # Add all packages with --with
            for pkg in sorted(packages):
                args.extend(["--with", pkg])

            if with_editable:
                args.extend(["--with-editable", str(with_editable)])

            # Convert file path to absolute before adding to command
            # Split off any :object suffix first
            if ":" in file_spec:
                file_path, server_object = file_spec.rsplit(":", 1)
                file_spec = f"{Path(file_path).resolve()}:{server_object}"
            else:
                file_spec = str(Path(file_spec).resolve())

            # Add fastmcp run command
            args.extend(["mcp", "run", file_spec])

            server_config: Dict[str, Any] = {"command": "uv", "args": args}

            # Add environment variables if specified
            if env_vars:
                server_config["env"] = env_vars

            config["mcpServers"][server_name] = server_config

            config_file.write_text(json.dumps(config, indent=2))
            print(f"Added server '{server_name}' to Claude config")
            return True
        except Exception as e:
            print(f"Failed to update Claude config: {e}")
            return False


def install_in_claude(
    server_name: str = "ERPNext",
    site_name: Optional[str] = None,
    frappe_path: Optional[str] = None,
    env_vars: Optional[Dict[str, str]] = None,
) -> bool:
    """Install the ERPNext MCP server in Claude desktop app.

    Args:
        server_name: Name to display in Claude
        site_name: Frappe site name
        frappe_path: Path to Frappe installation
        env_vars: Additional environment variables

    Returns:
        True if installation succeeded, False otherwise
    """
    # Determine the current file's location
    current_file = Path(__file__).resolve()

    # The CLI script is in the same directory
    cli_script = current_file.parent / "cli.py"

    # Create environment variables
    env_dict = env_vars or {}

    # Add site name and frappe path if provided
    if site_name:
        env_dict["FRAPPE_SITE_NAME"] = site_name

    if frappe_path:
        env_dict["FRAPPE_PATH"] = frappe_path

    # Create the file spec
    file_spec = str(cli_script)

    # Update Claude config
    return update_claude_config(
        file_spec=file_spec,
        server_name=server_name,
        env_vars=env_dict,
        with_packages=["erpnext_mcp_server"],
    )


def uninstall_from_claude(server_name: str = "ERPNext") -> bool:
    """Uninstall the ERPNext MCP server from Claude desktop app.

    Args:
        server_name: Name of the server to remove

    Returns:
        True if uninstallation succeeded, False otherwise
    """
    config_dir = get_claude_config_path()
    if not config_dir:
        print("Claude Desktop config directory not found.")
        return False

    config_file = config_dir / "claude_desktop_config.json"
    if not config_file.exists():
        print("Claude Desktop config file not found.")
        return False

    try:
        config = json.loads(config_file.read_text())
        if "mcpServers" not in config:
            print("No MCP servers configured in Claude.")
            return True

        if server_name not in config["mcpServers"]:
            print(f"Server '{server_name}' not found in Claude config.")
            return True

        # Remove the server
        del config["mcpServers"][server_name]

        # Write the updated config
        config_file.write_text(json.dumps(config, indent=2))
        print(f"Removed server '{server_name}' from Claude config.")
        return True
    except Exception as e:
        print(f"Failed to update Claude config: {e}")
        return False


def main():
    """Main CLI entrypoint for Claude integration."""
    parser = argparse.ArgumentParser(
        description="ERPNext MCP Server Claude Integration"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Install command
    install_parser = subparsers.add_parser("install", help="Install in Claude")
    install_parser.add_argument(
        "--name", default="ERPNext", help="Name to display in Claude"
    )
    install_parser.add_argument("--site", help="Frappe site name")
    install_parser.add_argument("--frappe-path", help="Path to Frappe installation")
    install_parser.add_argument(
        "--env",
        action="append",
        nargs=2,
        metavar=("KEY", "VALUE"),
        help="Additional environment variables",
    )

    # Uninstall command
    uninstall_parser = subparsers.add_parser("uninstall", help="Uninstall from Claude")
    uninstall_parser.add_argument(
        "--name", default="ERPNext", help="Name of the server to remove"
    )

    args = parser.parse_args()

    if args.command == "install":
        # Convert env vars to dictionary
        env_vars = {}
        if args.env:
            for key, value in args.env:
                env_vars[key] = value

        success = install_in_claude(
            server_name=args.name,
            site_name=args.site,
            frappe_path=args.frappe_path,
            env_vars=env_vars,
        )
        sys.exit(0 if success else 1)

    elif args.command == "uninstall":
        success = uninstall_from_claude(server_name=args.name)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

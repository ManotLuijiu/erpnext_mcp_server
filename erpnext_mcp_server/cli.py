#!/usr/bin/env python3
"""
Standalone MCP server for ERPNext

This script allows running the MCP server outside of the Frappe framework,
which is useful for development or for running in environments where bench
is not available.

Usage:
    python -m erpnext_mcp_server.cli [--port PORT] [--transport stdio|sse] [--log-level LEVEL]
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("mcp_server")


def is_frappe_available():
    """Check if Frappe is available"""
    try:
        import frappe

        return True
    except ImportError:
        return False


def run_server_standalone():
    """Run the MCP server in standalone mode"""
    parser = argparse.ArgumentParser(description="ERPNext MCP Server")
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port to listen on (for HTTP/SSE transport)",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="sse",
        help="Transport protocol to use",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Logging level",
    )
    parser.add_argument(
        "--dev", action="store_true", help="Run in development mode (localhost only)"
    )
    parser.add_argument(
        "--site",
        help="Frappe site to use (if not specified, uses FRAPPE_SITE_NAME environment variable)",
    )
    parser.add_argument(
        "--frappe-path",
        help="Path to Frappe installation (if not specified, uses current directory or FRAPPE_PATH environment variable)",
    )

    args = parser.parse_args()

    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    frappe_available = is_frappe_available()

    if not frappe_available:
        # Try to initialize Frappe
        frappe_path = args.frappe_path or os.environ.get("FRAPPE_PATH")
        site_name = args.site or os.environ.get("FRAPPE_SITE_NAME")

        if not frappe_path or not site_name:
            logger.error(
                "Frappe not found and neither --frappe-path/FRAPPE_PATH "
                "nor --site/FRAPPE_SITE_NAME are specified"
            )
            sys.exit(1)

        # Add Frappe to path
        frappe_path = Path(frappe_path).resolve()
        sys.path.insert(0, str(frappe_path))

        # Initialize Frappe
        import frappe

        frappe.init(site=site_name, sites_path=str(frappe_path / "sites"))

        # Connect to the database
        frappe.connect()

    # Now we can import our server
    try:
        from erpnext_mcp_server.mcp_erpnext.mcp_server import get_server

        # Get the server
        server = get_server()

        # Configure settings
        settings = {
            "log_level": args.log_level,
            "port": args.port,
        }

        # Development mode binds only to localhost
        if args.dev:
            settings["host"] = "127.0.0.1"
            settings["debug"] = True

        # Override settings
        for key, value in settings.items():
            setattr(server.settings, key, value)

        # Run the server
        server.run(transport=args.transport)

    except Exception as e:
        logger.exception(f"Error running MCP server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_server_standalone()

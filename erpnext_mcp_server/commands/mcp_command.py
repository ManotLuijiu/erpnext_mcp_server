"""
Frappe command for running the MCP server

Usage:
    bench mcp [--port PORT] [--transport stdio|sse] [--log-level LEVEL]
"""

import os

import click
import frappe
from frappe.commands.utils import pass_context


@click.command("mcp")
@click.option("--port", default=8080, help="Port to listen on (for HTTP/SSE transport)")
@click.option(
    "--transport",
    default="sse",
    type=click.Choice(["stdio", "sse"]),
    help="Transport protocol to use",
)
@click.option(
    "--log-level",
    default="INFO",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    help="Logging level",
)
@click.option("--dev", is_flag=True, help="Run in development mode (localhost only)")
@pass_context
def mcp_command(context, port, transport, log_level, dev):
    """Run the MCP server for ERPNext"""
    # We import here to ensure Frappe is fully initialized
    from erpnext_mcp_server.mcp_erpnext.mcp_server import get_server

    # Set up settings
    settings = {
        "log_level": log_level,
        "port": port,
    }

    # Development mode binds only to localhost
    if dev:
        settings["host"] = "127.0.0.1"
        settings["debug"] = True

    # Get the server
    server = get_server()

    # Override settings
    for key, value in settings.items():
        setattr(server.settings, key, value)

    # Run the server
    server.run(transport=transport)


commands = [mcp_command]

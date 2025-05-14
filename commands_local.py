import os
import subprocess

import click
import frappe


@click.command()
@click.option("--site", default=None, help="Site name")
@click.option("--port", default=8100, help="Port to run on")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
def start_local_mcp(site=None, port=8100, reload=False):
    """Start local MCP server"""
    site = site or frappe.local.site

    print(f"Starting local MCP server for {site} on port {port}")

    cmd = [
        "python",
        "-m",
        "erpnext_mcp_server.mcp.local_server",
        "run-local-server",
        "--site",
        site,
        "--port",
        str(port),
    ]

    if reload:
        cmd.append("--reload")

    # Run in foreground for local testing
    subprocess.run(cmd)


@click.command()
def test_mcp():
    """Run MCP client tests"""
    print("Running MCP tests...")
    subprocess.run(["python", "-m", "erpnext_mcp_server.test_client"])

# erpnext_mcp_server/commands.py
import click
import subprocess
import os
import sys
import json
from pathlib import Path


@click.command()
@click.option("--site", help="Site name")
@click.option("--port", default=8100, help="Port to run on")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
def start_local(site=None, port=8100, reload=False):
    """Start local MCP server"""
    import frappe

    site = site or getattr(frappe.local, "site", None)

    if not site:
        click.echo("Please specify site with --site option")
        return

    click.echo(f"Starting local MCP server for {site} on port {port}")

    cmd = [
        sys.executable,
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

    # Run in foreground
    subprocess.run(cmd)


@click.command()
def test():
    """Run MCP tests"""
    click.echo("Running MCP tests...")
    subprocess.run([sys.executable, "-m", "erpnext_mcp_server.test_client"])


@click.command()
@click.option("--site", help="Site name")
def status(site=None):
    """Check MCP server status"""
    import frappe

    site = site or getattr(frappe.local, "site", None)

    if not site:
        click.echo("Please specify site with --site option")
        return

    # Check if process is running
    import psutil

    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if "local_server" in " ".join(
                proc.info["cmdline"] or []
            ) and site in " ".join(proc.info["cmdline"] or []):
                click.echo(f"MCP server running for {site} (PID: {proc.info['pid']})")
                return
        except:
            pass

    click.echo(f"No MCP server found for {site}")


# Main CLI group
@click.group()
def mcp():
    """MCP Server commands"""
    pass


# Add commands to group
mcp.add_command(start_local, "start")
mcp.add_command(test, "test")
mcp.add_command(status, "status")

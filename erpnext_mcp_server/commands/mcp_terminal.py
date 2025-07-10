"""
ERPNext MCP Terminal Command for Bench Integration
"""

import click
import subprocess
import sys
from pathlib import Path


@click.command()
@click.option("--site", help="Site name (defaults to current site)")
@click.option("--port", default=8100, help="MCP server port")
@click.option("--host", default="localhost", help="MCP server host")
@click.option("--quick", help="Run a single query and exit")
@click.pass_context
def mcp_terminal(ctx, site, port, host, quick):
    """Launch enhanced MCP terminal client for fast ERPNext reporting"""
    import frappe
    
    # Get current site if not specified
    if not site:
        site = getattr(frappe.local, 'site', None)
        if not site:
            click.echo("Error: No site specified and no current site found")
            click.echo("Use: bench --site [sitename] mcp-terminal")
            return
    
    # Get the enhanced client path
    app_path = Path(__file__).parent.parent.parent
    client_script = app_path / "enhanced_cli_client.py"
    
    if not client_script.exists():
        click.echo(f"Error: Enhanced CLI client not found at {client_script}")
        click.echo("Please run setup_cli.sh first")
        return
    
    # Build command arguments
    cmd = [
        sys.executable,
        str(client_script),
        "--site", site,
        "--port", str(port),
        "--host", host
    ]
    
    if quick:
        cmd.extend(["--quick", quick])
    
    # Run the enhanced client
    try:
        click.echo(f"🚀 Launching MCP Terminal for site: {site}")
        subprocess.run(cmd)
    except KeyboardInterrupt:
        click.echo("\n👋 Terminal session ended")
    except Exception as e:
        click.echo(f"Error running MCP terminal: {e}")


commands = [mcp_terminal]
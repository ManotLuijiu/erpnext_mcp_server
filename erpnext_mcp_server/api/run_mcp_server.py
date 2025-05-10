#!/usr/bin/env python3

"""
Wrapper script to run the MCP server with proper Frappe context
"""

import os
import sys
import json
import frappe
from frappe.utils import get_site_path


def run_mcp_server():
    """Run the MCP server with proper Frappe context"""
    try:
        # Get the current site
        site_name = (
            frappe.local.site
            if hasattr(frappe.local, "site")
            else os.environ.get("FRAPPE_SITE")
        )

        if not site_name:
            raise ValueError("No site specified. Set FRAPPE_SITE environment variable.")

        # Get site settings
        settings = frappe.get_single("MCP Server Settings")
        transport = settings.transport or "stdio"
        port = settings.server_port or 3000

        # Set up environment
        site_path = get_site_path()
        apps_path = os.path.join(frappe.get_app_path("erpnext_mcp_server"))

        # Path to the standalone server
        server_script = os.path.join(apps_path, "mcp", "standalone_server.py")

        # Python path with all necessary modules
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{site_path}:{apps_path}:{env.get('PYTHONPATH', '')}"
        env["FRAPPE_SITE"] = site_name
        env["FRAPPE_SITE_PATH"] = site_path

        # Command to run the server
        if transport == "stdio":
            cmd = [
                sys.executable,
                server_script,
                "--site",
                site_name,
                "--transport",
                "stdio",
            ]
        else:
            cmd = [
                sys.executable,
                server_script,
                "--site",
                site_name,
                "--transport",
                transport,
                "--port",
                str(port),
            ]

        # Import subprocess here to avoid issues
        import subprocess

        # Run the server
        process = subprocess.Popen(
            cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        # Return the process for monitoring
        return process

    except Exception as e:
        frappe.logger().error(f"Error starting MCP server: {str(e)}")
        raise


def get_server_info():
    """Get information about the MCP server"""
    settings = frappe.get_single("MCP Server Settings")

    # Check available tools and resources
    tools = []
    resources = []

    # TODO: Dynamically discover available tools and resources

    return {
        "enabled": settings.enabled,
        "transport": settings.transport,
        "port": settings.server_port,
        "process_id": settings.process_id,
        "last_start_time": settings.last_start_time,
        "last_stop_time": settings.last_stop_time,
        "last_error": settings.last_error,
        "tools": tools,
        "resources": resources,
    }


# Frappe method to be called from API
@frappe.whitelist()
def start_server():
    """Start the MCP server"""
    try:
        process = run_mcp_server()

        # Update settings
        settings = frappe.get_single("MCP Server Settings")
        settings.process_id = process.pid
        settings.last_start_time = frappe.utils.now()
        settings.last_error = None
        settings.save()

        return {
            "status": "success",
            "process_id": process.pid,
            "message": "MCP server started successfully",
        }

    except Exception as e:
        # Save error to settings
        settings = frappe.get_single("MCP Server Settings")
        settings.last_error = str(e)
        settings.save()

        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def get_server_logs(lines: int = 100):
    """Get the last N lines of server logs"""
    try:
        log_file = os.path.join(frappe.utils.get_site_path(), "logs", "mcp_server.log")

        if not os.path.exists(log_file):
            return "No log file found"

        with open(log_file, "r") as f:
            all_lines = f.readlines()
            last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            return "".join(last_lines)

    except Exception as e:
        return f"Error reading logs: {str(e)}"

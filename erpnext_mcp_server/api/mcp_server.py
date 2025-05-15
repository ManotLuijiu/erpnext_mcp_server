import os
import sys

import frappe
from frappe import _
from frappe.utils import get_site_path


@frappe.whitelist()
def get_mcp_server_status():
    """Get the current status of the MCP server"""
    try:
        settings = frappe.get_single("MCP Server Settings")
        status = settings.get_server_status()  # type: ignore
        return status
    except Exception as e:
        frappe.log_error(f"Error getting MCP server status: {str(e)}")
        return {"status": "Error", "is_running": False, "last_error": str(e)}


@frappe.whitelist()
def start_mcp_server():
    """Start the MCP server"""
    try:
        settings = frappe.get_single("MCP Server Settings")

        # Check if server is already running
        if settings.is_server_running():  # type: ignore
            return {
                "status": "info",
                "message": "MCP Server is already running",
                "is_running": True,
            }

        # Start the server
        settings.start_server()  # type: ignore

        return {
            "status": "success",
            "message": "MCP Server started successfully",
            "is_running": True,
        }

    except Exception as e:
        frappe.log_error(f"Error starting MCP server: {str(e)}")
        return {"status": "error", "message": str(e), "is_running": False}


@frappe.whitelist()
def stop_mcp_server():
    """Stop the MCP server"""
    try:
        settings = frappe.get_single("MCP Server Settings")

        # Check if server is running
        if not settings.is_server_running():  # type: ignore
            return {
                "status": "info",
                "message": "MCP Server is not running",
                "is_running": False,
            }

        # Stop the server
        settings.stop_server()  # type: ignore

        return {
            "status": "success",
            "message": "MCP Server stopped successfully",
            "is_running": False,
        }

    except Exception as e:
        frappe.log_error(f"Error stopping MCP server: {str(e)}")
        return {"status": "error", "message": str(e), "is_running": False}


@frappe.whitelist()
def restart_mcp_server():
    """Restart the MCP server"""
    try:
        settings = frappe.get_single("MCP Server Settings")
        settings.restart_server()  # type: ignore

        return {
            "status": "success",
            "message": "MCP Server restarted successfully",
            "is_running": True,
        }

    except Exception as e:
        frappe.log_error(f"Error restarting MCP server: {str(e)}")
        return {"status": "error", "message": str(e), "is_running": False}


@frappe.whitelist()
def get_mcp_server_logs():
    """Get MCP server logs"""
    try:
        settings = frappe.get_single("MCP Server Settings")
        logs = settings.get_server_logs()  # type: ignore

        # If no logs, provide some diagnostic information
        if (
            not logs
            or logs == "No logs available. The server might not have started yet."
        ):
            diagnostic_info = []
            diagnostic_info.append("=== MCP Server Diagnostic Information ===")
            diagnostic_info.append(f"Server Path: {settings.server_path}")  # type: ignore
            diagnostic_info.append(f"Transport: {settings.transport}")  # type: ignore
            diagnostic_info.append(f"Status: {settings.status}")  # type: ignore
            diagnostic_info.append(f"Process ID: {settings.process_id}")  # type: ignore
            diagnostic_info.append(f"Last Start: {settings.last_start_time}")  # type: ignore
            diagnostic_info.append(f"Last Stop: {settings.last_stop_time}")  # type: ignore
            diagnostic_info.append(f"Site: {frappe.local.site}")
            diagnostic_info.append(f"Python Executable: {sys.executable}")
            diagnostic_info.append(f"Sites Path: {get_site_path()}")

            if settings.last_error:  # type: ignore
                diagnostic_info.append(f"\nLast Error: {settings.last_error}")  # type: ignore

            logs = "\n".join(diagnostic_info)

        return logs

    except Exception as e:
        frappe.log_error(f"Error getting MCP server logs: {str(e)}")
        return f"Error retrieving logs: {str(e)}"


@frappe.whitelist()
def get_mcp_server_config():
    """Get MCP server configuration"""
    try:
        settings = frappe.get_single("MCP Server Settings")

        config = {
            "server_path": settings.server_path,  # type: ignore
            "transport": settings.transport,  # type: ignore
            "log_level": settings.log_level,  # type: ignore
            "auto_start": settings.auto_start,  # type: ignore
            "status": settings.status,  # type: ignore
            "is_running": settings.is_server_running(),  # type: ignore
            "process_id": settings.process_id,  # type: ignore
            "last_start_time": settings.last_start_time,  # type: ignore
            "last_stop_time": settings.last_stop_time,  # type: ignore
            "last_error": settings.last_error,  # type: ignore
        }

        return config

    except Exception as e:
        frappe.log_error(f"Error getting MCP server config: {str(e)}")
        return {"error": str(e)}


@frappe.whitelist()
def update_mcp_server_config(config):
    """Update MCP server configuration"""
    try:
        settings = frappe.get_single("MCP Server Settings")

        # Update allowed fields
        if "server_path" in config:
            settings.server_path = config["server_path"]  # type: ignore
        if "transport" in config:
            settings.transport = config["transport"]  # type: ignore
        if "log_level" in config:
            settings.log_level = config["log_level"]  # type: ignore
        if "auto_start" in config:
            settings.auto_start = config["auto_start"]  # type: ignore

        settings.save()

        return {"status": "success", "message": "Configuration updated successfully"}

    except Exception as e:
        frappe.log_error(f"Error updating MCP server config: {str(e)}")
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def test_mcp_server_connection():
    """Test connection to MCP server"""
    try:
        settings = frappe.get_single("MCP Server Settings")

        if not settings.is_server_running():  # type: ignore
            return {"status": "error", "message": "MCP Server is not running"}

        # TODO: Add actual connection test once we have a way to communicate with the server
        # For now, just check if the process is running

        return {
            "status": "success",
            "message": "MCP Server is running",
            "process_id": settings.process_id,  # type: ignore
        }

    except Exception as e:
        frappe.log_error(f"Error testing MCP server connection: {str(e)}")
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def get_environment_info():
    """Get environment information for troubleshooting"""
    try:
        import platform

        info = {
            "python_version": sys.version,
            "python_executable": sys.executable,
            "frappe_site": frappe.local.site,
            "sites_path": frappe.get_site_path(),
            "platform": platform.platform(),
            "python_path": sys.path[:5],  # First 5 entries
            "environment_variables": {
                "FRAPPE_SITE": os.environ.get("FRAPPE_SITE"),
                "SITES_PATH": os.environ.get("SITES_PATH"),
                "PYTHONPATH": os.environ.get("PYTHONPATH"),
            },
        }

        # Check if MCP modules are importable
        try:
            import mcp

            info["mcp_available"] = True
            info["mcp_version"] = getattr(mcp, "__version__", "unknown")
        except ImportError as e:
            info["mcp_available"] = False
            info["mcp_error"] = str(e)

        # Check if server file exists
        settings = frappe.get_single("MCP Server Settings")
        if settings.server_path and os.path.exists(settings.server_path):  # type: ignore
            info["server_file_exists"] = True
            info["server_file_path"] = settings.server_path  # type: ignore
        else:
            info["server_file_exists"] = False
            info["server_file_path"] = settings.server_path  # type: ignore

        return info

    except Exception as e:
        frappe.log_error(f"Error getting environment info: {str(e)}")
        return {"error": str(e)}

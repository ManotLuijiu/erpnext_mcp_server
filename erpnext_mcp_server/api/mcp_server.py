import frappe
import json
import psutil
import os
import subprocess
import time
from typing import Dict, List, Any
from datetime import datetime
from frappe.utils import get_site_path, now_datetime, format_datetime


@frappe.whitelist()
def get_mcp_server_status() -> Dict[str, Any]:
    """Get the current status of the MCP server"""
    try:
        # Get MCP Server settings
        settings = frappe.get_single("MCP Server Settings")

        # Check if the server process is running
        is_running = False
        process_id = None
        uptime = None

        if settings.process_id:
            try:
                # Check if the process exists
                process = psutil.Process(settings.process_id)
                if process.is_running():
                    is_running = True
                    process_id = settings.process_id

                    # Calculate uptime
                    if settings.last_start_time:
                        start_time = frappe.utils.get_datetime(settings.last_start_time)
                        uptime = str(frappe.utils.now_datetime() - start_time).split(
                            "."
                        )[0]
            except psutil.NoSuchProcess:
                # Process doesn't exist, clear the PID
                settings.process_id = None
                settings.save(ignore_permissions=True)

        # Determine server status
        status = "Running" if is_running else "Stopped"
        if settings.last_error and not is_running:
            status = "Error"

        return {
            "status": status,
            "is_running": is_running,
            "process_id": process_id,
            "last_start_time": settings.last_start_time,
            "last_stop_time": settings.last_stop_time,
            "last_error": settings.last_error,
            "enabled": settings.enabled,
            "transport": settings.transport or "stdio",
            "port": settings.server_port,
            "uptime": uptime,
            "active_connections": 0,  # Placeholder
            "available_tools": 5,  # Placeholder
            "available_resources": 3,  # Placeholder
        }

    except Exception as e:
        frappe.logger().error(f"Error getting MCP server status: {str(e)}")
        return {"status": "Error", "is_running": False, "last_error": str(e)}


@frappe.whitelist()
def start_mcp_server() -> Dict[str, Any]:
    """
    Start the MCP server.
    """
    if not frappe.has_permission("MCP Server Settings", "write"):
        frappe.throw("You do not have permission to start the MCP server")

    # Get settings document
    settings = get_settings_doc(settings_name)

    if settings.status == "Running":  # type: ignore
        return {"status": "error", "message": "MCP Server is already running."}

    # Update start time
    settings.db_set("last_start_time", now_datetime())
    settings.db_set("enabled", 1)
    settings.db_set("status", "Starting")

    # Start the server
    settings.start_server()  # type: ignore

    return {"status": "success", "message": "MCP Server is started."}


@frappe.whitelist()
def stop_mcp_server(settings_name=None):
    """
    Stop the MCP server.
    """
    if not frappe.has_permission("MCP Server Settings", "write"):
        frappe.throw("You do not have permission to stop the MCP server")

    # Get settings document
    settings = get_settings_doc(settings_name)

    if settings.status != "Running":  # type: ignore
        return {"status": "error", "message": "MCP Server is not running."}

    # Update stop time
    settings.db_set("last_stop_time", now_datetime())
    settings.db_set("enabled", 0)
    settings.db_set("status", "Stopped")

    # Stop the server
    settings.stop_server()  # type: ignore

    return {"status": "success", "message": "MCP Server is stopped."}


@frappe.whitelist()
def get_mcp_server_status(settings_name=None):
    """
    Get the status of the MCP server.
    """
    if not frappe.has_permission("MCP Server Settings", "read"):
        frappe.throw("You do not have permission to view the MCP server status")

    # Get settings document
    settings = get_settings_doc(settings_name)

    # Check if the server is running
    is_running = settings.is_server_running()  # type: ignore

    # Ensure status is accurate
    if is_running and settings.status != "Running":  # type: ignore
        settings.db_set("status", "Running")
    elif not is_running and settings.status == "Running":  # type: ignore
        settings.db_set("status", "Stopped")

    return {
        "status": settings.status,  # type: ignore
        "is_running": is_running,
        "process_id": settings.process_id,  # type: ignore
        "last_start_time": settings.last_start_time,  # type: ignore
        "last_stop_time": settings.last_stop_time,  # type: ignore
        "enabled": settings.enabled,  # type: ignore
        "transport": settings.transport,  # type: ignore
        "last_error": settings.last_error,  # type: ignore
    }


def get_settings_doc(settings_name=None):
    """
    Get the MCP Server Settings document.
    """
    if settings_name:
        # Use the provided settings name
        settings = frappe.get_doc("MCP Server Settings", settings_name)
    else:
        # Get the first enabled settings or create one if none exists
        settings_list = frappe.get_all("MCP Server Settings", filters={"enabled": 1})

        if settings_list:
            settings = frappe.get_doc("MCP Server Settings", settings_list[0].name)
        else:
            # Check if any settings exist
            all_settings = frappe.get_all("MCP Server Settings", limit=1)

            if all_settings:
                settings = frappe.get_doc("MCP Server Settings", all_settings[0].name)
            else:
                # Create new settings
                settings = frappe.new_doc("MCP Server Settings")
                settings.enabled = 0  # type: ignore
                settings.status = "Stopped"  # type: ignore
                settings.transport = "stdio"  # type: ignore
                settings.port = 8000  # type: ignore
                settings.log_level = "INFO"  # type: ignore
                settings.server_name = "ERPNext MCP Server"  # type: ignore
                settings.insert()

    return settings


def auto_start_server():
    """Auto-start MCP server if configured to do so"""
    try:
        # Get settings with auto_start enabled
        settings_list = frappe.get_all(
            "MCP Server Settings", filters={"auto_start": 1, "enabled": 1}, limit=1
        )

        if settings_list:
            settings = frappe.get_doc("MCP Server Settings", settings_list[0].name)
            settings.start_server()  # type: ignore
            frappe.db.commit()
            frappe.log_error(
                f"Auto-started MCP Server (PID: {settings.process_id})",  # type: ignore
                "MCP Server",
            )

    except Exception as e:
        frappe.log_error(f"Error auto-starting MCP server: {e}", "MCP Server")


# Add auto-start to hooks
# This will be called after the site is ready
def after_site_login():
    auto_start_server()

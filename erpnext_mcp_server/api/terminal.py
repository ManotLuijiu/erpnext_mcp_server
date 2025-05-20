import json
import os

import frappe
from frappe.utils import cint

from erpnext_mcp_server.utils.mcp_server import check_mcp_server


@frappe.whitelist()
def send_terminal_output(user, output_data):
    frappe.publish_realtime(
        "mcp:output", data=output_data, user=user  # This will send to specific user
    )


# For broadcasting to all users
@frappe.whitelist()
def broadcast_terminal_output(output_data):
    frappe.publish_realtime("mcp:output", data=output_data)


@frappe.whitelist()
def get_terminal_settings():
    """Get terminal settings for the current user"""
    settings = {
        "mcp_server_available": check_mcp_server(),
        "socketio_port": cint(frappe.conf.get("socketio_port", 9000)),
        "user": frappe.session.user,
        "theme": frappe.db.get_value("User", frappe.session.user, "theme") or "light",
        "can_use_terminal": frappe.has_permission("MCP Terminal", "read"),
    }

    return settings


@frappe.whitelist()
def start_mcp_server():
    """Start the MCP server"""
    # Verify permissions
    if not frappe.has_permission("MCP Terminal", "write"):
        frappe.throw("You do not have permission to start the MCP server")

    from erpnext_mcp_server.utils.mcp_server import start_mcp_server

    result = start_mcp_server()

    return {"success": result}


@frappe.whitelist()
def stop_mcp_server():
    """Stop the MCP server"""
    # Verify permissions
    if not frappe.has_permission("MCP Terminal", "write"):
        frappe.throw("You do not have permission to stop the MCP server")

    from erpnext_mcp_server.utils.mcp_server import stop_mcp_server

    result = stop_mcp_server()

    return {"success": result}


@frappe.whitelist()
def check_mcp_server_status():
    """Check if MCP server is running"""
    status = check_mcp_server()
    return {"running": status}

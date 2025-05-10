import frappe
from frappe import _
from erpnext_mcp_server.mcp.server import erp_server


@frappe.whitelist()
def call_tool(tool_name, arguments):
    """Call a tool on the MCP server"""
    # Implement permission checks and logging
    # Then delegate to the MCP server
    return erp_server.call_tool(tool_name, arguments)


@frappe.whitelist()
def get_resource(resource_uri):
    """Get a resource from the MCP server"""
    # Implement permission checks and logging
    # Then delegate to the MCP server
    return erp_server.get_resource(resource_uri)

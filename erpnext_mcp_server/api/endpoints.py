import frappe
from frappe import _
from erpnext_mcp_server.mcp_server_fetch.server import erp_server


@frappe.whitelist()
def call_tool(tool_name, arguments):
    """Call a tool on the MCP server"""
    # Implement permission checks and logging
    # Then delegate to the MCP server
    return erp_server.call_tool(tool_name, arguments)


@frappe.whitelist()
async def read_resources(resource_uri):
    """Get a resource from the MCP server"""
    # Implement permission checks and logging
    # Then delegate to the MCP server
    resources = await erp_server.read_resource(resource_uri)
    return resources


@frappe.whitelist()
def get_resources():
    """Get a resource from the MCP server"""
    # Implement permission checks and logging
    # Then delegate to the MCP server
    return erp_server.list_resources()

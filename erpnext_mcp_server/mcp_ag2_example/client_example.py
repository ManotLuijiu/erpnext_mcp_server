import json

import frappe
import requests


def test_mcp_api():
    """Test the MCP API endpoints."""
    # List resources
    resources = frappe.call("erpnext_mcp_server.api.list_resources")
    print(f"Resources: {json.dumps(resources, indent=2)}")

    # Read a resource
    erp_resource = frappe.call(
        "erpnext_mcp_server.mcp_ag2_example.server.api.read_resource",
        uri="erp://doctype/User",
    )
    print(f"ERP Resource: {json.dumps(erp_resource, indent=2)}")

    # List tools
    tools = frappe.call("erpnext_mcp_server.mcp_ag2_example.server.api.list_tools")
    print(f"Tools: {json.dumps(tools, indent=2)}")

    # Call a tool
    result = frappe.call(
        "erpnext_mcp_server.mcp_ag2_example.server.api.call_tool",
        name="write_file",
        arguments={"path": "test.txt", "content": "Hello from MCP client!"},
    )
    print(f"Tool result: {json.dumps(result, indent=2)}")


if __name__ == "__main__":
    test_mcp_api()

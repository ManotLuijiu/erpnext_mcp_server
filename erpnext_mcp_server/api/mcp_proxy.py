import frappe
from frappe import _
import requests
import json
import os
import subprocess
import time


@frappe.whitelist()
def query(query, context=None):
    """
    Proxy API to forward queries to the MCP Server

    Args:
        query: The query text to send to the MCP server
        context: Optional context data

    Returns:
        MCP server response
    """
    if not frappe.has_permission("MCP Server Settings", "read"):
        frappe.throw(_("You do not have permission to uer MCP"))

    # Get the MCP Server settings
    try:
        settings = get_mcp_settings()

        print(f"settings mcp_proxy.py {settings}")

        if not settings.is_server_running():  # type: ignore
            return {
                "error": _("MCP server is not running. Please start the server first.")
            }

        # Determine how to communicate with the MCP Server
        if settings.transport == "sse":  # type: ignore
            # For SSE Transport, use HTTP call
            return call_mcp_via_http(query, context, settings.port)  # type: ignore
        else:
            # For stdio transport, use subprocess communication
            return call_mcp_via_subprocess(query, context)
    except Exception as e:
        frappe.log_error(f"Error querying MCP: {str(e)}", "MCP Proxy")
        return {"error": str(e)}


def get_mcp_settings():
    """Get the MCP server settings"""
    settings_list = frappe.get_all(
        "MCP Server Settings", filters={"enabled": 1}, limit=1
    )

    if not settings_list:
        frappe.throw(_("MCP server is not configured or enabled"))

    settings = frappe.get_doc("MCP Server Settings", settings_list[0].name)
    return settings


def call_mcp_via_http(query, context, port=8000):
    """Call MCP server via HTTP for SSE transport"""
    try:
        # Prepare the request data
        data = {"query": query, "context": context or {}}

        # Send the request to the MCP server
        response = requests.post(
            f"http://localhost:{port}/api/mcp/query",
            json=data,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=30,  # 30 seconds timeout
        )

        if response.status_code != 200:
            return {
                "error": _(
                    f"MCP server returned error: {response.status_code} - {response.text}"
                )
            }

        return response.json()

    except requests.RequestException as e:
        frappe.log_error(f"HTTP error querying MCP: {str(e)}", "MCP Proxy")
        return {"error": str(e)}


def call_mcp_via_subprocess(query, context):
    """Call MCP server via subprocess for stdio transport"""
    try:
        # Get the path to the Python script
        script_path = os.path.join(
            frappe.get_app_path("erpnext_mcp_server"), "mcp", "query_client.py"
        )

        # Create a temporary file for the input data
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json") as f:
            temp_file = f.name
            json.dump({"query": query, "context": context or {}}, f)

        try:
            # Execute the query client script
            env = os.environ.copy()
            env["FRAPPE_SITE"] = frappe.local.site

            result = subprocess.run(
                [env.get("PYTHONBIN", "python3"), script_path, temp_file],
                env=env,
                capture_output=True,
                text=True,
                timeout=30,  # 30 seconds timeout
            )

            if result.returncode != 0:
                frappe.log_error(f"MCP query failed: {result.stderr}", "MCP Proxy")
                return {"error": _("MCP query failed"), "details": result.stderr}

            # Parse the JSON result
            return json.loads(result.stdout)

        finally:
            # Clean up the temporary file
            try:
                os.unlink(temp_file)
            except Exception:
                pass

    except Exception as e:
        frappe.log_error(f"Error in subprocess call to MCP: {str(e)}", "MCP Proxy")
        return {"error": str(e)}

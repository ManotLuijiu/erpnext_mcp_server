import asyncio
import json
import logging
from typing import Dict, List, Optional

import frappe
from frappe import _
from frappe.utils import cstr
from server import get_mcp_server

logger = logging.getLogger(__name__)


@frappe.whitelist(allow_guest=False)
def list_resources():
    """List available MCP resources."""
    try:
        server = get_mcp_server()

        # Create a future to hold the result
        loop = server.loop
        future = asyncio.run_coroutine_threadsafe(
            server.mcp_server.list_resources(), loop  # type: ignore
        )

        # Wait for the result with timeout
        result = future.result(timeout=10)

        # Convert to JSON-serializable format
        resources = []
        for resource in result:
            resources.append(
                {
                    "uri": str(resource.uri),
                    "name": resource.name,
                    "description": resource.description,
                    "mimeType": resource.mimeType,
                }
            )

        return {"status": "success", "resources": resources}

    except Exception as e:
        logger.exception("Error listing resources")
        return {"status": "error", "message": str(e)}


@frappe.whitelist(allow_guest=False)
def read_resource(uri):
    """Read a resource by URI."""
    try:
        server = get_mcp_server()

        # Create a future to hold the result
        loop = server.loop
        if not server.mcp_server or not loop:
            raise ValueError(
                "MCP server is not initialized or unavailable, or event loop is not set"
            )

        future = asyncio.run_coroutine_threadsafe(
            server.mcp_server.read_resource(uri), loop
        )

        # Wait for the result with timeout
        result = future.result(timeout=10)

        return {"status": "success", "content": result}

    except Exception as e:
        logger.exception(f"Error reading resource: {uri}")
        return {"status": "error", "message": str(e)}


@frappe.whitelist(allow_guest=False)
def list_tools():
    """List available MCP tools."""
    try:
        server = get_mcp_server()

        # Create a future to hold the result
        loop = server.loop
        if not loop:
            raise ValueError("Event loop is not set or unavailable")

        if not server.mcp_server:
            raise ValueError("MCP server is not initialized or unavailable")

        future = asyncio.run_coroutine_threadsafe(server.mcp_server.list_tools(), loop)

        # Wait for the result with timeout
        result = future.result(timeout=10)

        # Convert to JSON-serializable format
        tools = []
        for tool in result:
            tools.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema,
                }
            )

        return {"status": "success", "tools": tools}

    except Exception as e:
        logger.exception("Error listing tools")
        return {"status": "error", "message": str(e)}


@frappe.whitelist(allow_guest=False)
def call_tool(name, arguments=None):
    """Call an MCP tool."""
    try:
        if arguments and isinstance(arguments, str):
            arguments = json.loads(arguments)

        server = get_mcp_server()

        # Create a future to hold the result
        loop = server.loop
        if not server.mcp_server:
            raise ValueError("MCP server is not initialized or unavailable")

        if not loop:
            raise ValueError("Event loop is not set or unavailable")

        future = asyncio.run_coroutine_threadsafe(
            server.mcp_server.call_tool(name, arguments), loop
        )

        # Wait for the result with timeout
        result = future.result(timeout=30)

        # Extract text content from result
        content = []
        for item in result:
            if hasattr(item, "text"):
                content.append(item.text)
            else:
                content.append(str(item))

        return {"status": "success", "content": content}

    except Exception as e:
        logger.exception(f"Error calling tool: {name}")
        return {"status": "error", "message": str(e)}

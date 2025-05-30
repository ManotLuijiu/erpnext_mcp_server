"""
ERPNext MCP Server - Main Implementation
Provides Model Context Protocol server for ERPNext automation
"""

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Dict, List

import frappe
import mcp.server.stdio
import mcp.types as types
from frappe.utils import get_site_name
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from .tools.database_tools import DatabaseTools
from .tools.document_tools import DocumentTools
from .tools.file_tools import FileTools
from .tools.system_tools import SystemTools


@asynccontextmanager
async def server_lifespan(server: Server) -> AsyncIterator[Dict[str, Any]]:
    """Manage server startup and shutdown lifecycle."""
    # Initialize resources on startup
    site_name = get_site_name(
        frappe.local.request.host if frappe.local.request else None
    )

    # Initialize Frappe context
    if not frappe.db:
        frappe.init(site=site_name)
        frappe.connect()

    # Initialize Frappe context
    if not frappe.db:
        frappe.init(site=site_name)
        frappe.connect()

    # Initialize tool classes
    document_tools = DocumentTools()
    database_tools = DatabaseTools()
    system_tools = SystemTools()
    file_tools = FileTools()

    context = {
        "db": frappe.db,
        "site_name": site_name,
        "document_tools": document_tools,
        "database_tools": database_tools,
        "system_tools": system_tools,
        "file_tools": file_tools,
    }

    try:
        yield context
    finally:
        # Clean up on shutdown
        if frappe.db:
            frappe.db.close()


# Create server instance
server = Server("erpnext-mcp-server", lifespan=server_lifespan)


@server.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """List all available tools."""
    return [
        # Document operations
        types.Tool(
            name="list_doctypes",
            description="List all available document types in ERPNext with module information",
            inputSchema={
                "type": "object",
                "properties": {
                    "module": {
                        "type": "string",
                        "description": "Filter by specific module (optional)",
                    }
                },
            },
        ),
        types.Tool(
            name="get_document",
            description="Retrieve a specific document with full details and formatting",
            inputSchema={
                "type": "object",
                "properties": {
                    "doctype": {
                        "type": "string",
                        "description": "The document type (e.g., 'Customer', 'Sales Invoice')",
                    },
                    "name": {"type": "string", "description": "The document name/ID"},
                    "fields": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific fields to retrieve (optional, gets all if not specified)",
                    },
                },
                "required": ["doctype", "name"],
            },
        ),
        types.Tool(
            name="search_documents",
            description="Search documents with advanced filtering and pagination",
            inputSchema={
                "type": "object",
                "properties": {
                    "doctype": {
                        "type": "string",
                        "description": "The document type to search",
                    },
                    "query": {"type": "string", "description": "Search query text"},
                    "filters": {
                        "type": "object",
                        "description": "Additional filters as key-value pairs",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 20,
                        "description": "Maximum number of results to return",
                    },
                    "fields": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Fields to include in results",
                    },
                },
                "required": ["doctype"],
            },
        ),
        # Database operations
        types.Tool(
            name="execute_sql",
            description="Execute SQL queries (SELECT only for security)",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SQL SELECT query to execute",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 100,
                        "description": "Maximum number of rows to return",
                    },
                },
                "required": ["query"],
            },
        ),
        # System operations
        types.Tool(
            name="get_system_info",
            description="Get comprehensive system information including versions, database details, and platform info",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="bench_command",
            description="Execute safe bench commands for system management",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Bench command to execute (e.g., 'version', 'status', 'list-apps')",
                    },
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Additional command arguments",
                    },
                },
                "required": ["command"],
            },
        ),
        # File operations
        types.Tool(
            name="list_files",
            description="List files and directories with detailed information",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path to list"},
                    "recursive": {
                        "type": "boolean",
                        "default": False,
                        "description": "List files recursively",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "File pattern to match (e.g., '*.py')",
                    },
                },
                "required": ["path"],
            },
        ),
        types.Tool(
            name="read_file",
            description="Read and display file contents with syntax awareness",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to read"},
                    "lines": {
                        "type": "integer",
                        "description": "Maximum number of lines to read (optional)",
                    },
                    "encoding": {
                        "type": "string",
                        "default": "utf-8",
                        "description": "File encoding",
                    },
                },
                "required": ["path"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: Dict[str, Any]
) -> List[types.TextContent]:
    """Handle tool execution."""
    ctx = server.request_context

    try:
        if name == "list_doctypes":
            result = await ctx.lifespan_context["document_tools"].list_doctypes(
                arguments.get("module")
            )
        elif name == "get_document":
            result = await ctx.lifespan_context["document_tools"].get_document(
                arguments["doctype"], arguments["name"], arguments.get("fields")
            )
        elif name == "search_documents":
            result = await ctx.lifespan_context["document_tools"].search_documents(
                arguments["doctype"],
                arguments.get("query"),
                arguments.get("filters", {}),
                arguments.get("limit", 20),
                arguments.get("fields"),
            )
        elif name == "execute_sql":
            result = await ctx.lifespan_context["database_tools"].execute_sql(
                arguments["query"], arguments.get("limit", 100)
            )
        elif name == "get_system_info":
            result = await ctx.lifespan_context["system_tools"].get_system_info()
        elif name == "bench_command":
            result = await ctx.lifespan_context["system_tools"].bench_command(
                arguments["command"], arguments.get("args", [])
            )
        elif name == "list_files":
            result = await ctx.lifespan_context["file_tools"].list_files(
                arguments["path"],
                arguments.get("recursive", False),
                arguments.get("pattern"),
            )
        elif name == "read_file":
            result = await ctx.lifespan_context["file_tools"].read_file(
                arguments["path"],
                arguments.get("lines"),
                arguments.get("encoding", "utf-8"),
            )
        else:
            raise ValueError(f"Unknown tool: {name}")

        return [types.TextContent(type="text", text=str(result))]
    except Exception as e:
        error_msg = f"Error executing {name}: {str(e)}"
        return [types.TextContent(type="text", text=error_msg)]


async def run_server():
    """Main server run function"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="erpnext-mcp-server",
                server_version="1.0.0.",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(run_server())

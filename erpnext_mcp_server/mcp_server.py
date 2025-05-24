"""ERPNext MCP Server using low-level implementation"""

import asyncio
import logging
import sys
from collections.abc import AsyncIterable
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, List

import frappe
import mcp.server.stdio
import mcp.types as types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ERPNextContext:
    """Context for ERPNext operations."""

    def __init__(self) -> None:
        self.initialized = False
        self.site = None

    async def connect(self):
        """Initialize Frappe connection."""
        try:
            if not frappe.db:
                frappe.init_site()
                frappe.connect()

            self.site = frappe.local.site
            self.initialized = True
            logger.info(f"Connected to ERPNext site: {self.site}")

        except Exception as e:
            logger.error(f"Failed to connect to ERPNext; {e}")
            raise

    async def disconnect(self):
        """Clean up Frappe connection."""
        try:
            if frappe.db:
                frappe.db.close()
            logger.info("Disconnected from ERPNext")
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")


@asynccontextmanager
async def server_lifespan(server: Server) -> AsyncIterator[Dict[str, Any]]:
    """Manage server startup and shutdown lifecycle."""
    logger.info("Starting ERPNext MCP Server...")

    # Initialize ERPNext context
    erpnext_ctx = ERPNextContext()
    await erpnext_ctx.connect()

    try:
        yield {"erpnext": erpnext_ctx}
    finally:
        # Clean up on shutdown
        await erpnext_ctx.disconnect()
        logger.info("ERPNext MCP Server stopped")


# Create server with lifespan management
server = Server("erpnext-mcp-server", lifespan=server_lifespan)


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools."""
    return [
        types.Tool(
            name="list_doctypes",
            description="List all available doctypes in ERPNext",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="get_document",
            description="Get a specific document from ERPNext",
            inputSchema={
                "type": "object",
                "properties": {
                    "doctype": {"type": "string", "description": "Document type name"},
                    "name": {"type": "string", "description": "Document name/ID"},
                },
                "required": ["doctype", "name"],
            },
        ),
        types.Tool(
            name="search_documents",
            description="Search documents in ERPNext",
            inputSchema={
                "type": "object",
                "properties": {
                    "doctype": {
                        "type": "string",
                        "description": "Document type to search",
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 20,
                    },
                },
                "required": ["doctype", "query"],
            },
        ),
        types.Tool(
            name="create_document",
            description="Create a new document in ERPNext",
            inputSchema={
                "type": "object",
                "properties": {
                    "doctype": {
                        "type": "string",
                        "description": "Document type to create",
                    },
                    "data": {
                        "type": "object",
                        "description": "Document data as JSON object",
                    },
                },
                "required": ["doctype", "data"],
            },
        ),
        types.Tool(
            name="update_document",
            description="Update an existing document in ERPNext",
            inputSchema={
                "type": "object",
                "properties": {
                    "doctype": {"type": "string", "description": "Document type"},
                    "name": {"type": "string", "description": "Document name/ID"},
                    "data": {"type": "object", "description": "Updated document data"},
                },
                "required": ["doctype", "name", "data"],
            },
        ),
        types.Tool(
            name="execute_sql",
            description="Execute read-only SQL query on ERPNext database",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "SQL SELECT query"}
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="get_system_info",
            description="Get ERPNext system information",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="bench_command",
            description="Execute safe bench commands",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Bench command to execute (status, version, migrate, etc.)",
                    }
                },
                "required": ["command"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution."""
    ctx = server.request_context
    erpnext_ctx = ctx.lifespan_context["erpnext"]

    if not erpnext_ctx.initialized:
        return [types.TextContent(type="text", text="Error: ERPNext not initialized")]

    try:
        result = await execute_tool(name, arguments)
        return [types.TextContent(type="text", text=result)]

    except Exception as e:
        logger.error(f"Tool {name} failed: {e}")
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]


async def execute_tool(name: str, arguments: dict) -> str:
    """Execute the requested tool."""
    if name == "list_doctypes":
        return await list_doctypes()

    elif name == "get_document":
        doctype = arguments["doctype"]
        doc_name = arguments["name"]
        return await get_document(doctype, doc_name)

    elif name == "search_documents":
        doctype = arguments["doctype"]
        query = arguments["query"]
        limit = arguments.get("limit", 20)
        return await search_documents(doctype, query, limit)

    elif name == "create_document":
        doctype = arguments["doctype"]
        data = arguments["data"]
        return await create_document(doctype, data)

    elif name == "update_document":
        doctype = arguments["doctype"]
        doc_name = arguments["name"]
        data = arguments["data"]
        return await update_document(doctype, doc_name, data)

    elif name == "execute_sql":
        query = arguments["query"]
        return await execute_sql_query(query)

    elif name == "get_system_info":
        return await get_system_info()

    elif name == "bench_command":
        command = arguments["command"]
        return await execute_bench_command(command)

    else:
        raise ValueError(f"Unknown tool: {name}")


# Tool implementations
async def list_doctypes() -> str:
    """List all doctypes."""
    try:
        doctypes = frappe.get_all(
            "DocType",
            fields=["name", "module", "is_custom", "description"],
            filters={"istable": 0},
            order_by="name",
        )
        result = "📋 Available DocTypes:\n\n"
        for dt in doctypes:
            icon = "🔧" if dt.get("is_custom") else "📄"
            result += f"{icon} {dt['name']} ({dt.get('module', 'Unknown')})\n"
            if dt.get("description"):
                result += f"   {dt['description']}\n"

        return result

    except Exception as e:
        raise Exception(f"Failed to list doctypes: {e}")


async def get_document(doctype: str, name: str) -> str:
    """Get a specific document."""
    try:
        doc = frappe.get_doc(doctype, name)
        doc_dict = doc.as_dict()

        result = f"📄 Document: {doctype} - {name}\n\n"

        # Show key fields first
        key_fields = [
            "name",
            "title",
            "subject",
            "customer",
            "supplier",
            "item_code",
            "status",
        ]
        shown_fields = set()

        for field in key_fields:
            if field in doc_dict and doc_dict[field]:
                result += f"{field}: {doc_dict[field]}\n"
                shown_fields.add(field)

        result += "\n--- All Fields ---\n"
        for field, value in doc_dict.items():
            if field not in shown_fields and not field.startswith("_"):
                if isinstance(value, (str, int, float)):
                    result += f"{field}: {value}\n"
                elif isinstance(value, list) and value:
                    result += f"{field}: [{len(value)} items]\n"
        return result
    except Exception as e:
        raise Exception(f"Failed to get document {doctype}/{name}: {e}")


async def search_documents(doctype: str, query: str, limit: int = 20) -> str:
    """Search documents."""
    try:
        results = frappe.get_all(
            doctype,
            filters=[["name", "like", f"%{query}%"]],
            fields=["name", "modified"],
            limit=limit,
            order_by="modified desc",
        )

        if not results:
            return f"🔍 No results found for '{query}' in {doctype}"

        result = f"🔍 Search Results for '{query}' in {doctype}:\n\n"
        for i, doc in enumerate(results, 1):
            result += (
                f"{i}. {doc['name']} (Modified: {doc.get('modified', 'Unknown')})\n"
            )

        return result

    except Exception as e:
        raise Exception(f"Failed to search {doctype}: {e}")


async def create_document(doctype: str, data: dict) -> str:
    """Create a new document."""
    try:
        if not isinstance(data, dict):
            raise ValueError("The 'data' argument must be a dictionary.")
        doc = frappe.get_doc({"doctype": doctype, **data})
        doc.insert()
        frappe.db.commit()

        return f"✅ Created {doctype}: {doc.name}"

    except Exception as e:
        raise Exception(f"Failed to create {doctype}: {e}")


async def update_document(doctype: str, name: str, data: dict) -> str:
    """Update an existing document."""
    try:
        doc = frappe.get_doc(doctype, name)
        doc.update(data)
        doc.save()
        frappe.db.commit()

        return f"✅ Updated {doctype}: {name}"

    except Exception as e:
        raise Exception(f"Failed to update {doctype}/{name}: {e}")


async def execute_sql_query(query: str) -> str:
    """Execute SQL query."""
    try:
        # Security check
        if not query.strip().upper().startswith("SELECT"):
            raise Exception("Only SELECT queries are allowed for security")

        results = list(frappe.db.sql(query, as_dict=True))

        if not results:
            return "📊 Query executed successfully - No results"

        result = f"📊 Query Results ({len(results)} rows):\n\n"

        # Show first few rows in formatted way
        for i, row in enumerate(results[:10]):
            result += f"Row {i + 1}:\n"
            if isinstance(row, dict):
                for key, value in row.items():
                    result += f" {key}: {value}\n"
            elif isinstance(row, (list, tuple)):
                for idx, value in enumerate(row):
                    result += f" {idx}: {value}\n"
            else:
                result += f" {row}\n"
            result += "\n"

        if len(results) > 10:
            result += f"... and {len(results) - 10} more rows\n"

        return result
    except Exception as e:
        raise Exception(f"SQL query failed: {e}")


async def get_system_info() -> str:
    """Get system information."""
    try:
        info = {
            "site": frappe.local.site,
            "frappe_version": frappe.__version__,
            "apps": frappe.get_installed_apps(),
            "db_name": frappe.conf.db_name,
            "current_user": getattr(frappe.session, "user", "Unknown"),
        }

        result = "🖥️ ERPNext System Information:\n\n"
        result += f"Site: {info['site']}\n"
        result += f"Frappe Version: {info['frappe_version']}\n"
        result += f"Database: {info['db_name']}\n"
        result += f"Current User: {info['current_user']}\n"
        result += f"\nInstalled Apps ({len(info['apps'])}):\n"

        for app in info["apps"]:
            result += f"  • {app}\n"

        return result

    except Exception as e:
        raise Exception(f"Failed to get system info: {e}")


async def execute_bench_command(command: str) -> str:
    """Execute bench command."""
    import subprocess

    try:
        # Security: only allow safe commands
        safe_commands = ["status", "version", "migrate", "list", "restart"]
        cmd_parts = command.split()

        if not cmd_parts or cmd_parts[0] not in safe_commands:
            raise Exception(f"Command not allowed. Safe commands: {safe_commands}")

        # Execute command
        result = subprocess.run(
            ["bench"] + cmd_parts,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=frappe.get_site_path(".."),
        )

        output = f"🔧 Bench Command: {command}\n\n"

        if result.returncode == 0:
            output += f"✅ Success:\n{result.stdout}"
        else:
            output += f"❌ Failed (code {result.returncode}):\n{result.stderr}"

        return output

    except subprocess.TimeoutExpired:
        raise Exception("Command timed out after 30 seconds")
    except Exception as e:
        raise Exception(f"Bench command failed: {e}")


async def run_server():
    """Run the MCP server."""
    try:
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="ERPNext MCP Server",
                    server_version="1.0.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise


def main():
    """Entry point."""
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

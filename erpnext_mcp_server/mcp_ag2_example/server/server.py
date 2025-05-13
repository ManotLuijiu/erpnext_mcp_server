import asyncio
import json
import logging
import os
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

import frappe
from frappe import _

# Import MCP libraries
from mcp.server import Server as MCPServer
from mcp.types import Resource, TextContent, Tool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ERPNextMCPServer:
    """MCP Server implementation for ERPNext integration.

    This class bridges between ERPNext's synchronous world and MCP's asynchronous world.
    It manages an MCP server in a separate thread with an event loop.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """Singleton pattern to ensure only one server instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ERPNextMCPServer, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, site_name=None):
        """Initialize the MCP server with ERPNext integration.

        Args:
            site_name (_type_, optional): _description_. Defaults to None.
        """
        if self._initialized:
            return

        self.site_name = site_name or frappe.local.site
        self.loop = None
        self.server_thread = None
        self.mcp_server = None
        self.is_running = False

        # Base path for file operations
        self.base_path = Path(frappe.get_site_path("private", "files", "mcp_data"))
        self.base_path.mkdir(exist_ok=True, parents=True)

        # Initialize MCP server in a separate thread
        self._initialized = True
        self.start_server()

    def start_server(self):
        """Start the MCP server in a separate thread."""
        if self.is_running:
            return

        def run_server_thread():
            """Run the async event loop in a separate thread."""
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

            # Create and initialize MCP server
            self.mcp_server = MCPServer("erpnext-mcp-server")

            # Initialize MCP server
            self.mcp_server = MCPServer("erpnext-mcp-server")

            # Register handlers
            self._register_handlers()

            # Run the event loop until stopped
            self.is_running = True
            self.loop.run_forever()

        self.server_thread = threading.Thread(target=run_server_thread, daemon=True)
        self.server_thread.start()
        logger.info("ERPNext MCP Server started in background thread")

    def stop_server(self):
        """Stop the MCP server."""
        if not self.is_running:
            return

        if self.loop:
            # Schedule loop stop from the main thread
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.server_thread.join(timeout=5)  # type: ignore
            self.is_running = False
            logger.info("ERPNext MCP Server stopped")

    def _register_handlers(self):
        """Register all MCP protocol handlers."""

        @self.mcp_server.list_resources()  # type: ignore
        async def handle_list_resources():
            """List available ERPNext resources."""
            # This will run in the server thread
            resources = []

            # Add ERPNext DocTypes as resources
            doctyp_list = self._run_in_frappe(
                lambda: frappe.get_all("DocType", fields=["name"])
            )
            for dt in doctyp_list:  # type: ignore
                resources.append(
                    Resource(
                        uri=f"erp://doctype/{dt['name']}",  # type: ignore
                        name=dt["name"],
                        description=f"ERPNext DocType: {dt['name']}",
                        mimeType="application/json",
                    )
                )

            # Add file resources
            resources.append(
                Resource(
                    uri="storage://local/",  # type: ignore
                    name="Local Document Store",
                    description="Files stored in ERPNext private files",
                    mimeType="text/plain",
                )
            )

            return resources

        @self.mcp_server.read_resource()  # type: ignore
        async def handle_read_resource(uri: str) -> str:
            """Read a resource based on URI pattern."""
            uri_str = str(uri)

            # Handle DocType resources
            if uri_str.startswith("erp://doctype/"):
                doctype = uri_str.split("erp://doctype/")[1]

                # Capture any filters in the URI
                filters = {}
                if "?" in doctype:
                    doctype, query = doctype.split("?", 1)
                    for param in query.split("&"):
                        if "=" in param:
                            key, value = param.split("=", 1)
                            filters[key] = value

                # Get doctype data
                result = self._run_in_frappe(
                    lambda: frappe.get_all(
                        doctype, fields=["*"], filters=filters, limit=100
                    )
                )
                return json.dumps(result, indent=2)

            # Handle file resources
            elif uri_str.startswith("storage://local/"):
                path = uri_str.split("storage://local/")[1]
                full_path = (self.base_path / path).resolve()

                # Security check - ensure path is within base_path
                if not str(full_path).startswith(str(self.base_path)):
                    raise ValueError(
                        f"Access denied: Path {path} is outside base directory"
                    )

                if not full_path.exists():
                    raise FileNotFoundError(f"Resource not found: {path}")

                with open(full_path, "r") as f:
                    return f.read()

            else:
                raise ValueError(f"Unsupported URI format: {uri}")

        @self.mcp_server.list_tools()  # type: ignore
        async def handle_list_tools():
            """List available tools for ERPNext operations."""
            return [
                Tool(
                    name="write_file",
                    description="Write content to a file in ERPNext's private files",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "content": {"type": "string"},
                        },
                        "required": ["path", "content"],
                    },
                ),
                Tool(
                    name="update_erp_record",
                    description="Update an existing record in ERPNext",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "doctype": {"type": "string"},
                            "name": {"type": "string"},
                            "values": {"type": "object"},
                        },
                        "required": ["doctype", "name", "values"],
                    },
                ),
            ]

        @self.mcp_server.call_tool()  # type: ignore
        async def handle_call_tool(
            name: str, arguments: dict | None
        ) -> List[TextContent]:
            """Handle tool invocation with proper response formatting."""
            try:
                if not arguments:
                    arguments = {}

                if name == "write_file":
                    return [await self._write_file(arguments)]

                elif name == "create_erp_record":
                    return [await self._create_erp_record(arguments)]
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]

            except Exception as e:
                return [
                    TextContent(
                        type="text", text=f"Error executing tool {name}: {str(e)}"
                    )
                ]

    async def _write_file(self, arguments: Dict[str, Any]) -> TextContent:
        """Write content to a file in ERPNext's private files."""
        path = arguments.get("path")
        content = arguments.get("content")

        if not path or not content:
            raise ValueError("Both path and content are required")

        try:
            full_path = (self.base_path / path).resolve()

            # Security check - ensure path is within base_path
            if not str(full_path).startswith(str(self.base_path)):
                raise ValueError(
                    f"Access denied: Path {path} is outside base directory"
                )

            # Create parent directories if they don't exist
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Write the file
            with open(full_path, "w") as f:
                f.write(content)

            return TextContent(
                type="text",
                text=json.dumps(
                    {"status": "success", "path": path, "bytes_written": len(content)},
                    indent=2,
                ),
            )

        except Exception as e:
            raise RuntimeError(f"Failed to write file: {e}")

    async def _create_erp_record(self, arguments: Dict[str, Any]) -> TextContent:
        """Create a new record in ERPNext"""
        doctype = arguments.get("doctype")
        values = arguments.get("values", {})

        if not doctype:
            raise ValueError("doctype is required")

        try:
            # Run in Frappe's environment
            result = self._run_in_frappe(lambda: self._create_doc(doctype, values))

            return TextContent(
                type="text",
                text=json.dumps(
                    {
                        "status": "success",
                        "doctype": doctype,
                        "name": result.get("name") if result else None,
                        "creation": result.get("creation") if result else None,
                    },
                    indent=2,
                ),
            )

        except Exception as e:
            raise RuntimeError(f"Failed to create record: {e}")

    def _create_doc(self, doctype, values):
        """Create a document in Frappe (runs in Frappe thread)."""
        try:
            doc = frappe.new_doc(doctype)
            doc.update(values)
            doc.insert()
            frappe.db.commit()
            return {"name": doc.name, "creation": str(doc.creation)}
        except Exception as e:
            frappe.db.rollback()
            raise e

    async def _update_erp_record(self, arguments: Dict[str, Any]) -> TextContent:
        """Update an existing record in ERPNext."""
        doctype = arguments.get("doctype")
        name = arguments.get("name")
        values = arguments.get("values", {})

        if not doctype or not name:
            raise ValueError("Both doctype and name are required")

        try:
            # Run in Frappe's environment
            result = self._run_in_frappe(
                lambda: self._update_doc(doctype, name, values)
            )

            return TextContent(
                type="text",
                text=json.dumps(
                    {
                        "status": "success",
                        "doctype": doctype,
                        "name": name,
                        "modified": result.get("modified") if result else None,
                    },
                    indent=2,
                ),
            )

        except Exception as e:
            raise RuntimeError(f"Failed to update record: {e}")

    def _update_doc(self, doctype, name, values):
        """Update a document in Frappe (runs in Frappe thread)."""
        try:
            doc = frappe.get_doc(doctype, name)
            doc.update(values)
            doc.save()
            frappe.db.commit()
            return {"modified": str(doc.modified)}
        except Exception as e:
            frappe.db.rollback()
            raise e

    def _run_in_frappe(self, func):
        """Run a function in Frappe's context/thread.

        This is necessary because Frappe operations must run in the main thread, not in our async event loop thread.
        """
        result = None
        exception = None

        def wrapper():
            nonlocal result, exception
            try:
                # Switch to the correct site context if needed
                if (
                    hasattr(frappe.local, "site")
                    and frappe.local.site != self.site_name
                ):
                    frappe.init(site=self.site_name)
                    frappe.connect()

                result = func()
            except Exception as e:
                exception = e
            finally:
                # Reset site context if we changed it
                if (
                    hasattr(frappe.local, "site")
                    and frappe.local.site != self.site_name
                ):
                    frappe.destroy()

        # If we're already in the main thread, just execute
        if threading.current_thread() is threading.main_thread():
            wrapper()
        else:
            # Otherwise, we need to use a synchronization mechanism
            # to run in the main thread and wait for the result
            event = threading.Event()

            def main_thread_task():
                wrapper()
                event.set()

            # Schedule the task to run in the main thread
            frappe.enqueue(main_thread_task, queue="short")

            # Wait for the task to complete (with timeout)
            if not event.wait(timeout=30):
                raise TimeoutError("Frappe operation timed out")
        if exception:
            raise exception

        return result


# Global instance
def get_mcp_server() -> ERPNextMCPServer:
    """Get or create the global MCP server instance."""
    return ERPNextMCPServer()

#!/usr/bin/env python3

"""
Standalone MCP Server for ERPNext
This server can run independently from the Frappe process
"""

import os
import sys
import json
import asyncio
from typing import Dict, List, Any, Optional
from pathlib import Path

# Add the ERPNext site path to Python path
site_path = os.environ.get("FRAPPE_SITE_PATH")
if site_path:
    sys.path.insert(0, site_path)

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        Resource,
        Tool,
        TextContent,
        ImageContent,
        EmbeddedResource,
        CallToolResult,
    )
except ImportError as e:
    print(f"Error importing MCP modules: {e}")
    sys.exit(1)


class ERPNextMCPServer:
    def __init__(self, site_name: str):
        self.site_name = site_name
        self.server = Server("erpnext-mcp-server")
        self.setup_tools()
        self.setup_resources()

    def setup_frappe_context(self):
        """Initialize Frappe context for database operations"""
        import frappe

        frappe.init(site=self.site_name)
        frappe.connect()

    def call_frappe_method(self, method_path: str, **kwargs) -> Any:
        """Call a Frappe method safely"""
        try:
            self.setup_frappe_context()
            import frappe

            # Import the method
            module_path, method_name = method_path.rsplit(".", 1)
            module = __import__(module_path, fromlist=[method_name])
            method = getattr(module, method_name)

            # Call the method
            result = method(**kwargs)

            # Commit changes
            frappe.db.commit()

            return result

        except Exception as e:
            frappe.db.rollback() if "frappe" in sys.modules else None
            raise e
        finally:
            if "frappe" in sys.modules:
                frappe.destroy()

    def setup_tools(self):
        """Setup available tools"""

        @self.server.call_tool()
        async def get_document(
            doctype: str, name: str, fields: Optional[List[str]] = None
        ) -> List[TextContent]:
            """Get a specific document from ERPNext"""
            try:
                result = self.call_frappe_method(
                    "frappe.get_doc", doctype=doctype, name=name
                )

                if fields:
                    result = {field: result.get(field) for field in fields}

                return [
                    TextContent(
                        type="text", text=json.dumps(result, indent=2, default=str)
                    )
                ]

            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]

        @self.server.call_tool()
        async def search_documents(
            doctype: str,
            filters: Optional[Dict] = None,
            fields: Optional[List[str]] = None,
            limit: int = 10,
        ) -> List[TextContent]:
            """Search for documents in ERPNext"""
            try:
                filters = filters or {}
                fields = fields or ["name"]

                result = self.call_frappe_method(
                    "frappe.get_all",
                    doctype=doctype,
                    filters=filters,
                    fields=fields,
                    limit=limit,
                )

                return [
                    TextContent(
                        type="text", text=json.dumps(result, indent=2, default=str)
                    )
                ]

            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]

        @self.server.call_tool()
        async def create_document(doctype: str, doc_data: Dict) -> List[TextContent]:
            """Create a new document in ERPNext"""
            try:
                result = self.call_frappe_method(
                    "frappe.get_doc", doctype=doctype, **doc_data
                )

                # Insert the document
                result.insert()

                return [
                    TextContent(
                        type="text",
                        text=f"Document created successfully: {result.name}",
                    )
                ]

            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]

        @self.server.call_tool()
        async def run_query(query: str, as_dict: bool = True) -> List[TextContent]:
            """Run a SQL query on ERPNext database"""
            try:
                result = self.call_frappe_method(
                    "frappe.db.sql", query=query, as_dict=as_dict
                )

                return [
                    TextContent(
                        type="text", text=json.dumps(result, indent=2, default=str)
                    )
                ]

            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]

        @self.server.call_tool()
        async def get_report(
            report_name: str, filters: Optional[Dict] = None
        ) -> List[TextContent]:
            """Get report data from ERPNext"""
            try:
                result = self.call_frappe_method(
                    "frappe.desk.query_report.run",
                    report_name=report_name,
                    filters=filters or {},
                )

                return [
                    TextContent(
                        type="text", text=json.dumps(result, indent=2, default=str)
                    )
                ]

            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]

        @self.server.call_tool()
        async def execute_method(method_path: str, **kwargs) -> List[TextContent]:
            """Execute a custom Frappe method"""
            try:
                result = self.call_frappe_method(method_path, **kwargs)

                return [
                    TextContent(
                        type="text", text=json.dumps(result, indent=2, default=str)
                    )
                ]

            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    def setup_resources(self):
        """Setup available resources"""

        @self.server.list_resources()
        async def list_resources() -> List[Resource]:
            """List available resources"""
            return [
                Resource(
                    uri="erpnext://doctypes",
                    name="Available DocTypes",
                    description="List of all DocTypes in ERPNext",
                    mimeType="application/json",
                ),
                Resource(
                    uri="erpnext://reports",
                    name="Available Reports",
                    description="List of all Reports in ERPNext",
                    mimeType="application/json",
                ),
                Resource(
                    uri="erpnext://config",
                    name="Server Configuration",
                    description="Current ERPNext configuration",
                    mimeType="application/json",
                ),
            ]

        @self.server.read_resource()
        async def read_resource(uri: str) -> str:
            """Read resource content"""
            try:
                if uri == "erpnext://doctypes":
                    doctypes = self.call_frappe_method(
                        "frappe.get_all",
                        doctype="DocType",
                        fields=["name", "module", "issingle", "custom"],
                        order_by="name",
                    )
                    return json.dumps(doctypes, indent=2)

                elif uri == "erpnext://reports":
                    reports = self.call_frappe_method(
                        "frappe.get_all",
                        doctype="Report",
                        fields=["name", "report_type", "module", "is_standard"],
                        order_by="name",
                    )
                    return json.dumps(reports, indent=2)

                elif uri == "erpnext://config":
                    config = {
                        "site": self.site_name,
                        "version": self.call_frappe_method("frappe.__version__"),
                        "apps": self.call_frappe_method("frappe.get_installed_apps"),
                    }
                    return json.dumps(config, indent=2)

                else:
                    return json.dumps({"error": "Resource not found"})

            except Exception as e:
                return json.dumps({"error": str(e)})

    async def run(self, transport: str = "stdio"):
        """Run the MCP server"""
        if transport == "stdio":
            async with stdio_server() as streams:
                await self.server.run(*streams)
        else:
            # Add support for other transports (HTTP, WebSocket, etc.) later
            raise NotImplementedError(f"Transport {transport} not implemented")


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="ERPNext MCP Server")
    parser.add_argument("--site", required=True, help="Frappe site name")
    parser.add_argument("--transport", default="stdio", help="Transport protocol")

    args = parser.parse_args()

    # Set environment variables for Frappe
    os.environ["FRAPPE_SITE"] = args.site

    # Create and run the server
    server = ERPNextMCPServer(args.site)
    await server.run(args.transport)


if __name__ == "__main__":
    asyncio.run(main())

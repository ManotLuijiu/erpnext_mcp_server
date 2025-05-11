# erpnext_mcp_server/mcp/local_server.py (fixed version)
import asyncio
import logging
import click
import json
import os
from contextlib import asynccontextmanager
from typing import Dict, Any
from pathlib import Path
import frappe
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LocalERPNextMCPServer:
    def __init__(self, site_name: str):
        self.site_name = site_name

        # Ensure we're in the right directory
        frappe_bench_dir = Path.home() / "frappe-bench"
        if os.getcwd() != str(frappe_bench_dir):
            os.chdir(frappe_bench_dir)
            logger.info(f"Changed working directory to: {os.getcwd()}")

        # Create server with simple lifespan
        self.mcp_server = Server(
            name="erpnext-mcp-local",
            version="1.0.0-dev",
            instructions="Local ERPNext MCP Server for development",
            lifespan=self.local_lifespan,
        )

        self.setup_tools()

    @asynccontextmanager
    async def local_lifespan(self, server: Server):
        """Simple lifespan for local development"""
        logger.info(f"Starting local MCP server for site: {self.site_name}")

        # Simple context for local dev
        context = {
            "site_name": self.site_name,
            "request_count": 0,
        }

        try:
            yield context
        finally:
            logger.info("Shutting down local MCP server")

    def setup_tools(self):
        """Set up basic tools for testing"""

        @self.mcp_server.call_tool()
        async def get_customer_info(name: str, arguments: Dict[str, Any]):
            """Get customer information"""
            try:
                # Initialize Frappe with explicit directory
                frappe.init(site=self.site_name)
                frappe.connect()

                try:
                    customer_name = arguments.get("customer_name", "_Test Customer")

                    # Check if customer exists
                    if not frappe.db.exists("Customer", customer_name):
                        # Try to find any customer
                        customers = frappe.get_list("Customer", limit=1)
                        if customers:
                            # Use the first available customer
                            customer_name = customers[0].name
                            logger.info(f"Using existing customer: {customer_name}")
                        else:
                            # Create a test customer
                            logger.info(f"Creating test customer: {customer_name}")
                            test_customer = frappe.get_doc(
                                {
                                    "doctype": "Customer",
                                    "customer_name": customer_name,
                                    "customer_type": "Individual",
                                    "customer_group": "Individual",
                                    "territory": "All Territories",
                                }
                            )
                            test_customer.insert()
                            frappe.db.commit()

                    customer = frappe.get_doc("Customer", customer_name)

                    result = {
                        "name": customer.name,
                        "customer_name": customer.customer_name,
                        "email": customer.email_id or "N/A",
                        "mobile": customer.mobile_no or "N/A",
                        "customer_group": customer.customer_group or "N/A",
                        "territory": customer.territory or "N/A",
                        "creation": str(customer.creation)
                        if customer.creation
                        else "N/A",
                    }

                    return [
                        types.TextContent(
                            type="text", text=json.dumps(result, indent=2)
                        )
                    ]

                except Exception as e:
                    logger.error(f"Tool error: {str(e)}")
                    frappe.db.rollback()
                    return [types.TextContent(type="text", text=f"Error: {str(e)}")]
                finally:
                    frappe.destroy()

            except Exception as site_error:
                logger.error(f"Site error: {str(site_error)}")
                return [
                    types.TextContent(
                        type="text",
                        text=f"Site Error: {str(site_error)}. Working directory: {os.getcwd()}",
                    )
                ]


@click.command()
@click.option("--site", required=True, help="ERPNext site name")
def main(site: str):
    """Run local MCP server using stdio for testing"""

    async def run_server():
        # Create server instance
        server = LocalERPNextMCPServer(site_name=site)

        # Run with stdio (easier for testing)
        async with stdio_server() as (read_stream, write_stream):
            await server.mcp_server.run(
                read_stream,
                write_stream,
                server.mcp_server.create_initialization_options(),
            )

    # Run the server
    asyncio.run(run_server())


if __name__ == "__main__":
    main()

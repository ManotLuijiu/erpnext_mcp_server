# erpnext_mcp_server/mcp/http_server.py
import asyncio
import logging
import click
import json
import frappe
from mcp.server.lowlevel import Server
import mcp.types as types
import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.requests import Request
from starlette.routing import Route

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleHTTPMCPServer:
    def __init__(self, site_name: str):
        self.site_name = site_name
        self.mcp_server = Server(name="erpnext-http-mcp")
        self.setup_tools()

    def setup_tools(self):
        @self.mcp_server.call_tool()
        async def get_customer_info(name: str, arguments: dict):
            frappe.init(site=self.site_name)
            frappe.connect()

            try:
                customer_name = arguments.get("customer_name")
                customer = frappe.get_doc("Customer", customer_name)

                result = {
                    "name": customer.name,
                    "customer_name": customer.customer_name,
                    "email": customer.email_id or "N/A",
                }

                return [
                    types.TextContent(type="text", text=json.dumps(result, indent=2))
                ]
            except Exception as e:
                return [types.TextContent(type="text", text=f"Error: {str(e)}")]
            finally:
                frappe.destroy()

    async def handle_request(self, request: Request):
        """Simple HTTP handler"""
        try:
            data = await request.json()
            method = data.get("method")

            if method == "tools/list":
                result = await self.mcp_server._list_tools_handler(None)
                return JSONResponse(
                    {
                        "jsonrpc": "2.0",
                        "id": data.get("id"),
                        "result": result.model_dump(),
                    }
                )
            elif method == "tools/call":
                name = data["params"]["name"]
                arguments = data["params"].get("arguments", {})
                result = await self.mcp_server._call_tool_handler(name, arguments)
                return JSONResponse(
                    {
                        "jsonrpc": "2.0",
                        "id": data.get("id"),
                        "result": result.model_dump(),
                    }
                )
            else:
                return JSONResponse(
                    {
                        "jsonrpc": "2.0",
                        "id": data.get("id"),
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {method}",
                        },
                    }
                )
        except Exception as e:
            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "id": data.get("id", 1),
                    "error": {"code": -32000, "message": str(e)},
                }
            )


@click.command()
@click.option("--site", required=True, help="ERPNext site name")
@click.option("--port", default=8100, help="Port to run on")
def run_http_server(site: str, port: int):
    """Run simple HTTP MCP server"""

    server = SimpleHTTPMCPServer(site_name=site)

    app = Starlette(
        routes=[
            Route("/", server.handle_request, methods=["POST"]),
        ]
    )

    uvicorn.run(app, host="127.0.0.1", port=port)


if __name__ == "__main__":
    run_http_server()

import frappe
import os
import sys
import logging
from pathlib import Path

# Import the server from mcp_server.py
# from erpnext_mcp_server.mcp_server import server
from erpnext_mcp_server.mcp_server_fetch.server import erp_server

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("erpnext_mcp_server")


@frappe.whitelist()
def get_server():
    """Return the MCP server instance."""
    return erp_server


if __name__ == "__main__":
    # This will run when executed directly
    logger.info("Starting ERPNext MCP Server in direct mode")
    erp_server.run()

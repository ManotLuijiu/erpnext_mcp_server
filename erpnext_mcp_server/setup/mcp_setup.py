import logging
import frappe
from frappe import _

logger = logging.getLogger(__name__)


def after_install():
    """Setup after app installation."""
    # Create necessary directories
    create_directories()

    # Set up default configuration
    create_default_config()

    # Initialize server on first install
    init_mcp_server()

    logger.info("ERPNext MCP Server installed successfully")


def on_app_update():
    """Handle app updates."""
    # Update configuration if needed
    update_config()

    logger.info("ERPNext MCP Server updated successfully")


def create_directories():
    """Create necessary directories for MCP server operation."""
    import os
    from pathlib import Path

    # Create data directory in site private files
    data_dir = Path(frappe.get_site_path("private", "files", "mcp_data"))
    data_dir.mkdir(exist_ok=True, parents=True)

    logger.info(f"Created MCP data directory: {data_dir}")


def create_default_config():
    """Create default configuration for MCP server."""
    # You can implement this to create any necessary configuration
    # in the Frappe settings system
    pass


def update_config():
    """Update configuration after app update if needed."""
    # You can implement this to update any necessary configuration
    # after app updates
    pass


def init_mcp_server():
    """Initialize the MCP server."""
    try:
        # Import here to avoid circular imports
        from erpnext_mcp_server.mcp_ag2_example.server.server import get_mcp_server

        # This will initialize the server if it's not already running
        server = get_mcp_server()
        server.start_server()
        logger.info("MCP Server initialized")

    except Exception as e:
        logger.error(f"Failed to initialize MCP Server: {e}")


def before_uninstall():
    """Clean up before app uninstallation."""
    try:
        # Import here to avoid circular imports
        from erpnext_mcp_server.mcp_ag2_example.server.server import get_mcp_server

        # Stop the server if it's running
        server = get_mcp_server()
        server.stop_server()
        logger.info("MCP Server stopped")

    except Exception as e:
        logger.error(f"Error stopping MCP Server: {e}")

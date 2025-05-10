import frappe


def get_boot_info(bootinfo):
    """Add MCP server status to bootinfo"""
    try:
        # Check if user has permission to view MCP server status
        if frappe.has_permission("MCP Server Settings", "read"):
            # Get MCP server status
            settings_list = frappe.get_all(
                "MCP Server Settings",
                filters={"enabled": 1},
                fields=["name", "status", "transport", "port", "process_id"],
                limit=1,
            )

            # Add MCP server status to bootinfo
            bootinfo.mcp_server = {
                "available": True,
                "is_running": False,  # Default to False
                "transport": "stdio",  # Default transport
                "port": 8000,  # Default port
            }

            if settings_list:
                settings = settings_list[0]

                # Check if server is actually running
                if settings.get("process_id"):
                    try:
                        import os

                        # Try to check if process exists
                        os.kill(int(settings.get("process_id")), 0)
                        is_running = True
                    except (OSError, ValueError):
                        is_running = False
                else:
                    is_running = False

                # Update bootinfo with status
                bootinfo.mcp_server.update(
                    {
                        "is_running": is_running,
                        "status": settings.get("status"),
                        "transport": settings.get("transport", "stdio"),
                        "port": settings.get("port", 8000),
                    }
                )
    except Exception:
        frappe.log_error("Error fetching MCP server info for boot", "MCP Server")

def after_install():
    # Create default MCP Server Settings
    import frappe

    if not frappe.db.exists("DocType", "MCP Server Settings"):
        return

    # Check if any settings exist
    if not frappe.db.exists("MCP Server Settings"):
        try:
            settings = frappe.new_doc("MCP Server Settings")
            settings.enabled = 0  # type: ignore
            settings.status = "Stopped"  # type: ignore
            settings.transport = "stdio"  # type: ignore
            settings.port = 8000  # type: ignore
            settings.log_level = "INFO"  # type: ignore
            settings.server_name = "ERPNext MCP Server"  # type: ignore
            settings.insert()
            frappe.db.commit()
        except Exception:
            frappe.log_error(
                "Failed to create default MCP Server Settings", "MCP Server"
            )

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def after_install():
    """Actions to be performed after app installation"""
    # Create MCP Terminal role if it doesn't exist
    if not frappe.db.exists("Role", "MCP Terminal User"):
        role = frappe.get_doc(
            {
                "doctype": "Role",
                "role_name": "MCP Terminal User",
                "desk_access": 1,
                "is_custom": 1,
            }
        )
        role.insert(ignore_permissions=True)
        frappe.db.commit()

    # Update MCP Terminal page permissions
    if frappe.db.exists("Page", "mcp-terminal"):
        page = frappe.get_doc("Page", "mcp-terminal")
        # Add MCP Terminal User role if it doesn't exist
        has_role = False
        for role in page.roles:  # type: ignore
            if role.role == "MCP Terminal User":
                has_role = True
                break

        if not has_role:
            page.append("roles", {"role": "MCP Terminal User"})
            page.save(ignore_permissions=True)
            frappe.db.commit()

    # Create default MCP Server Settings
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

import frappe
from frappe import _


def get_context(context):
    """Get context for MCP Terminal page."""
    # Ensure user is authenticated
    if frappe.session.user == "Guest":
        frappe.throw(
            _("Please login to access the MCP Terminal"), frappe.PermissionError
        )

    # Check if user has required permissions
    if not frappe.has_permission("System Manager"):
        # Check for custom MCP Terminal permission
        if not frappe.has_permission("MCP Terminal", "read"):
            frappe.throw(
                _("You don't have permission to access MCP Terminal"),
                frappe.PermissionError,
            )

    context.title = _("ERPNext MCP Terminal")
    context.no_cache = 1

    # Add user context
    context.user = frappe.session.user
    context.site = frappe.local.site
    context.sitename = frappe.local.site_name or frappe.local.site

    # Add system info
    context.system_info = {
        "frappe_version": frappe.__version__,
        "site": frappe.local.site,
        "user": frappe.session.user,
        "session_id": frappe.session.sid,
    }

    return context


@frappe.whitelist()
def get_page_info():
    """Get information about the MCP Terminal page."""
    return {
        "title": _("ERPNext MCP Terminal"),
        "user": frappe.session.user,
        "site": frappe.local.site,
        "has_permission": frappe.has_permission("System Manager")
        or frappe.has_permission("MCP Terminal", "read"),
        "system_info": {
            "frappe_version": frappe.__version__,
            "site": frappe.local.site,
            "user": frappe.session.user,
        },
    }


@frappe.whitelist()
def check_terminal_permissions():
    """Check if user has permission to use MCP Terminal."""
    try:
        # Check System Manager role
        if frappe.has_permission("System Manager"):
            return {"has_permission": True, "role": "System Manager"}

        # Check custom MCP Terminal permission
        if frappe.has_permission("MCP Terminal", "read"):
            return {"has_permission": True, "role": "MCP Terminal User"}

        return {"has_permission": False, "role": None}

    except Exception as e:
        frappe.log_error(f"Error checking MCP Terminal permissions: {str(e)}")
        return {"has_permission": False, "error": str(e)}

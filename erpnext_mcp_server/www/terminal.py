import frappe


def get_context(context):
    """Page context for terminal."""
    context.no_cache = 1
    context.title = "ERPNext MCP Terminal"

    # Check authentication
    if frappe.session.user == "Guest":
        frappe.throw("Please login to access the MCP Terminal", frappe.PermissionError)

    # Add context data
    context.user = frappe.session.user
    context.site = frappe.local.site

    return context

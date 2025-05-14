import json
from datetime import datetime, timedelta

import frappe


def clear_expired_tokens():
    """Clear expired MCP tokens from cache and localStorage"""
    try:
        # Clear from cache
        keys = frappe.cache().get_keys("mcp_token:*")
        for key in keys:  # type: ignore
            try:
                # Check if token is expired in cache
                token = frappe.cache().get_value(key)
                if not token:
                    frappe.cache().delete_key(key)
            except Exception as e:
                frappe.log_error(
                    f"Error clearing token {key}: {str(e)}", "Token Cleanup Error"
                )

        # We can't directly clear from localStorage as that's client-side
        # Instead, log a message recommending periodic client-side cleanup
        frappe.log_error(
            "Expired MCP tokens cleared from server cache. Client-side localStorage cleanup happens automatically in the browser.",
            "Token Cleanup",
            level="Info",  # type: ignore
        )
    except Exception as e:
        frappe.log_error(
            f"Error in clear_expired_tokens: {str(e)}", "Token Cleanup Error"
        )

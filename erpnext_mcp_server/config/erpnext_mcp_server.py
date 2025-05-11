from frappe import _


def get_data():
    return {
        "label": _("MCP Server"),
        "items": [
            {
                "type": "doctype",
                "name": "MCP Server Manager",
                "label": _("MCP Server Manager"),
                "description": _("Manage MCP Servers"),
                "icon": "fa fa-server",
            }
        ],
    }

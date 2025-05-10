import frappe
from frappe import _
import json


def get_context(context):
    context.title = _("MCP Server Dashboard")
    return context

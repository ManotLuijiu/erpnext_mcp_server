import frappe
import json
from frappe.utils.caching import site_cache

socket = frappe.conf.db_socket

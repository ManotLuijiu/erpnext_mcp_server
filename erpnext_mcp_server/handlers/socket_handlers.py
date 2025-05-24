import frappe

frappe.publish_realtime("my_custom_event", {"msg": "Hi!"}, user="Administrator")

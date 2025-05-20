import frappe
from frappe import _


def delivery_slip_connector_socketio(arg1, arg2):
    print(_("==================Connector"))

    # Trigger the event here
    frappe.publish_realtime("item_connector", data={"message": "item-1"})

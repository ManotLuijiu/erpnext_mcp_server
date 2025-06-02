import frappe


@frappe.whitelist()
def execute_terminal_command(command, user):
    """Execute terminal command and send realtime updates"""
    try:
        # Publish initial response
        frappe.publish_realtime(
            event="terminal_output",
            message={"type": "output", "data": f"Executing: {command}\n"},
            # user=frappe.session.user,
            user=user,
        )

        # Simulate command processing (replace with actual command execution)
        import time

        for i in range(1, 4):
            time.sleep(1)
            frappe.publish_realtime(
                event="terminal_output",
                message={"type": "output", "data": f"Processing... {i}\n"},
                # user=frappe.session.user,
                user=user,
            )

        # Final result
        frappe.publish_realtime(
            event="terminal_output",
            message={
                "type": "output",
                "data": f"Result for '{command}': Operation completed successfully\n",
            },
            # user=frappe.session.user,
            user=user,
        )

        return {"success": True}

    except Exception as e:
        frappe.publish_realtime(
            event="terminal_output",
            message={"type": "error", "data": f"Error: {str(e)}\n"},
            # user=frappe.session.user,
            user=user,
        )
        return {"success": False, "error": str(e)}

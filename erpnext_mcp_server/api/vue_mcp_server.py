import subprocess

import frappe


@frappe.whitelist()
def execute_terminal_command(command):
    """Execute terminal command and send realtime updates"""
    try:
        # Security check - only allow certain commands
        allowed_commands = ["pwd", "ls", "whoami", "data"]
        base_command = command.split()[0] if command else ""

        if base_command not in allowed_commands:
            frappe.publish_realtime(
                event="terminal_output",
                message={
                    "type": "error",
                    "data": f"Command not allowed: {base_command}",
                },
                user=frappe.session.user,
            )
            return {"success": False, "error": "Command not allowed"}

        # Echo the command
        # Publish initial response
        frappe.publish_realtime(
            event="terminal_output",
            message={"type": "output", "data": f"Executing: {command}\n"},
            user=frappe.session.user,
        )

        # Simulate command processing (replace with actual command execution)
        # import time

        # for i in range(1, 4):
        #     time.sleep(1)
        #     frappe.publish_realtime(
        #         event="terminal_output",
        #         message={"type": "output", "data": f"Processing... {i}\n"},
        #         user=frappe.session.user,
        #     )

        # Final result
        # frappe.publish_realtime(
        #     event="terminal_output",
        #     message={
        #         "type": "output",
        #         "data": f"Result for '{command}': Operation completed successfully\n",
        #     },
        #     user=frappe.session.user,
        # )

        # Execute the command
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Stream output in realtime
        if process.stdout is not None:
            for line in process.stdout:
                frappe.publish_realtime(
                    event="terminal_output",
                    message={"type": "output", "data": line},
                    user=frappe.session.user,
                )

        # Wait for process to complete
        process.wait()

        return {"success": True}

    except Exception as e:
        frappe.publish_realtime(
            event="terminal_output",
            message={"type": "error", "data": f"Error: {str(e)}\n"},
            user=frappe.session.user,
        )
        return {"success": False, "error": str(e)}

import os
import signal
import subprocess
import threading

import frappe
import frappe.realtime

# Global variables to manage MCP process
mcp_processes = {}  # Store processes by user


def init_socket_handler():
    """Register socket.io handlers on startup"""
    frappe.msgprint("Initializing MCP Terminal socket handlers")

    # Testing
    frappe.publish_realtime("item_connector", data={"message": "item-1"})

    # Register custom events
    frappe.publish_realtime("mcp_terminal_input", handle_terminal_input)


def handle_terminal_input(data, sid=None):
    """Handle terminal input from the client"""
    if not sid:
        return

    # Get the current user
    user = frappe.session.user

    # Start MCP process if not already running
    if user not in mcp_processes or mcp_processes[user]["process"] is None:
        start_mcp_process(user)

    # Send command to the process
    try:
        process = mcp_processes[user]["process"]
        command = data.get("command", "")

        if process and command:
            process.stdin.write((command + "\n").encode("utf-8"))
            process.stdin.flush()
    except Exception as e:
        frappe.log_error(f"Error sending command to MCP: {str(e)}")
        frappe.publish_realtime(
            "mcp_terminal_output", f"\r\nError: {str(e)}\r\n", user=user
        )


def start_mcp_process(user):
    """Start the MCP process for a user"""
    try:
        # Get the command to start MCP Server - adjust this path!
        mcp_command = [
            "python",
            "-c",
            'import time; print("MCP Server started!"); time.sleep(1); print("Ready for commands..."); while True: cmd = input(); print(f"You entered: {cmd}")',
        ]

        # Start the process
        process = subprocess.Popen(
            mcp_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Merge stderr into stdout
            bufsize=0,
        )

        # Store the process
        mcp_processes[user] = {"process": process, "stop_thread": False}

        # Start output reader thread
        output_thread = threading.Thread(target=read_mcp_output, args=(user,))
        output_thread.daemon = True
        output_thread.start()

        frappe.publish_realtime(
            "mcp_terminal_output", f"MCP Server started successfully.\r\n", user=user
        )

    except Exception as e:
        frappe.log_error(f"Error starting MCP process: {str(e)}")
        frappe.publish_realtime(
            "mcp_terminal_output", f"Error starting MCP Server: {str(e)}\r\n", user=user
        )


def read_mcp_output(user):
    """Read output from MCP process and send to client"""
    if user not in mcp_processes:
        return

    process = mcp_processes[user]["process"]

    while process and process.poll() is None and not mcp_processes[user]["stop_thread"]:
        try:
            # Read output a byte at a time for responsive terminal
            byte = process.stdout.read(1)
            if byte:
                # Send to the client
                char = byte.decode("utf-8", errors="replace")
                frappe.publish_realtime("mcp_terminal_output", char, user=user)
            else:
                # Process has ended output
                break
        except Exception as e:
            frappe.log_error(f"Error reading MCP output: {str(e)}")
            break

    # If we're here, the process ended or errored
    if process and process.poll() is not None:
        exit_code = process.poll()
        frappe.publish_realtime(
            "mcp_terminal_output",
            f"\r\nMCP Server exited with code {exit_code}\r\n",
            user=user,
        )
        mcp_processes[user]["process"] = None


def stop_mcp_process(user):
    """Stop the MCP process for a user"""
    if user not in mcp_processes:
        return

    # Signal the thread to stop
    mcp_processes[user]["stop_thread"] = True

    # Terminal the process
    try:
        process = mcp_processes[user]["process"]
        if process:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

            mcp_processes[user]["process"] = None

            return {"success": True}
    except Exception as e:
        frappe.log_error(f"Error stopping MCP process: {str(e)}")

    return {"success": False}


# Add cleanup functions
def cleanup_on_logout():
    """Stop MCP process when user log out"""
    user = frappe.session.user
    stop_mcp_process(user)


def cleanup_all_processes():
    """Stop all MCP processes on server exit"""
    for user in list(mcp_processes.keys()):
        stop_mcp_process(user)

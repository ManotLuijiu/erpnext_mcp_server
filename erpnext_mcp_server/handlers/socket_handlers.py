import json
import os
import signal
import subprocess
import sys
import threading
import traceback

import frappe

# Global variables to manage MCP process
mcp_processes = {}  # Store processes by user


@frappe.whitelist()
def start_mcp_process_api():
    """Start the MCP server process - API method"""
    try:
        user = frappe.session.user

        # Kill any existing process for this user
        if user in mcp_processes and mcp_processes[user].get("process"):
            try:
                process = mcp_processes[user]["process"]
                process.terminate()
                process.wait(timeout=2)
            except:
                pass

        # Very simple test command for debugging
        mcp_command = [
            sys.executable,
            "-c",
            'import sys; print("MCP Server started!"); sys.stdout.flush(); '
            "while True: "
            "    try: "
            '        cmd = input(); print(f"Echo: {cmd}"); sys.stdout.flush(); '
            "    except EOFError: break "
            '    except Exception as e: print(f"Error: {e}"); sys.stdout.flush()',
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

        # Start output reader thread with safe error handling
        output_thread = threading.Thread(target=safe_read_mcp_output, args=(user,))
        output_thread.daemon = True
        output_thread.start()

        return {"success": True, "message": "MCP Server started successfully"}
    except Exception as e:
        # Print to stdout for debugging
        print(f"Error starting MCP process: {str(e)}")
        traceback.print_exc()

        # Try direct output to the client
        try:
            frappe.publish_realtime(
                "mcp_terminal_output",
                f"Error starting MCP Server: {str(e)}\r\n",
                user=frappe.session.user,
            )
        except:
            pass

        return {"success": False, "error": str(e)}


def safe_read_mcp_output(user):
    """Wrapper function with additional error handling"""
    try:
        read_mcp_output(user)
    except Exception as e:
        # Print to stdout for debugging
        print(f"Error in read_mcp_output: {str(e)}")
        traceback.print_exc()

        # Try direct output to the client
        try:
            frappe.publish_realtime(
                "mcp_terminal_output",
                f"\r\nError in output reader: {str(e)}\r\n",
                user=user,
            )
        except:
            pass


@frappe.whitelist()
def send_terminal_input(command):
    """Send input to the MCP process - API method"""
    try:
        user = frappe.session.user

        # Check if process exists
        if user not in mcp_processes or mcp_processes[user]["process"] is None:
            return {"success": False, "error": "MCP Server not running"}

        process = mcp_processes[user]["process"]

        # Send command to process
        if process:
            process.stdin.write((command + "\n").encode("utf-8"))
            process.stdin.flush()
            return {"success": True}

        return {"success": False, "error": "Process not available"}
    except Exception as e:
        frappe.log_error(f"Error sending command to MCP: {str(e)}")
        return {"success": False, "error": str(e)}


def handle_terminal_input(user, message):
    """Handle terminal input from the client"""
    if not user:
        return

    # Start MCP process if not already running
    if user not in mcp_processes or mcp_processes[user]["process"] is None:
        start_mcp_process(user)

    # Send command to the process
    try:
        process = mcp_processes[user]["process"]
        command = message.get("command", "")

        if process and command:
            process.stdin.write((command + "\n").encode("utf-8"))
            process.stdin.flush()
    except Exception as e:
        frappe.log_error(f"Error sending command to MCP: {str(e)}")
        frappe.publish_realtime(
            "mcp_terminal_output", f"\r\nError: {str(e)}\r\n", user=user
        )


@frappe.whitelist()
def start_mcp_process(user):
    """Start an MCP process for a user"""
    try:
        # Simple test command
        mcp_command = [
            "python",
            frappe.get_app_path("erpnext_mcp_server", "api", "mcp_server.py"),
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
        print(f"No MCP process found for user {user}")
        return

    # process = mcp_processes[user]["process"]
    process = mcp_processes[user].get("process")
    if not process:
        print(f"Process object is None for user {user}")
        return

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

    # Terminate the process
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


# Event handlers for socket events
def cleanup_on_logout():
    """Stop MCP process when user logs out"""
    user = frappe.session.user
    stop_mcp_process(user)


def cleanup_all_processes():
    """Stop all MCP processes on server exit"""
    for user in list(mcp_processes.keys()):
        stop_mcp_process(user)


# Handle events from Redis
def realtime_handler(event, message):
    """Handle realtime events from socketio via Redis"""
    try:
        if event == "mcp_terminal_input" and isinstance(message, dict):
            user = message.get("user")
            data = message.get("data", {})
            if user:
                handle_terminal_input(user, data)
    except Exception as e:
        frappe.log_error(f"Error in realtime handler: {str(e)}")

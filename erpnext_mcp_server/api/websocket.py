import json
import os
import select

import frappe
from frappe import _
from frappe.utils import now_datetime

from erpnext_mcp_server.api.terminal import active_sessions, resize_terminal


def handle_terminal_websocket(ws):
    """Handle WebSocket connections for terminal sessions"""
    try:
        # Get session ID from query parameters
        query_params = frappe.request.environ.get("QUERY_STRING", "")
        params = dict(
            param.split("=") for param in query_params.split("&") if "=" in param
        )
        session_id = params.get("session_id")

        if not session_id:
            ws.send(json.dumps({"error": "Session ID is required"}))
            return

        # Check if session exists
        if session_id not in active_sessions:
            ws.send(json.dumps({"error": "Terminal session not found or expired"}))
            return

        session = active_sessions[session_id]

        # Check if the session belongs to the current user
        if session["user"] != frappe.session.user:
            ws.send(
                json.dumps(
                    {
                        "error": "You don't have permission to access this terminal session"
                    }
                )
            )
            return

        # Get the master file descriptor
        master_fd = session["master_fd"]

        # Set up a simple bidirectional proxy between WebSocket and pty
        while True:
            # Update last active timestamp
            session["last_active"] = now_datetime()

            # Check if process is still running
            if session.get("process") and session["process"].poll() is not None:
                # Process has terminated
                ws.send(
                    json.dumps(
                        {"error": "Terminal process has terminated", "close": True}
                    )
                )
                break

            # Use select to monitor both the WebSocket and terminal
            readable, _, _ = select.select([ws.sock, master_fd], [], [], 0.1)

            if ws.sock in readable:
                # Data from WebSocket to terminal
                try:
                    message = ws.receive()
                    if message is None:
                        # WebSocket closed
                        break

                    # Write data to terminal
                    os.write(master_fd, message.encode())
                except Exception as e:
                    frappe.log_error(
                        f"Error receiving from WebSocket: {str(e)}",
                        "Terminal WebSocket Error",
                    )
                    break

            if master_fd in readable:
                # Data from terminal to WebSocket
                try:
                    data = os.read(master_fd, 65536)
                    ws.send(data)
                except Exception as e:
                    frappe.log_error(
                        f"Error reading from terminal: {str(e)}",
                        "Terminal WebSocket Error",
                    )
                    break
    except Exception as e:
        frappe.log_error(
            f"Error in terminal WebSocket handler: {str(e)}", "Terminal WebSocket Error"
        )

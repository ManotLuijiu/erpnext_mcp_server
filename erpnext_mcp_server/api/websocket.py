# erpnext_mcp_server/websocket.py

import json
import os
import select
import time

import frappe
from frappe import _
from frappe.utils import now_datetime

from erpnext_mcp_server.api.terminal import (
    active_sessions,
    log_terminal_command,
    resize_terminal,
)


def handle_terminal_websocket(ws):
    """Handle WebSocket connections for terminal sessions"""
    try:
        # First message should be authentication
        message = ws.receive()
        if not message:
            ws.send(json.dumps({"error": "No authentication data received"}))
            return

        auth_data = json.loads(message)
        session_id = auth_data.get("session_id")

        if not session_id:
            ws.send(json.dumps({"error": "Session ID is required for authentication"}))
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

        # Authentication successful
        ws.send(
            json.dumps(
                {"message": "Authentication successful", "session_id": session_id}
            )
        )

        # Set up WebSocket communication
        master_fd = session["master_fd"]

        # Use select to monitor both WebSocket and terminal
        while True:
            # Update the last active timestamp
            session["last_active"] = now_datetime()

            # Check if the process is still running
            if session.get("process") and session["process"].poll() is not None:
                # Process has terminated
                ws.send(
                    json.dumps(
                        {"error": "Terminal process has terminated", "close": True}
                    )
                )
                break

            # Wait for data from WebSocket or terminal
            try:
                ws_ready = ws.sock.poll(timeout=100)  # Poll with 100ms timeout

                if ws_ready:
                    # Data from WebSocket
                    message = ws.receive()
                    if message is None:
                        # WebSocket closed
                        break

                    data = json.loads(message)

                    # Handle different message types
                    if data.get("type") == "input":
                        # Input to send to terminal
                        input_data = data.get("data", "")
                        os.write(master_fd, input_data.encode())

                        # Log the command if it ends with a newline
                        if input_data.endswith("\n") or input_data.endswith("\r"):
                            log_terminal_command(session_id, input_data.strip())

                    elif data.get("type") == "resize":
                        # Resize the terminal
                        rows = data.get("rows", 24)
                        cols = data.get("cols", 80)
                        # session_id = frappe.local.form_dict.get("session_id")

                        resize_terminal(session_id, rows, cols)

                    elif data.get("type") == "ping":
                        # Respond to ping with pong
                        ws.send(json.dumps({"type": "pong", "time": time.time()}))

                # Check if there's data from the terminal
                ready, _, _ = select.select([master_fd], [], [], 0)
                if ready:
                    output = os.read(master_fd, 65536).decode("utf-8", errors="replace")
                    if output:
                        ws.send(json.dumps({"type": "output", "data": output}))
            except Exception as e:
                frappe.log_error(
                    f"Error in terminal WebSocket communication: {str(e)}",
                    "Terminal WebSocket Error",
                )
                ws.send(json.dumps({"error": str(e), "close": True}))
                break
    except Exception as e:
        frappe.log_error(
            f"Error in terminal WebSocket handler: {str(e)}", "Terminal WebSocket Error"
        )
        try:
            ws.send(json.dumps({"error": str(e), "close": True}))
        except:
            pass

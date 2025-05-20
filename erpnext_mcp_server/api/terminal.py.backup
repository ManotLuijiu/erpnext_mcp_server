import fcntl
import json
import os
import pty
import random
import select
import signal
import string
import struct
import subprocess
import sys
import tempfile
import termios
import time

import frappe
from frappe import _
from frappe.utils import (
    cint,
    get_site_name,
    get_site_path,
    now_datetime,
    time_diff_in_seconds,
)

# Dictionary to store active terminal sessions
active_sessions = {}


@frappe.whitelist()
def get_mcp_settings():
    """Get MCP Server settings based on system information"""
    try:
        # Check if user has permissions
        if not frappe.has_permission("MCP Terminal", "read"):
            frappe.throw(
                _("You don't have permission to access MCP Terminal"),
                frappe.PermissionError,
            )

        site_name = get_site_name()
        print(f"site_name {site_name}")

        site_path = get_site_path()
        print(f"site_path {site_path}")

        # Determine the WebSocket URL based on the current site
        websocket_url = f"wss://{frappe.local.site}/{site_name}/api/websocket/terminal"

        print(f"websocket_url {websocket_url}")

        # Check if the MCP server is running
        mcp_running = is_mcp_server_running()

        print(f"mcp_running {mcp_running}")

        # Get system information
        system_info = {
            "frappe_version": frappe.__version__,
            "site_name": site_name,
            "app_name": "erpnext_mcp_server",
            "user": frappe.session.user,
            "terminal_id": generate_terminal_id(),
        }

        print(f"system_info {system_info}")

        return {
            "api_url": f"/api/method/erpnext_mcp_server.api.terminal.execute_command",  # noqa: F541
            "websocket_url": websocket_url,
            "auto_reconnect": 1,
            "is_configured": True,
            "mcp_running": mcp_running,
            "system_info": system_info,
        }
    except Exception as e:
        frappe.log_error(f"Error getting MCP settings: {str(e)}", "MCP Settings Error")
        return {
            "api_url": None,
            "websocket_url": None,
            "auto_reconnect": 0,
            "is_configured": False,
            "error": str(e),
        }


def is_mcp_server_running():
    """Check if the MCP server is running on this system"""
    try:
        # Check for MCP server process
        # This is just an example - adapt to your actual MCP server process name
        output = subprocess.check_output(
            ["pgrep", "-f", "mcp_server"], stderr=subprocess.STDOUT
        )
        return bool(output.strip())
    except subprocess.CalledProcessError:
        # Process not found
        return False
    except Exception as e:
        frappe.log_error(
            f"Error checking MCP server status: {str(e)}", "MCP Server Check Error"
        )
        return False


def generate_terminal_id():
    """Generate a unique terminal ID"""
    timestamp = int(time.time())
    random_str = "".join(random.choices(string.ascii_letters + string.digits, k=8))
    return f"term_{timestamp}_{random_str}"


@frappe.whitelist()
def create_terminal_session():
    """Create a new terminal session for the MCP server"""
    try:
        # Check permissions
        if not frappe.has_permission("MCP Terminal", "write"):
            frappe.throw(
                _("You don't have permission to create a terminal session"),
                frappe.PermissionError,
            )

        # Generate a unique session ID
        session_id = generate_terminal_id()

        # Create a pseudo-terminal
        master_fd, slave_fd = pty.openpty()

        # Make the terminal non-blocking
        fcntl.fcntl(master_fd, fcntl.F_SETFL, os.O_NONBLOCK)

        # Start the MCP server process if it's not already running
        if not is_mcp_server_running():
            # Path to Python interpreter
            python_executable = sys.executable

            # Path to the MCP server module
            mcp_server_module = "erpnext_mcp_server.mcp_ag2_example.server.server"

            # Start the MCP server process using Python to run the module
            process = subprocess.Popen(
                [python_executable, "-m", mcp_server_module],
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                shell=False,
                preexec_fn=os.setsid,
            )

            # Store the session information
            active_sessions[session_id] = {
                "master_fd": master_fd,
                "slave_fd": slave_fd,
                "process": process,
                "user": frappe.session.user,
                "created_at": now_datetime(),
                "last_active": now_datetime(),
            }

            # Log the session creation
            log_terminal_session(session_id, "Connect")

            return {
                "success": True,
                "session_id": session_id,
                "message": "Terminal session created successfully",
            }
        else:
            # Connect to existing MCP server
            # This would require your MCP server to support attaching to existing instances
            # Implement according to your MCP server's specific requirements
            frappe.throw(
                _(
                    "MCP Server is already running. Attaching to existing instance not implemented."
                )
            )
    except Exception as e:
        frappe.log_error(
            f"Error creating terminal session: {str(e)}", "Terminal Session Error"
        )
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def execute_command():
    """Execute a command in the terminal session"""
    from frappe import _

    try:
        # Check permissions
        if not frappe.has_permission("MCP Terminal", "write"):
            frappe.throw(
                _("You don't have permission to execute commands"),
                frappe.PermissionError,
            )

        # Get parameters
        session_id = frappe.local.form_dict.get("session_id")
        command = frappe.local.form_dict.get("command")

        if not session_id or not command:
            frappe.throw(_("Session ID and command are required"))

        # Check if session exists
        if session_id not in active_sessions:
            frappe.throw(_("Terminal session not found or expired"))

        session = active_sessions[session_id]

        # Check if the session belongs to the current user
        if session["user"] != frappe.session.user:
            frappe.throw(_("You don't have permission to access this terminal session"))

        # Update the last active timestamp
        session["last_active"] = now_datetime()

        # Write the command to the terminal
        os.write(session["master_fd"], command.encode())

        # Log the command
        log_terminal_command(session_id, command)

        # Wait for a short time to allow the command to execute
        time.sleep(0.1)

        # Read the output (non-blocking)
        output = ""
        try:
            ready, _, _ = select.select([session["master_fd"]], [], [], 0.5)
            if ready:
                output = os.read(session["master_fd"], 65536).decode(
                    "utf-8", errors="replace"
                )
        except Exception as e:
            frappe.log_error(
                f"Error reading from terminal: {str(e)}", "Terminal Read Error"
            )

        return {"success": True, "output": output}
    except Exception as e:
        frappe.log_error(f"Error executing command: {str(e)}", "Terminal Command Error")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def resize_terminal(session_id, rows, cols):
    """Resize the terminal"""
    try:
        # Check permissions
        if not frappe.has_permission("MCP Terminal", "write"):
            frappe.throw(
                _("You don't have permission to resize the terminal"),
                frappe.PermissionError,
            )

        # Get parameters
        session_id = frappe.local.form_dict.get("session_id")
        rows = cint(frappe.local.form_dict.get("rows") or 24)
        cols = cint(frappe.local.form_dict.get("cols") or 80)

        if not session_id:
            frappe.throw(_("Session ID is required"))

        # Check if session exists
        if session_id not in active_sessions:
            frappe.throw(_("Terminal session not found or expired"))

        session = active_sessions[session_id]

        # Check if the session belongs to the current user
        if session["user"] != frappe.session.user:
            frappe.throw(_("You don't have permission to access this terminal session"))

        # Resize the terminal
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(session["master_fd"], termios.TIOCSWINSZ, winsize)

        return {"success": True, "message": "Terminal resized successfully"}
    except Exception as e:
        frappe.log_error(f"Error resizing terminal: {str(e)}", "Terminal Resize Error")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def close_terminal_session():
    """Close a terminal session"""
    try:
        # Check permissions
        if not frappe.has_permission("MCP Terminal", "write"):
            frappe.throw(
                _("You don't have permission to close terminal sessions"),
                frappe.PermissionError,
            )

        # Get session ID
        session_id = frappe.local.form_dict.get("session_id")

        if not session_id:
            frappe.throw(_("Session ID is required"))

        # Check if session exists
        if session_id not in active_sessions:
            return {"success": True, "message": "Session already closed"}

        session = active_sessions[session_id]

        # Check if the session belongs to the current user
        if session["user"] != frappe.session.user and not frappe.has_permission(
            "MCP Terminal", "admin"
        ):
            frappe.throw(_("You don't have permission to close this terminal session"))

        # Kill the process
        try:
            if session.get("process"):
                os.killpg(os.getpgid(session["process"].pid), signal.SIGTERM)
        except ProcessLookupError:
            # Process already terminated
            pass
        except Exception as e:
            frappe.log_error(
                f"Error terminating process: {str(e)}", "Terminal Session Error"
            )

        # Close file descriptors
        try:
            os.close(session["master_fd"])
        except OSError:
            pass

        try:
            os.close(session["slave_fd"])
        except OSError:
            pass

        # Remove from active sessions
        del active_sessions[session_id]

        # Log the session closure
        log_terminal_session(session_id, "close")

        return {"success": True, "message": "Terminal session closed successfully"}
    except Exception as e:
        frappe.log_error(
            f"Error closing terminal session: {str(e)}", "Terminal Session Error"
        )
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def log_terminal_session(session_id, action):
    """Log terminal session events"""
    try:
        # Make sure action is one of the valid options
        valid_actions = ["Connect", "Disconnect", "Command", "Token Request", "Error"]
        action = action if action in valid_actions else "Connect"

        log = frappe.new_doc("MCP Terminal Log")
        log.user = frappe.session.user  # type: ignore
        log.timestamp = now_datetime()  # type: ignore
        log.session_id = session_id  # type: ignore
        log.action = action  # type: ignore
        log.command_type = "Shell"  # type: ignore
        log.details = f"Terminal session {action}"  # type: ignore
        log.insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(
            f"Failed to log terminal session: {str(e)}", "Terminal Log Error"
        )


def log_terminal_command(session_id, command):
    """Log terminal commands for auditing"""
    try:
        # Don't log sensitive commands like passwords
        if any(
            sensitive in command.lower()
            for sensitive in ["password", "secret", "token", "key"]
        ):
            sanitized_command = "[REDACTED SENSITIVE COMMAND]"
        else:
            sanitized_command = command

        log = frappe.new_doc("MCP Terminal Log")
        log.user = frappe.session.user  # type: ignore
        log.timestamp = now_datetime()  # type: ignore
        log.session_id = session_id  # type: ignore
        log.action = "Command"  # type: ignore
        log.command_type = "Shell"  # type: ignore

        # Limit length to avoid huge logs
        log.details = sanitized_command[:1000]  # type: ignore
        log.insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(
            f"Failed to log terminal command: {str(e)}", "Terminal Log Error"
        )


@frappe.whitelist()
def check_terminal_session(session_id=None):
    """Check if a terminal session is valid"""
    try:
        # Check permissions
        if not frappe.has_permission("MCP Terminal", "read"):
            frappe.throw(
                _("You don't have permission to access terminal sessions"),
                frappe.PermissionError,
            )

        if not session_id:
            return {"success": False, "message": "Session ID is required"}

        # Check if session exists
        if session_id not in active_sessions:
            return {
                "success": False,
                "message": "Terminal session not found or expired",
            }

        session = active_sessions[session_id]

        # Check if the session belongs to the current user
        if session["user"] != frappe.session.user and not frappe.has_permission(
            "MCP Terminal", "admin"
        ):
            return {
                "success": False,
                "message": "You don't have permission to access this terminal session",
            }

        # Check if the process is still running
        if session.get("process") and session["process"].poll() is not None:
            # Process has terminated
            return {"success": False, "message": "Terminal process has terminated"}

        return {
            "success": True,
            "message": "Terminal session is valid",
            "created_at": session["created_at"],
            "last_active": session["last_active"],
        }
    except Exception as e:
        frappe.log_error(
            f"Error checking terminal session: {str(e)}", "Terminal Session Error"
        )
        return {"success": False, "error": str(e)}


# Scheduled task to clean up expired sessions
def cleanup_terminal_sessions():
    """Clean up expired terminal sessions"""
    try:
        current_time = now_datetime()
        sessions_to_remove = []

        for session_id, session in active_sessions.items():
            # Check if the session has been inactive for more than 30 minutes
            last_active = session["last_active"]
            if time_diff_in_seconds(current_time, last_active) > 1800:  # 30 minutes
                sessions_to_remove.append(session_id)

        # Close expired sessions
        for session_id in sessions_to_remove:
            try:
                session = active_sessions[session_id]

                # Kill the process
                try:
                    if session.get("process"):
                        os.killpg(os.getpgid(session["process"].pid), signal.SIGTERM)
                except ProcessLookupError:
                    # Process already terminated
                    pass
                except Exception as e:
                    frappe.log_error(
                        f"Error terminating process: {str(e)}",
                        "Terminal Session Cleanup Error",
                    )

                # Close file descriptors
                try:
                    os.close(session["master_fd"])
                except OSError:
                    pass

                try:
                    os.close(session["slave_fd"])
                except OSError:
                    pass

                # Remove from active sessions
                del active_sessions[session_id]

                # Log the session cleanup
                log_terminal_session(session_id, "cleanup")
            except Exception as e:
                frappe.log_error(
                    f"Error cleaning up session {session_id}: {str(e)}",
                    "Terminal Session Cleanup Error",
                )
    except Exception as e:
        frappe.log_error(
            f"Error in terminal session cleanup: {str(e)}",
            "Terminal Session Cleanup Error",
        )

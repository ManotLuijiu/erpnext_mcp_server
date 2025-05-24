"""Terminal API for MCP integration."""

import json
import os
import queue
import subprocess
import threading
import time
from typing import Any, Dict, Optional

import frappe
from frappe.utils import now_datetime

# Store active MCP processes
active_processes = {}


@frappe.whitelist()
def start_mcp_session():
    """Start a new MCP session."""
    try:
        session_id = frappe.generate_hash(length=10)

        # Get the path to MCP server script
        app_path = frappe.get_app_path("erpnext_mcp_server")
        mcp_script = os.path.join(app_path, "mcp_server.py")

        # Get site name from frappe.local
        site_name = frappe.local.site

        # Get Python executable path
        import sys

        python_executable = sys.executable

        # Start MCP Server process with site context
        env = os.environ.copy()
        env["FRAPPE_SITE"] = site_name

        process = subprocess.Popen(
            [python_executable, mcp_script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            cwd=frappe.get_site_path(".."),
        )

        # Create communication queues
        request_queue = queue.Queue()
        response_queue = queue.Queue()

        # Start communication threads
        stdin_thread = threading.Thread(
            target=stdin_worker, args=(process, request_queue, session_id)
        )
        stdout_thread = threading.Thread(
            target=stdout_worker, args=(process, response_queue, session_id)
        )

        stdin_thread.daemon = True
        stdout_thread.daemon = True
        stdin_thread.start()
        stdout_thread.start()

        # Store process info
        active_processes[session_id] = {
            "process": process,
            "request_queue": request_queue,
            "response_queue": response_queue,
            "stdin_thread": stdin_thread,
            "stdout_thread": stdout_thread,
            "user": frappe.session.user,
            "started": now_datetime(),
            "last_used": now_datetime(),
        }

        # Send initialization request
        init_request = {
            "jsonrpc": "2.0",
            "id": "init",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "ERPNext Terminal", "version": "1.0.0"},
            },
        }

        request_queue.put(init_request)

        # Wait for initialization response
        try:
            response = response_queue.get(timeout=10)
            if "error" in response:
                raise Exception(f"MCP initialization failed: {response['error']}")
        except queue.Empty:
            raise Exception("MCP server initialization timeout")

        # Publish session started event
        frappe.publish_realtime(
            event="mcp_session_started",
            message={"session_id": session_id},
            user=frappe.session.user,
        )

        return {"success": True, "session_id": session_id}

    except Exception as e:
        frappe.log_error(f"Failed to start MCP session: {e}")
        return {"success": False, "error": str(e)}


def stdin_worker(process, request_queue, session_id):
    """Worker thread for handling stdin communication."""
    try:
        while True:
            if session_id not in active_processes:
                break

            try:
                request = request_queue.get(timeout=1)
                if request is None:  # Signal signal
                    break

                json_str = json.dumps(request) + "\n"
                process.stdin.write(json_str)
                process.stdin.flush()

            except queue.Empty:
                continue
            except Exception as e:
                frappe.log_error(f"stdin_worker error: {e}")
                break

    except Exception as e:
        frappe.log_error(f"stdin_worker fatal error: {e}")


def stdout_worker(process, response_queue, session_id):
    """Worker thread for handling stdout communication."""
    try:
        while True:
            if session_id not in active_processes:
                break
            if process.poll() is not None:
                break
            try:
                line = process.stdout.readline()
                if not line:
                    break
                response = json.loads(line.strip())
                response_queue.put(response)
            except json.JSONDecodeError:
                continue
            except Exception as e:
                frappe.log_error(f"stdout_worker error: {e}")
                break

    except Exception as e:
        frappe.log_error(f"stdout_worker fatal error: {e}")


@frappe.whitelist()
def execute_mcp_command(
    session_id: str, command: str, args: Optional[Dict[str, Any]] = None
):
    """Execute MCP command."""
    try:
        if session_id not in active_processes:
            return {"success": False, "error": "Session not found"}

        process_info = active_processes[session_id]
        process = process_info["process"]

        # Check if process is alive
        if process.poll() is not None:
            cleanup_session(session_id)
            return {"success": False, "error": "Session terminated"}

        # Update last used time
        process_info["last_used"] = now_datetime()

        # Build MCP request
        request_id = frappe.generate_hash(length=8)

        if command == "list_tools":
            mcp_request = {"jsonrpc": "2.0", "id": request_id, "method": "tools/list"}
        else:
            mcp_request = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "tools/call",
                "params": {"name": command, "arguments": args or {}},
            }

        # Send request
        process_info["request_queue"].put(mcp_request)

        # Wait for response
        try:
            response = process_info["response_queue"].get(timeout=30)
        except queue.Empty:
            return {"success": False, "error": "Command timed out"}

        # Process response
        if "error" in response:
            result = {
                "success": False,
                "error": response["error"].get("message", "Unknown error"),
                "timestamp": now_datetime(),
            }
        else:
            result_data = response.get("result", {})

            if "content" in result_data:
                # Extract text from content array
                text_content = ""
                for content in result_data["context"]:
                    if content.get("type") == "text":
                        text_content += content.get("text", "")

                result = {
                    "success": not result_data.get("isError", False),
                    "data": text_content,
                    "timestamp": now_datetime(),
                }

                if result_data.get("isError"):
                    result["error"] = text_content
            else:
                # Handle tools/list response
                result = {
                    "success": True,
                    "data": json.dumps(result_data, indent=2),
                    "timestamp": now_datetime(),
                }

        # Publish result
        frappe.publish_realtime(
            event="mcp_command_result", message=result, user=frappe.session.user
        )

        return result

    except Exception as e:
        frappe.log_error(f"MCP command execution failed: {e}")
        error_result = {"success": False, "error": str(e), "timestamp": now_datetime()}

        frappe.publish_realtime(
            event="mcp_command_result", message=error_result, user=frappe.session.user
        )

        return error_result


@frappe.whitelist()
def end_mcp_session(session_id: str):
    """End MCP session."""
    try:
        cleanup_session(session_id)

        frappe.publish_realtime(
            event="mcp_session_ended",
            message={"session_id": session_id},
            user=frappe.session.user,
        )

        return {"success": True}

    except Exception as e:
        return {"success": False, "error": str(e)}


def cleanup_session(session_id: str):
    """Clean up session resources."""
    if session_id in active_processes:
        process_info = active_processes[session_id]

        # Stop threads
        try:
            process_info["request_queue"].put(None)  # Shutdown signal
        except Exception:
            pass

        # Terminate process
        try:
            process = process_info["process"]
            process.terminate()
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        except Exception:
            pass

        # Remove from active processes
        del active_processes[session_id]


@frappe.whitelist()
def get_active_sessions():
    """Get active sessions for current user."""
    try:
        user_sessions = []

        for session_id, info in active_processes.items():
            if info["user"] == frappe.session.user:
                user_sessions.append(
                    {
                        "session_id": session_id,
                        "started": info["started"],
                        "last_used": info["last_used"],
                        "is_alive": info["process"].poll() is None,
                    }
                )

        return {"success": True, "sessions": user_sessions}

    except Exception as e:
        return {"success": False, "error": str(e)}


def cleanup_inactive_sessions():
    """Background job to cleanup inactive session."""
    try:
        current_time = time.time()
        inactive_sessions = []

        for session_id, info in active_processes.items():
            # Check if dead or inactive for > 1 hour
            last_used = time.mktime(info["last_used"].timetuple())
            is_dead = info["process"].poll() is not None
            is_inactive = (current_time - last_used) > 3600

            if is_dead or is_inactive:
                inactive_sessions.append(session_id)

        # Clean up
        for session_id in inactive_sessions:
            cleanup_session(session_id)

        if inactive_sessions:
            frappe.logger().info(
                f"Cleaned up {len(inactive_sessions)} inactive MCP sessions"
            )

    except Exception as e:
        frappe.log_error(f"Session cleanup failed: {e}")

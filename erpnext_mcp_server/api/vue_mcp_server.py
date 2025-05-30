"""
Vue MCP Server API
Frappe API methods for terminal communication with MCP server
"""

import asyncio
import json
import os
import signal
import subprocess
import threading
import time
from typing import Any, Dict, Optional

import frappe
from frappe import _


class MCPProcessManager:
    """Managers MCP server processes for terminal sessions."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(MCPProcessManager, cls).__new__(cls)
                    cls._instance.processes = {}
                    cls._instance.initialized = False
        return cls._instance

    def __init__(self) -> None:
        if not self.initialized:
            self.processes: Dict[str, subprocess.Popen] = {}
            self.initialized = True

    def get_session_key(self) -> str:
        """Get unique session key for current user/site."""
        return f"{frappe.session.user}@{frappe.local.site}"

    def start_mcp_server(self) -> bool:
        """Start MCP server process for current session."""
        session_key = self.get_session_key()

        if session_key in self.processes:
            # Check if process is still alive
            proc = self.processes[session_key]
            if proc.poll() is None:
                return True  # Already running
            else:
                # Process died, remove it
                del self.processes[session_key]

        try:
            # Path to MCP server script
            server_script = os.path.join(
                frappe.get_app_path("erpnext_mcp_server"), "mcp", "server.py"
            )

            if not os.path.exists(server_script):
                frappe.publish_realtime(
                    "terminal_output",
                    {
                        "type": "error",
                        "data": f"MCP server script not found: {server_script}",
                    },
                    user=frappe.session.user,
                )
                return False

            # Start MCP server process
            env = os.environ.copy()
            env["FRAPPE_SITE"] = frappe.local.site

            proc = subprocess.Popen(
                ["python", server_script],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                cwd=frappe.get_site_path(),
            )

            self.processes[session_key] = proc

            frappe.publish_realtime(
                "mcp_status",
                {"status": "connected", "session": session_key},
                user=frappe.session.user,
            )

            return True

        except Exception as e:
            frappe.publish_realtime(
                "terminal_output",
                {"type": "error", "data": f"Failed to start MCP server: {str(e)}"},
                user=frappe.session.user,
            )
            return False

    def send_command(self, command: str) -> bool:
        """Send command to MCP server process."""
        session_key = self.get_session_key()

        if session_key not in self.processes:
            if not self.start_mcp_server():
                return False

        proc = self.processes[session_key]

        try:
            # Check f process is alive
            if proc.poll() is not None:
                # Process died, restart
                del self.processes[session_key]
                if not self.start_mcp_server():
                    return False
                proc = self.processes[session_key]

            # Format command as JSON-RPC request
            request = {
                "jsonrpc": "2.0",
                "id": int(time.time() * 1000),
                "method": "tools/call",
                "params": self._parse_command(command),
            }

            # Send command
            proc.stdin.write(json.dumps(request) + "\n")  # type: ignore
            proc.stdin.flush()  # type: ignore

            # Start background thread to read response
            threading.Thread(
                target=self._read_response, args=(proc, session_key), daemon=True
            ).start()

            return True

        except Exception as e:
            frappe.publish_realtime(
                "terminal_output",
                {"type": "error", "data": f"Failed to send command: {str(e)}"},
                user=frappe.session.user,
            )
            return False

    def _parse_command(self, command: str) -> Dict[str, Any]:
        """Parse terminal command into MCP tool call."""
        parts = command.strip().split()
        if not parts:
            return {"name": "get_system_info", "arguments": {}}

        tool_name = parts[0]
        args = parts[1:]

        # Map common commands to MCP tools
        if tool_name == "help":
            return {"name": "get_system_info", "arguments": {}}
        elif tool_name == "list_doctypes":
            return {
                "name": "list_doctypes",
                "arguments": {"module": args[0] if args else None},
            }
        elif tool_name == "get_document":
            if len(args) >= 2:
                return {
                    "name": "get_document",
                    "arguments": {"doctype": args[0], "name": args[1]},
                }
        elif tool_name == "search_documents":
            if len(args) >= 2:
                arguments = {"doctype": args[0], "query": args[1]}
                # Parse additional flags like --limit
                for i, arg in enumerate(args[2:], 2):
                    if arg == "--limit" and i + 1 < len(args):
                        arguments["limit"] = int(args[i + 1])  # type: ignore
                return {"name": "search_documents", "arguments": arguments}
        elif tool_name == "execute_sql":
            if args:
                return {"name": "execute_sql", "arguments": {"query": " ".join(args)}}
        elif tool_name == "get_system_info":
            return {"name": "get_system_info", "arguments": {}}
        elif tool_name == "bench_command":
            return {
                "name": "bench_command",
                "arguments": {
                    "command": args[0] if args else "status",
                    "args": args[1:],
                },
            }
        elif tool_name == "list_files":
            arguments = {"path": args[0] if args else "."}
            if "--recursive" in args:
                arguments["recursive"] = True  # type: ignore
            return {"name": "list_files", "arguments": arguments}
        elif tool_name == "read_file":
            if args:
                arguments = {"path": args[0]}
                if "--lines" in args:
                    try:
                        lines_idx = args.index("--lines")
                        if lines_idx + 1 < len(args):
                            arguments["lines"] = int(args[lines_idx + 1])  # type: ignore
                    except (ValueError, IndexError):
                        pass
                return {"name": "read_file", "arguments": arguments}

        # Default: treat as system info
        return {"name": "get_system_info", "arguments": {}}

    def _read_response(self, proc: subprocess.Popen, session_key: str):
        """Read response from MCP server in background thread."""
        try:
            while proc.poll() is None:
                line = proc.stdout.readline()  # type: ignore
                if not line:
                    break

                try:
                    response = json.loads(line.strip())

                    if "result" in response:
                        # Success response
                        frappe.publish_realtime(
                            "terminal_output",
                            {"type": "stdout", "data": response["result"]},
                            user=frappe.session.user,
                        )
                    elif "error" in response:
                        # Error response
                        frappe.publish_realtime(
                            "terminal_output",
                            {"type": "stderr", "data": response["error"]["message"]},
                            user=frappe.session.user,
                        )

                except json.JSONDecodeError:
                    # Non-JSON output, send as-is
                    frappe.publish_realtime(
                        "terminal_output",
                        {"type": "stdout", "data": line.strip()},
                        user=frappe.session.user,
                    )

        except Exception as e:
            frappe.publish_realtime(
                "terminal_output",
                {"type": "error", "data": f"Error reading response: {str(e)}"},
                user=frappe.session.user,
            )
        finally:
            # Clean up process
            if session_key in self.processes:
                del self.processes[session_key]

            frappe.publish_realtime(
                "mcp_status", {"status": "disconnected"}, user=frappe.session.user
            )

    def stop_server(self, session_key: Optional[str] = None):
        """Stop MCP server process."""
        if session_key is None:
            session_key = self.get_session_key()
        if session_key in self.processes:
            proc = self.processes[session_key]
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            finally:
                del self.processes[session_key]

    def cleanup_all(self):
        """Clean up all MCP server processes."""
        for session_key in list(self.processes.keys()):
            self.stop_server(session_key)


# Global process manager instance
mcp_manager = MCPProcessManager()


@frappe.whitelist()
def execute_terminal_command(command: str):
    """Execute terminal command and send realtime updates"""
    try:
        # Validate user permissions
        if not frappe.has_permission("System Settings", "read"):
            frappe.throw(_("Insufficient permissions to execute terminal commands"))
        # Security check - only allow certain commands
        # allowed_commands = [
        #     "pwd",
        #     "ls",
        #     "whoami",
        #     "get_document",
        #     "search_documents",
        #     "execute_sql",
        #     "list_files",
        #     "bench_command",
        #     "list_doctypes",
        # ]
        # base_command = command.split()[0] if command else ""

        # if base_command not in allowed_commands:
        #     frappe.publish_realtime(
        #         event="terminal_output",
        #         message={
        #             "type": "error",
        #             "data": f"Command not allowed: {base_command}",
        #         },
        #         user=frappe.session.user,
        #     )
        #     frappe.msgprint(f"Command {base_command} not allowed")
        #     return {"success": False, "error": "Command not allowed"}

        # Echo the command
        # Publish initial response
        # frappe.publish_realtime(
        #     event="terminal_output",
        #     message={"type": "output", "data": f"Executing: {command}"},
        #     user=frappe.session.user,
        # )

        # Send command acknowledgment
        frappe.publish_realtime(
            "terminal_output",
            {"type": "command", "data": command},
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
        # if process.stdout is not None:
        #     for line in process.stdout:
        #         frappe.publish_realtime(
        #             event="terminal_output",
        #             message={"type": "output", "data": line},
        #             user=frappe.session.user,
        #         )

        # Wait for process to complete
        # process.wait()

        # Collect all output first (like terminal buffers)
        stdout, stderr = process.communicate()

        # Send complete output at once
        if stdout:
            cleaned_stdout = stdout.rstrip() + "\n"  # Ensure exactly one newline
            frappe.publish_realtime(
                event="terminal_output",
                # message={"type": "stdout", "data": stdout},
                message={"type": "stdout", "data": cleaned_stdout},
                user=frappe.session.user,
            )

        if stderr:
            cleaned_stderr = stderr.rstrip() + "\n"  # Ensure exactly one newline
            frappe.publish_realtime(
                event="terminal_output",
                # message={"type": "stderr", "data": stderr},
                message={"type": "stderr", "data": cleaned_stderr},
                user=frappe.session.user,
            )

        # Show prompt again
        # frappe.publish_realtime(
        #     event="terminal_output",
        #     message={"type": "prompt", "data": ""},
        #     user=frappe.session.user,
        # )

        # Send command to MCP server
        success = mcp_manager.send_command(command)

        if success:
            return {"success": True, "message": "Command sent to MCP server"}
        else:
            return {"success": False, "message": "Failed to send command"}

        # return {"success": True}

    except Exception as e:
        # error_msg = f"Error: {str(e)}\n"
        frappe.log_error(f"Terminal command error: {str(e)}")
        # frappe.publish_realtime(
        #     event="terminal_output",
        #     # message={"type": "error", "data": f"Error: {str(e)}\n"},
        #     message={"type": "stderr", "data": error_msg},
        #     user=frappe.session.user,
        # )
        # return {"success": False, "error": str(e)}
        frappe.publish_realtime(
            "terminal_output",
            {"type": "error", "data": str(e)},
            user=frappe.session.user,
        )
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def get_terminal_status():
    """Get current terminal/MCP server status."""
    try:
        session_key = mcp_manager.get_session_key()
        is_running = session_key in mcp_manager.processes

        if is_running:
            proc = mcp_manager.processes[session_key]
            is_alive = proc.poll() is None
            if not is_alive:
                del mcp_manager.processes[session_key]
                is_running = False

        return {
            "success": True,
            "status": "connected" if is_running else "disconnected",
            "session": session_key,
            "user": frappe.session.user,
            "site": frappe.local.site,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def start_mcp_server():
    """Manually start MCP server."""
    try:
        success = mcp_manager.start_mcp_server()
        return {"success": success}
    except Exception as e:
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def stop_mcp_server():
    """Manually stop MCP server."""
    try:
        mcp_manager.stop_server()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


# Cleanup on site shutdown
def cleanup_mcp_processes():
    """Clean up MCP processes on site shutdown."""
    try:
        mcp_manager.cleanup_all()
    except Exception:
        pass


# Register cleanup function
frappe.local.after_request = cleanup_mcp_processes

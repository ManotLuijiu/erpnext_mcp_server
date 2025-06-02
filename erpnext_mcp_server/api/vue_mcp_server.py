"""
Vue MCP Server API with Configuration Integration
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

from ..mcp.config import mcp_config, setup_mcp_server, validate_mcp_environment


class MCPProcessManager:
    """
    Managers MCP server processes for terminal sessions with fixed threading.
    """

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
            self.config = mcp_config  # Use global config
            self.initialized = True

    def get_session_key(self) -> str:
        """Get unique session key for current user/site."""
        return f"{frappe.session.user}@{frappe.local.site}"

    def start_mcp_server(self) -> bool:
        """Start MCP server process for current session using configuration."""
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
            # Validate environment first
            validate_mcp_environment()

            # Get server script path from config
            server_script = self.config.get_server_path()
            print(f"server_path {self.config.get_server_path()}")

            # Path to MCP server script
            # server_script = os.path.join(
            #     frappe.get_app_path("erpnext_mcp_server"), "mcp", "server.py"
            # )

            if not server_script.exists():
                frappe.publish_realtime(
                    "terminal_output",
                    {
                        "type": "error",
                        "data": f"MCP server script not found: {server_script}",
                    },
                    user=frappe.session.user,
                )
                return False

            # if not os.path.exists(server_script):
            #     frappe.publish_realtime(
            #         "terminal_output",
            #         {
            #             "type": "error",
            #             "data": f"MCP server script not found: {server_script}",
            #         },
            #         user=frappe.session.user,
            #     )
            #     return False

            # Start MCP server process
            # env = os.environ.copy()
            # env["FRAPPE_SITE"] = frappe.local.site

            # Use config environment variables
            env = self.config.get_environment_variables()

            # Start MCP server process
            proc = subprocess.Popen(
                ["python", str(server_script)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                cwd=frappe.get_site_path(),
            )

            # proc = subprocess.Popen(
            #     ["python", server_script],
            #     stdin=subprocess.PIPE,
            #     stdout=subprocess.PIPE,
            #     stderr=subprocess.PIPE,
            #     text=True,
            #     env=env,
            #     cwd=frappe.get_site_path(),
            # )

            self.processes[session_key] = proc

            # frappe.publish_realtime(
            #     "mcp_status",
            #     {"status": "connected", "session": session_key},
            #     user=frappe.session.user,
            # )

            frappe.publish_realtime(
                "mcp_status",
                {
                    "status": "connected",
                    "session": session_key,
                    "server_version": self.config.server_version,
                    "debug_mode": self.config.is_development_mode(),
                },
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

        user = frappe.session.user
        print(f"user vue_mcp_server.py {user}")

        site = (
            frappe.local.site
            if hasattr(frappe.local, "site")
            else os.environ.get("FRAPPE_SITE")
        )
        print(f"site {site}")

        if session_key not in self.processes:
            if not self.start_mcp_server():
                return False

        proc = self.processes[session_key]

        try:
            # Check if process is alive
            if proc.poll() is not None:
                # Process died, restart
                del self.processes[session_key]
                if not self.start_mcp_server():
                    return False
                proc = self.processes[session_key]

            # Parse and validate command using config
            parsed_command = self._parse_command(command)
            if not parsed_command:
                frappe.publish_realtime(
                    "terminal_output",
                    {"type": "error", "data": f"Invalid command: {command}"},
                    user=frappe.session.user,
                )
                return False

            # Format command as JSON-RPC request
            request = {
                "jsonrpc": "2.0",
                "id": int(time.time() * 1000),
                "method": "tools/call",
                "params": parsed_command,
            }

            # Send command
            proc.stdin.write(json.dumps(request) + "\n")  # type: ignore
            proc.stdin.flush()  # type: ignore

            # Start background thread to read response
            threading.Thread(
                target=self._read_response,
                args=(proc, session_key, user, site),
                daemon=True,
            ).start()

            return True

        except Exception as e:
            frappe.publish_realtime(
                "terminal_output",
                {"type": "error", "data": f"Failed to send command: {str(e)}"},
                user=frappe.session.user,
            )
            return False

    def _parse_command(self, command: str) -> Optional[Dict[str, Any]]:
        """Parse terminal command into MCP tool call with config validation."""
        parts = command.strip().split()
        if not parts:
            return {"name": "get_system_info", "arguments": {}}

        tool_name = parts[0]
        args = parts[1:]

        # Map common commands to MCP tools with config-aware validation
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
                # Parse additional flags like --limit with config validation
                for i, arg in enumerate(args[2:], 2):
                    if arg == "--limit" and i + 1 < len(args):
                        try:
                            limit = int(args[i + 1])
                            # Enforce config limit
                            arguments["limit"] = min(limit, self.config.sql_query_limit)  # type: ignore
                        except ValueError:
                            pass
                        arguments["limit"] = int(args[i + 1])  # type: ignore
                return {"name": "search_documents", "arguments": arguments}

        elif tool_name == "execute_sql":
            if args:
                query = " ".join(args)
                # Basic validation - detailed validation happens in DatabaseTools
                if any(
                    keyword in query.upper()
                    for keyword in ["INSERT", "UPDATE", "DELETE", "DROP"]
                ):
                    return None  # Invalid query
                return {
                    "name": "execute_sql",
                    "arguments": {"query": query, "limit": self.config.sql_query_limit},
                }

        elif tool_name == "get_system_info":
            return {"name": "get_system_info", "arguments": {}}

        elif tool_name == "bench_command":
            if args and args[0] in self.config.allowed_bench_commands:
                return {
                    "name": "bench_command",
                    "arguments": {"command": args[0], "args": args[1:]},
                }
            return None  # Invalid bench command

        elif tool_name == "list_files":
            if args:
                arguments = {"path": args[0]}
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

    def _read_response(
        self, proc: subprocess.Popen, session_key: str, user: str, site: str
    ):
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
                            # user=frappe.session.user,
                            user=user,
                            # site=site,
                        )
                    elif "error" in response:
                        # Error response
                        error_data = response["error"]["message"]
                        if self.config.is_development_mode():
                            # Include more debug info in development
                            error_data += (
                                f"\n\nDebug: {json.dumps(response['error'], indent=2)}"
                            )

                        frappe.publish_realtime(
                            "terminal_output",
                            {"type": "stderr", "data": error_data},
                            # user=frappe.session.user,
                            user=user,
                        )

                except json.JSONDecodeError:
                    # Non-JSON output, send as-is
                    frappe.publish_realtime(
                        "terminal_output",
                        {"type": "stdout", "data": line.strip()},
                        # user=frappe.session.user,
                        user=user,
                    )

        except Exception as e:
            frappe.publish_realtime(
                "terminal_output",
                {"type": "error", "data": f"Error reading response: {str(e)}"},
                # user=frappe.session.user,
                user=user,
            )
        finally:
            # Clean up process
            if session_key in self.processes:
                del self.processes[session_key]

            frappe.publish_realtime(
                "mcp_status",
                {"status": "disconnected"},
                # user=frappe.session.user
                user=user,
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
def execute_terminal_command(command: str, user: str):
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

        # Validate environment
        validate_mcp_environment()

        # Send command acknowledgment
        frappe.publish_realtime(
            "terminal_output",
            {"type": "command", "data": command},
            # user=frappe.session.user,
            user=user,
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
                # user=frappe.session.user,
                user=user,
            )

        if stderr:
            cleaned_stderr = stderr.rstrip() + "\n"  # Ensure exactly one newline
            frappe.publish_realtime(
                event="terminal_output",
                # message={"type": "stderr", "data": stderr},
                message={"type": "stderr", "data": cleaned_stderr},
                # user=frappe.session.user,
                user=user,
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
            # user=frappe.session.user,
            user=user,
        )
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def get_terminal_status():
    """Get current terminal/MCP server status with configuration info."""
    user = frappe.session.user
    site = (
        frappe.local.site
        if hasattr(frappe.local, "site")
        else os.environ.get("FRAPPE_SITE")
    )
    try:
        session_key = mcp_manager.get_session_key()
        is_running = session_key in mcp_manager.processes

        print(f"session_key {session_key}")
        print(f"is_running {is_running}")

        if is_running:
            proc = mcp_manager.processes[session_key]
            print(f"proc {proc}")

            is_alive = proc.poll() is None
            print(f"is_alive {is_alive}")

            if not is_alive:
                del mcp_manager.processes[session_key]
                is_running = False

        return {
            "success": True,
            "status": "connected" if is_running else "disconnected",
            "session": session_key,
            "user": user,
            "site": site,
            "server_version": mcp_config.server_version,
            "debug_mode": mcp_config.is_development_mode(),
            "config": {
                "max_file_size_mb": mcp_config.max_file_size // (1024 * 1024),
                "sql_query_limit": mcp_config.sql_query_limit,
                "command_timeout": mcp_config.command_timeout,
                "allowed_extensions": list(mcp_config.allowed_file_extensions),
                "safe_directories": mcp_config.safe_directories,
                "allowed_bench_commands": list(
                    mcp_config.allowed_bench_commands.keys()
                ),
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def start_mcp_server():
    """Manually start MCP server with config validation."""
    try:
        validate_mcp_environment()
        success = mcp_manager.start_mcp_server()
        print(f"success {success}")

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


@frappe.whitelist()
def get_mcp_config():
    """Get MCP configuration for terminal display."""
    try:
        return {
            "success": True,
            "config": {
                "server_name": mcp_config.server_name,
                "server_version": mcp_config.server_version,
                "max_file_size_mb": mcp_config.max_file_size // (1024 * 1024),
                "sql_query_limit": mcp_config.sql_query_limit,
                "command_timeout": mcp_config.command_timeout,
                "allowed_file_extensions": sorted(
                    list(mcp_config.allowed_file_extensions)
                ),
                "safe_directories": mcp_config.safe_directories,
                "allowed_bench_commands": mcp_config.allowed_bench_commands,
                "development_mode": mcp_config.is_development_mode(),
            },
        }
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

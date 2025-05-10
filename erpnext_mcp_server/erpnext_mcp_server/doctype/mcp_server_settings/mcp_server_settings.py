import os
import sys
import subprocess
import json
import logging
import time
import signal
import threading
from datetime import datetime
from pathlib import Path

import frappe
from frappe.model.document import Document
from frappe.utils import get_site_path, get_site_config
from frappe.utils.background_jobs import enqueue

logger = logging.getLogger(__name__)


class MCPServerSettings(Document):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._process = None
        self._output_thread = None
        self._should_stop = False

    def before_validate(self):
        """Validate settings before saving"""
        self.validate_server_path()
        self.validate_transport()

    def validate_server_path(self):
        """Ensure the server path exists"""
        if self.server_path:
            path = Path(self.server_path)
            if not path.exists():
                frappe.throw(f"Server path does not exist: {self.server_path}")
            if not path.suffix == ".py":
                frappe.throw("Server path must be a Python file (.py)")

    def validate_transport(self):
        """Validate transport settings"""
        valid_transports = ["stdio", "sse"]
        if self.transport not in valid_transports:
            frappe.throw(
                f"Invalid transport. Must be one of: {', '.join(valid_transports)}"
            )

    def after_insert(self):
        """Initialize settings after first save"""
        self.init_default_settings()

    def init_default_settings(self):
        """Set default values for settings"""
        if not self.server_path:
            # Try to find server.py in the app directory
            app_path = frappe.get_app_path("erpnext_mcp_server")
            server_path = os.path.join(app_path, "server.py")
            if os.path.exists(server_path):
                self.server_path = server_path

        if not self.transport:
            self.transport = "stdio"

        if not self.log_level:
            self.log_level = "INFO"

        self.save()

    def start_server(self):
        """Start the MCP server process"""
        if self.is_server_running():
            frappe.throw("MCP Server is already running")

        try:
            # Get the current site and environment
            site = frappe.local.site
            sites_path = frappe.utils.get_sites_path()

            # Get the Python executable from Frappe's environment
            python_executable = sys.executable

            # Get the path to the server script
            server_path = self.server_path
            if not server_path or not os.path.exists(server_path):
                # Fallback to default location
                app_path = frappe.get_app_path("erpnext_mcp_server")
                server_path = os.path.join(app_path, "server.py")

            if not os.path.exists(server_path):
                frappe.throw(f"Cannot find MCP server script at: {server_path}")

            # Prepare environment variables
            env = os.environ.copy()
            env.update(
                {
                    "FRAPPE_SITE": site,
                    "SITES_PATH": sites_path,
                    "MCP_TRANSPORT": self.transport or "stdio",
                    "MCP_LOG_LEVEL": self.log_level or "INFO",
                    "PYTHONPATH": f"{sites_path}:{env.get('PYTHONPATH', '')}",
                }
            )

            # Add site-specific paths to PYTHONPATH
            site_path = get_site_path()
            site_apps_path = os.path.join(site_path, "..", "..", "apps")
            env["PYTHONPATH"] = f"{site_apps_path}:{env['PYTHONPATH']}"

            # Prepare command
            cmd = [
                python_executable,
                "-c",
                f'''
import os
import sys

# Add Frappe paths to Python path
sites_path = r"{sites_path}"
site_path = r"{site_path}"
apps_path = os.path.join(sites_path, '..', 'apps')

sys.path.insert(0, apps_path)
sys.path.insert(0, sites_path)
sys.path.insert(0, site_path)

# Import and run Frappe initialization
import frappe
frappe.init(site='{site}', sites_path=sites_path)
frappe.connect()

# Now run the MCP server
exec(open(r'{server_path}').read())
''',
            ]

            # Start the process
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
                bufsize=1,
                universal_newlines=True,
                preexec_fn=os.setsid if hasattr(os, "setsid") else None,
            )

            # Update status
            self.process_id = str(self._process.pid)
            self.is_running = 1
            self.last_start_time = frappe.utils.now()
            self.last_error = None
            self.status = "Starting"
            self.save()

            # Start output monitoring in a separate thread
            self._should_stop = False
            self._output_thread = threading.Thread(
                target=self._monitor_process_output, daemon=True
            )
            self._output_thread.start()

            # Give the server a moment to start
            time.sleep(1)

            # Check if the process is still running
            if self._process.poll() is None:
                self.status = "Running"
                self.save()
                frappe.msgprint("MCP Server started successfully")
            else:
                self.status = "Error"
                self.is_running = 0
                self.save()
                frappe.throw("MCP Server failed to start")

        except Exception as e:
            logger.error(f"Error starting MCP server: {str(e)}")
            self.status = "Error"
            self.is_running = 0
            self.last_error = str(e)
            self.save()
            frappe.throw(f"Failed to start MCP server: {str(e)}")

    def stop_server(self):
        """Stop the MCP server process"""
        if not self.is_server_running():
            frappe.msgprint("MCP Server is not running")
            return

        try:
            # Signal the thread to stop
            self._should_stop = True

            # Get process if not already stored
            if not self._process and self.process_id:
                try:
                    self._process = psutil.Process(int(self.process_id))
                except:
                    pass

            if self._process:
                try:
                    # Try to terminate gracefully first
                    if hasattr(self._process, "terminate"):
                        self._process.terminate()
                    else:
                        os.kill(int(self.process_id), signal.SIGTERM)

                    # Wait for process to terminate
                    time.sleep(2)

                    # If still running, force kill
                    if self._process.poll() is None:
                        if hasattr(self._process, "kill"):
                            self._process.kill()
                        else:
                            os.kill(int(self.process_id), signal.SIGKILL)

                except ProcessLookupError:
                    # Process already dead
                    pass
                except Exception as e:
                    logger.error(f"Error during process termination: {e}")

            # Update status
            self.process_id = None
            self.is_running = 0
            self.last_stop_time = frappe.utils.now()
            self.status = "Stopped"
            self.save()

            frappe.msgprint("MCP Server stopped successfully")

        except Exception as e:
            logger.error(f"Error stopping MCP server: {str(e)}")
            self.last_error = str(e)
            self.save()
            frappe.throw(f"Failed to stop MCP server: {str(e)}")

    def restart_server(self):
        """Restart the MCP server"""
        self.stop_server()
        time.sleep(2)  # Wait for cleanup
        self.start_server()

    def is_server_running(self):
        """Check if the MCP server process is running"""
        if not self.process_id:
            return False

        try:
            # Check if process exists
            if self._process:
                return self._process.poll() is None
            else:
                # Try to check if PID exists
                try:
                    os.kill(int(self.process_id), 0)
                    return True
                except (OSError, ValueError):
                    return False
        except:
            return False

    def get_server_status(self):
        """Get the current status of the MCP server"""
        status = {
            "status": self.status or "Unknown",
            "is_running": self.is_server_running(),
            "process_id": self.process_id,
            "transport": self.transport,
            "last_start_time": self.last_start_time,
            "last_stop_time": self.last_stop_time,
            "last_error": self.last_error,
            "log_level": self.log_level,
        }

        # Update status based on actual process state
        if status["is_running"]:
            if self.status != "Running":
                self.status = "Running"
                self.save()
            status["status"] = "Running"
        else:
            if self.status in ["Running", "Starting"]:
                self.status = "Stopped"
                self.is_running = 0
                self.process_id = None
                self.save()
            status["status"] = "Stopped"

        return status

    def _monitor_process_output(self):
        """Monitor process output and log it"""
        if not self._process or not self._process.stdout:
            return

        try:
            while (
                not self._should_stop and self._process and self._process.poll() is None
            ):
                try:
                    line = self._process.stdout.readline()
                    if line:
                        # Clean up the line
                        line = line.strip()
                        if line:
                            # Log the output
                            logger.info(f"MCP Server: {line}")

                            # Check for special status messages
                            if "Error:" in line:
                                self.last_error = line
                                self.save()
                            elif "Server started successfully" in line:
                                self.status = "Running"
                                self.save()
                    else:
                        # No more output
                        break
                except Exception as e:
                    logger.error(f"Error reading process output: {e}")
                    break
        except Exception as e:
            logger.error(f"Error monitoring MCP server output: {e}")
        finally:
            # Process has ended
            if self._process:
                self._process.stdout.close()
                self.status = "Stopped"
                self.is_running = 0
                self.save()

    def get_server_logs(self, lines=50):
        """Get the last N lines of server logs"""
        try:
            # For now, return the last error if available
            if self.last_error:
                return f"Last Error:\n{self.last_error}"
            else:
                return "No logs available. The server might not have started yet."
        except Exception as e:
            return f"Error retrieving logs: {str(e)}"


# Import psutil if available
try:
    import psutil
except ImportError:
    psutil = None
    logger.warning(
        "psutil not installed, some process management features may be limited"
    )

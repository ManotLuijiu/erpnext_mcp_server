# Copyright (c) 2025, Manot Luijiu and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import subprocess
import os
import signal
import time
from frappe.utils import get_site_path
import threading
import logging

# Configure logging
logger = logging.getLogger(__name__)


class MCPServerSettings(Document):
    def validate(self):
        # Ensure only one active server settings document exists
        if not self.is_new():
            return

        existing = frappe.get_all("MCP Server Settings", filters={"enabled": 1})
        if existing and self.enabled:
            frappe.throw(
                "Only one active MCP Server configuration can exist at a time."
            )

    def on_update(self):
        if self.enabled:
            # Start server if enabled
            self.start_server()
        else:
            # Stop server if disabled
            self.stop_server()

    def start_server(self):
        """Start the MCP server in a separate process"""
        try:
            # Check if server is already running
            if self.is_server_running():
                frappe.msgprint("MCP Server is already running")
                return

            # Get the path to the server file
            site_path = get_site_path()
            server_path = os.path.join(
                frappe.get_app_path("erpnext_mcp_server"), "mcp", "server.py"
            )

            # Prepare environment variables
            env = os.environ.copy()
            env["FRAPPE_SITE"] = frappe.local.site
            env["MCP_TRANSPORT"] = self.transport or "stdio"

            # Start the server process
            self.process = subprocess.Popen(
                [env.get("PYTHONBIN", "python3"), server_path],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )

            # Store the process ID
            self.db_set("process_id", self.process.pid)

            # Start a thread to monitor the process output
            monitor_thread = threading.Thread(
                target=self.monitor_process_output, args=(self.process,), daemon=True
            )
            monitor_thread.start()

            # Wait a moment for the server to start
            time.sleep(1)

            if self.process.poll() is None:
                frappe.msgprint(
                    "MCP Server started successfully (PID: {})".format(self.process.pid)
                )
                self.db_set("status", "Running")
            else:
                output, error = self.process.communicate()
                frappe.msgprint("Failed to start MCP Server: {}".format(error))
                self.db_set("status", "Error")
                self.db_set("last_error", error[:1000])  # Limit error size
        except Exception as e:
            frappe.log_error(
                "Error starting MCP server: {}".format(str(e)), "MCP Server"
            )
            self.db_set("status", "Error")
            self.db_set("last_error", str(e))

    def stop_server(self):
        """Stop the MCP server process"""
        try:
            # Get the stored process ID
            pid = self.process_id

            if not pid:
                self.db_set("status", "Stopped")
                return

            # Try to terminate the process
            try:
                os.kill(int(pid), signal.SIGTERM)
                # Give it some time to terminate gracefully
                time.sleep(2)

                # Force kill if still running
                try:
                    os.kill(int(pid), 0)  # Check if process exists
                    os.kill(int(pid), signal.SIGKILL)
                    frappe.msgprint("MCP Server process killed forcefully")
                except OSError:
                    # Process already terminated
                    pass

                self.db_set("status", "Stopped")
                self.db_set("process_id", None)

            except OSError:
                # Process doesn't exist
                self.db_set("status", "Stopped")
                self.db_set("process_id", None)
        except Exception as e:
            frappe.log_error(
                "Error stopping MCP server: {}".format(str(e)), "MCP Server"
            )
            self.db_set("status", "Error")
            self.db_set("last_error", str(e))

    def is_server_running(self):
        """Check if the MCP Server process is running"""
        pid = self.process_id
        if not pid:
            return False

        try:
            os.kill(int(pid), 0)
            return True
        except OSError:
            # Process doesn't exist
            self.db_set("status", "Stopped")
            self.db_set("process_id", None)
            return False

    def monitor_process_output(self, process):
        """Monitor and log the process output"""
        try:
            for line in process.stdout:
                if line:
                    logger.info("MCP Server: %s", line.strip())

            # Process has ended, check for errors
            _, stderr = process.communicate()
            if stderr:
                logger.error("MCP Server error: %s", stderr)
                self.db_set("last_error", stderr[:1000])

            # Update status
            if process.returncode != 0:
                self.db_set("status", "Error")
            else:
                self.db_set("status", "Stopped")

            self.db_set("process_id", None)

        except Exception as e:
            logger.error("Error monitoring MCP server output: %s", str(e))

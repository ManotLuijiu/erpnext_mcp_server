# Copyright (c) 2025, Manot Luijiu and contributors
# For license information, please see license.txt

import subprocess
import os
import signal
import psutil
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import now
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    # These type hints will only be used during type checking
    from typing import Any


class MCPServerManager(Document):
    # Type hints for DocType fields
    server_name: str
    server_description: Optional[str] = None
    server_type: str
    server_status: str
    server_port: Optional[int] = None
    server_script_path: str
    server_logs: Optional[str] = None
    server_pid: Optional[int] = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.process = None

    def validate(self):
        """Validate document before saving"""
        if not self.server_name:
            frappe.throw(_("Server Name is required"))

        if not self.server_script_path:
            frappe.throw(_("Server Script Path is required"))

        if not self.server_type:
            frappe.throw(_("Server Type is required"))

        # Additional validations
        if self.server_name and len(self.server_name) < 3:
            frappe.throw(_("Server Name must be at least 3 characters long"))

    def before_save(self):
        # Validate script path exists
        if self.server_script_path:
            full_path = frappe.get_app_path(
                "erpnext_mcp_server", self.server_script_path
            )
            if not os.path.exists(full_path):
                frappe.throw(f"Script file not found: {full_path}")

    def on_update(self):
        # Update server status when document is saved
        self.update_server_status()

    @frappe.whitelist()
    def start_server(self):
        """Start the MCP Server"""
        if self.server_status == "Running":
            frappe.msgprint("Server is already running")
            return
        try:
            script_path = frappe.get_app_path(
                "erpnext_mcp_server", self.server_script_path
            )

            # Start the server process
            cmd = ["python", script_path]

            # Create a log file for this server
            log_file = frappe.get_app_path(
                "erpnext_mcp_server", f"logs/{self.name}.log"
            )
            os.makedirs(os.path.dirname(log_file), exist_ok=True)

            with open(log_file, "a") as f:
                f.write(f"\n\n=== Server started at {now()} ===\n")
                self.process = subprocess.Popen(
                    cmd,
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    preexec_fn=os.setsid,  # Create new process group
                )

            # Save PID for later reference
            self.server_pid = self.process.pid
            self.server_status = "Running"
            self.save()

            frappe.msgprint(f"Server '{self.server_name}' started successfully")

            return {
                "success": True,
                "message": f"Server '{self.server_name}' started successfully",
            }

        except Exception as e:
            self.server_status = "Error"
            self.server_logs = str(e)
            self.save()
            frappe.throw(f"{_('Failed to start server:')} {str(e)}")
            return {"success": False, "message": f"Failed to start server: {str(e)}"}

    @frappe.whitelist()
    def stop_server(self):
        """Stop the MCP Server"""
        if self.server_status != "Running":
            frappe.msgprint(_("Server is not running"))
            return
        try:
            if hasattr(self, "server_pid") and self.server_pid:
                # Find process by PID
                try:
                    process = psutil.Process(self.server_pid)
                    # Kill the entire process group
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                except psutil.NoSuchProcess:
                    pass
            self.server_status = "Stopped"
            self.server_pid = None
            self.save()

            frappe.msgprint(f"Server '{self.server_name}' stopped successfully")

            return {
                "success": True,
                "message": f"Server '{self.server_name}' stopped successfully",
            }

        except Exception as e:
            frappe.throw(f"Failed to stop server: {str(e)}")
            return {"success": False, "message": f"Failed to stop server: {str(e)}"}

    @frappe.whitelist()
    def restart_server(self):
        """Restart the MCP Server"""
        self.stop_server()
        self.start_server()

    @frappe.whitelist()
    def view_logs(self):
        """Load and display server logs"""
        try:
            log_file = frappe.get_app_path(
                "erpnext_mcp_server", f"logs/{self.name}.log"
            )

            if os.path.exists(log_file):
                with open(log_file, "r") as f:
                    logs = f.read()
                    # Get last 1000 lines
                    lines = logs.split("\n")
                    self.server_logs = "\n".join(lines[-1000:])
            else:
                self.server_logs = "No logs available"

            self.save()
            frappe.msgprint("Logs loaded successfully")

        except Exception as e:
            frappe.throw(f"Failed to load logs: {str(e)}")

    @frappe.whitelist()
    def update_server_status(self):
        """Check if server is still running and update status"""
        if hasattr(self, "server_pid") and self.server_pid:
            try:
                process = psutil.Process(self.server_pid)
                if process.is_running() and process.status() != psutil.STATUS_ZOMBIE:
                    self.server_status = "Running"
                else:
                    self.server_status = "Stopped"
                    self.server_pid = None
            except psutil.NoSuchProcess:
                self.server_status = "Stopped"
                self.server_pid = None
        else:
            self.server_status = "Stopped"

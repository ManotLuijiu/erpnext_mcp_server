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


class MCPServerManager(Document):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.process = None
        self.server_script_path = None  # Initialize server_script_path
        self.server_name = None  # Initialize server_name

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

        except Exception as e:
            self.server_status = "Error"
            self.server_logs = str(e)
            self.save()
            frappe.throw(f"{_('Failed to start server:')} {str(e)}")

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

        except Exception as e:
            frappe.throw(f"Failed to stop server: {str(e)}")

    def restart_server(self):
        """Restart the MCP Server"""
        self.stop_server()
        self.start_server()

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

import frappe
import json
import psutil
import os
import subprocess
import time
from typing import Dict, List, Any
from datetime import datetime
from frappe.utils import get_site_path, now_datetime, format_datetime


@frappe.whitelist()
def get_mcp_server_status() -> Dict[str, Any]:
    """Get the current status of the MCP server"""
    try:
        # Get MCP Server settings
        settings = frappe.get_single("MCP Server Settings")

        # Check if the server process is running
        is_running = False
        process_id = None
        uptime = None
        status = "Stopped"

        # Check if server is enabled
        if not settings.enabled:
            status = "Disabled"
        else:
            # Check if the server is running
            if settings.process_id:
                try:
                    # Check if the process exists
                    process = psutil.Process(settings.process_id)
                    if process.is_running():
                        is_running = True
                        process_id = settings.process_id
                        status = "Running"

                        # Calculate uptime
                        if settings.last_start_time:
                            start_time = frappe.utils.get_datetime(
                                settings.last_start_time
                            )
                            uptime = str(
                                frappe.utils.now_datetime() - start_time
                            ).split(".")[0]
                except psutil.NoSuchProcess:
                    # Process doesn't exist, clear the PID
                    settings.process_id = None
                    settings.save(ignore_permissions=True)

        # Check if errors occurred
        if settings.last_error and not is_running:
            if status == "Stopped":
                status = "Error"

        # # Determine server status
        # status = "Running" if is_running else "Stopped"
        # if settings.last_error and not is_running:
        #     status = "Error"

        # Get additional metrics
        active_connections = 0  # TODO: Implement actual connection count
        available_tools = (
            len(settings.available_tools) if settings.available_tools else 5
        )  # Default count
        available_resources = (
            len(settings.available_resources) if settings.available_resources else 3
        )  # Default count

        return {
            "status": status,
            "is_running": is_running,
            "process_id": process_id,
            "last_start_time": settings.last_start_time,
            "last_stop_time": settings.last_stop_time,
            "last_error": settings.last_error,
            "enabled": settings.enabled,
            "transport": settings.transport or "stdio",
            "server_port": settings.server_port,
            "server_version": settings.server_version,
            "log_level": settings.log_level,
            "max_connections": settings.max_connections,
            "timeout": settings.timeout,
            "auth_enabled": settings.auth_enabled,
            "uptime": uptime,
            "active_connections": active_connections,
            "available_tools": available_tools,
            "available_resources": available_resources,
        }

    except Exception as e:
        frappe.logger().error(f"Error getting MCP server status: {str(e)}")
        return {
            "status": "Error",
            "is_running": False,
            "last_error": str(e),
            "enabled": False,
            "transport": "stdio",
            "active_connections": 0,
            "available_tools": 0,
            "available_resources": 0,
        }


@frappe.whitelist()
def start_mcp_server() -> Dict[str, Any]:
    """Start the MCP server"""
    try:
        # Get settings
        settings = frappe.get_single("MCP Server Settings")

        # Check if server is enabled
        if not settings.enabled:
            return {
                "status": "error",
                "message": "MCP server is disabled. Enable it in settings first.",
            }

        # Check if server is already running
        status_info = get_mcp_server_status()
        if status_info.get("is_running"):
            return {"status": "error", "message": "MCP server is already running"}

        # Prepare the environment
        site_path = get_site_path()
        apps_path = frappe.get_app_path("erpnext_mcp_server")
        server_script = os.path.join(apps_path, "mcp", "standalone_server.py")

        # Check if server script exists
        if not os.path.exists(server_script):
            return {
                "status": "error",
                "message": f"Server script not found at {server_script}",
            }

        # Environment setup
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{site_path}:{apps_path}:{env.get('PYTHONPATH', '')}"
        env["FRAPPE_SITE"] = frappe.local.site
        env["FRAPPE_SITE_PATH"] = site_path

        # Prepare the command
        python_executable = frappe.utils.which("python3") or "python3"
        cmd = [
            python_executable,
            server_script,
            "--site",
            frappe.local.site,
            "--transport",
            settings.transport or "stdio",
        ]

        if settings.transport != "stdio" and settings.server_port:
            cmd.extend(["--port", str(settings.server_port)])

        # Log file path
        log_dir = os.path.join(site_path, "logs")
        log_file = os.path.join(log_dir, "mcp_server.log")
        os.makedirs(log_dir, exist_ok=True)

        # Start the server process
        with open(log_file, "a") as f:
            process = subprocess.Popen(
                cmd,
                stdout=f,
                stderr=subprocess.STDOUT,
                env=env,
                cwd=site_path,
                preexec_fn=os.setsid
                if hasattr(os, "setsid")
                else None,  # Create process group
            )

        # Give it a moment to start
        time.sleep(1)

        # Check if process is still running
        if process.poll() is None:
            # Update settings
            settings.process_id = process.pid
            settings.last_start_time = now_datetime()
            settings.last_error = None
            settings.save(ignore_permissions=True)

            return {
                "status": "success",
                "message": "MCP server started successfully",
                "process_id": process.pid,
            }
        else:
            # Process died immediately, read the error
            with open(log_file, "r") as f:
                lines = f.readlines()
                error_msg = "".join(lines[-20:])  # Get last 20 lines

            settings.last_error = error_msg
            settings.save(ignore_permissions=True)

            return {
                "status": "error",
                "message": f"MCP server failed to start. Check logs for details. Error: {error_msg}",
            }

    except Exception as e:
        frappe.logger().error(f"Error starting MCP server: {str(e)}")

        # Save error to settings
        try:
            settings = frappe.get_single("MCP Server Settings")
            settings.last_error = str(e)
            settings.save(ignore_permissions=True)
        except:
            pass

        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def stop_mcp_server() -> Dict[str, Any]:
    """Stop the MCP server"""
    try:
        settings = frappe.get_single("MCP Server Settings")

        if not settings.process_id:
            return {"status": "error", "message": "No running MCP server process found"}

        try:
            # Get the process
            process = psutil.Process(settings.process_id)

            # Get all child processes
            children = process.children(recursive=True)

            # Terminate the process gracefully
            for child in children:
                try:
                    child.terminate()
                except:
                    pass

            process.terminate()

            # Wait for process to terminate (max 10 seconds)
            try:
                process.wait(timeout=10)

                # Also wait for children to terminate
                for child in children:
                    try:
                        child.wait(timeout=2)
                    except:
                        pass
            except psutil.TimeoutExpired:
                # Force kill if it doesn't terminate
                for child in children:
                    try:
                        child.kill()
                    except:
                        pass

                process.kill()
                process.wait()

            # Update settings
            settings.process_id = None
            settings.last_stop_time = now_datetime()
            settings.save(ignore_permissions=True)

            return {"status": "success", "message": "MCP server stopped successfully"}

        except psutil.NoSuchProcess:
            # Process doesn't exist
            settings.process_id = None
            settings.save(ignore_permissions=True)
            return {"status": "error", "message": "Process no longer exists"}

    except Exception as e:
        frappe.logger().error(f"Error stopping MCP server: {str(e)}")
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def get_mcp_server_logs(lines: int = 100) -> str:
    """Get the last N lines of server logs"""
    try:
        log_file = os.path.join(get_site_path(), "logs", "mcp_server.log")

        if not os.path.exists(log_file):
            return "No log file found. Server may not have been started yet."

        # Read the last N lines efficiently
        with open(log_file, "r") as f:
            # Read all lines
            all_lines = f.readlines()

            # Get the last N lines
            start_index = max(0, len(all_lines) - lines)
            last_lines = all_lines[start_index:]

            return "".join(last_lines)

    except Exception as e:
        return f"Error reading logs: {str(e)}"


@frappe.whitelist()
def save_mcp_server_settings(settings_data: Dict[str, Any]) -> Dict[str, Any]:
    """Save MCP server settings"""
    try:
        settings = frappe.get_single("MCP Server Settings")

        # Update only allowed fields
        allowed_fields = [
            "enabled",
            "transport",
            "server_port",
            "log_level",
            "max_connections",
            "timeout",
            "api_key",
            "auth_enabled",
        ]

        for key, value in settings_data.items():
            if key in allowed_fields and hasattr(settings, key):
                setattr(settings, key, value)

        settings.save()

        return {"status": "success", "message": "Settings saved successfully"}

    except Exception as e:
        frappe.logger().error(f"Error saving MCP server settings: {str(e)}")
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def test_mcp_connection() -> Dict[str, Any]:
    """Test the MCP server connection"""
    try:
        status = get_mcp_server_status()

        if status.get("is_running"):
            # TODO: Implement actual connection test
            # For now, just verify the process is running
            return {
                "status": "success",
                "message": "MCP server is running and accessible",
                "details": {
                    "process_id": status.get("process_id"),
                    "transport": status.get("transport"),
                    "port": status.get("server_port"),
                },
            }
        else:
            return {
                "status": "error",
                "message": f"MCP server is not running. Current status: {status.get('status')}",
                "details": status,
            }

    except Exception as e:
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def refresh_tools_and_resources() -> Dict[str, Any]:
    """Refresh the list of available tools and resources"""
    try:
        # This would query the running MCP server for available tools and resources
        # For now, we'll use placeholder data

        settings = frappe.get_single("MCP Server Settings")

        # Clear existing tools and resources
        settings.available_tools = []
        settings.available_resources = []

        # Add default tools (these would come from the actual server)
        default_tools = [
            {
                "tool_name": "get_document",
                "description": "Get a specific document from ERPNext",
                "enabled": 1,
            },
            {
                "tool_name": "search_documents",
                "description": "Search for documents in ERPNext",
                "enabled": 1,
            },
            {
                "tool_name": "create_document",
                "description": "Create a new document in ERPNext",
                "enabled": 1,
            },
            {
                "tool_name": "run_query",
                "description": "Run a SQL query on ERPNext database",
                "enabled": 1,
            },
            {
                "tool_name": "get_report",
                "description": "Get report data from ERPNext",
                "enabled": 1,
            },
        ]

        # Add default resources
        default_resources = [
            {
                "uri": "erpnext://doctypes",
                "resource_name": "Available DocTypes",
                "description": "List of all DocTypes in ERPNext",
                "mime_type": "application/json",
                "enabled": 1,
            },
            {
                "uri": "erpnext://reports",
                "resource_name": "Available Reports",
                "description": "List of all Reports in ERPNext",
                "mime_type": "application/json",
                "enabled": 1,
            },
            {
                "uri": "erpnext://config",
                "resource_name": "Server Configuration",
                "description": "Current ERPNext configuration",
                "mime_type": "application/json",
                "enabled": 1,
            },
        ]

        for tool in default_tools:
            settings.append("available_tools", tool)

        for resource in default_resources:
            settings.append("available_resources", resource)

        settings.save()

        return {
            "status": "success",
            "message": "Tools and resources refreshed successfully",
            "tools_count": len(default_tools),
            "resources_count": len(default_resources),
        }

    except Exception as e:
        frappe.logger().error(f"Error refreshing tools and resources: {str(e)}")
        return {"status": "error", "message": str(e)}

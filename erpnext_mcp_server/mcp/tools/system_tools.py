"""
System Tools for ERPNext MCP Server
Handles system information and safe bench command execution
"""

import json
import os
import platform
import subprocess
from typing import Any, Dict, List, Optional

import frappe
from frappe import get_installed_apps
from frappe.utils import get_site_name
from frappe.utils.change_log import get_versions


class SystemTools:
    """Tools for system operations and information."""

    def __init__(self, config=None):
        print(f"config SystemTools {config}")
        self.config = config
        # Only allow safe bench commands
        self.allowed_bench_commands = {
            "version": "Show bench and app versions",
            "status": "Show process status",
            "list-apps": "List installed applications",
            "doctor": "Run system health check",
            "config": "Show configuration",
            "show-config": "Show site configuration",
            "backup": "Create site backup",
            "restore": "Restore site backup (read-only info)",
            "migrate": "Show migration status (read-only)",
            "build": "Build assets (read-only info)",
        }

    async def get_system_info(self) -> str:
        """Get comprehensive system information."""
        try:
            output = ["🖥️  System Information", "=" * 30, ""]

            # Site information
            site_name = get_site_name(
                frappe.local.request.host if frappe.local.request else None
            )
            output.extend(
                [
                    "🌐 Site Information:",
                    f"  • Site Name: {site_name}",
                    f"  • Host: {frappe.local.request.host if frappe.local.request else 'N/A'}",
                    f"  • User: {frappe.session.user}",
                    f"  • Session: {frappe.session.sid if frappe.session.sid else 'N/A'}",
                    "",
                ]
            )

            # Version information
            versions = get_versions()

            # Installed app
            # installed_apps = set(get_installed_apps())
            # apps = [app for app in apps if app["name"] not in installed_apps]
            # print(f"apps {apps}")

            output.append("📦 Application Versions:")
            for app, version in versions.items():
                output.append(f"  • {app}: {version}")
            output.append("")

            # Database information
            db_info = self._get_database_info()
            output.extend(
                [
                    "🗄️  Database Information:",
                    f"  • Database: {db_info['name']}",
                    f"  • Version: {db_info['version']}",
                    f"  • Size: {db_info['size']}",
                    f"  • Tables: {db_info['table_count']}",
                    "",
                ]
            )

            # Platform information
            output.extend(
                [
                    "🖥️  Platform Information:",
                    f"  • OS: {platform.system()} {platform.release()}",
                    f"  • Architecture: {platform.machine()}",
                    f"  • Python: {platform.python_version()}",
                    f"  • Processor: {platform.processor() or 'Unknown'}",
                    "",
                ]
            )

            # Memory and storage
            storage_info = self._get_storage_info()
            output.extend(
                ["💾 Storage Information:", f"  • Disk Usage: {storage_info}", ""]
            )

            # Configuration
            config_info = self._get_config_info()
            output.extend(
                [
                    "⚙️  Configuration:",
                    f"  • Debug Mode: {config_info['debug']}",
                    f"  • Developer Mode: {config_info['developer_mode']}",
                    f"  • Maintenance Mode: {config_info['maintenance_mode']}",
                    f"  • Auto Update: {config_info['auto_update']}",
                    "",
                ]
            )

            return "\n".join(output)

        except Exception as e:
            return f"❌ Error getting system info: {str(e)}"

    def _get_database_info(self) -> Dict[str, Any]:
        """Get database information."""
        try:
            # Database name
            db_name = frappe.conf.db_name

            # Database version
            version_result = frappe.db.sql("SELECT VERSION() as version", as_dict=True)
            version = version_result[0]["version"] if version_result else "Unknown"  # type: ignore

            # Database size
            size_result = frappe.db.sql(
                f"""
                SELECT 
                    ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS size_mb
                FROM information_schema.tables 
                WHERE table_schema = '{db_name}'
            """,
                as_dict=True,
            )
            size = (
                f"{size_result[0]['size_mb']} MB"  # type: ignore
                if size_result and size_result[0]["size_mb"]  # type: ignore
                else "Unknown"
            )

            # Table count
            tables = frappe.db.sql("SHOW TABLES", as_dict=True)
            table_count = len(tables)  # type: ignore

            return {
                "name": db_name,
                "version": version,
                "size": size,
                "table_count": table_count,
            }
        except Exception:
            return {
                "name": "Unknown",
                "version": "Unknown",
                "size": "Unknown",
                "table_count": 0,
            }

    def _get_storage_info(self) -> str:
        """Get storage information."""
        try:
            import shutil

            # Get disk usage for current directory
            total, used, free = shutil.disk_usage(frappe.get_site_path())

            total_gb = total // (1024**3)
            used_gb = used // (1024**3)
            free_gb = free // (1024**3)
            used_percent = (used / total) * 100

            return f"{used_gb}GB used / {total_gb}GB total ({used_percent:.1f}% used, {free_gb}GB free)"
        except Exception:
            return "Unable to determine"

    def _get_config_info(self) -> Dict[str, Any]:
        """Get configuration information."""
        return {
            "debug": getattr(frappe.conf, "debug", False),
            "developer_mode": getattr(frappe.conf, "developer_mode", False),
            "maintenance_mode": getattr(frappe.conf, "maintenance_mode", False),
            "auto_update": getattr(frappe.conf, "auto_update", False),
        }

    async def bench_command(self, command: str, args: List[str] = None) -> str:  # type: ignore
        """Execute safe bench commands."""
        try:
            # Security check
            if command not in self.allowed_bench_commands:
                return (
                    f"❌ Command not allowed: {command}\n\n🔧 Allowed commands:\n"
                    + "\n".join(
                        [
                            f"  • {cmd}: {desc}"
                            for cmd, desc in self.allowed_bench_commands.items()
                        ]
                    )
                )

            # Build command
            cmd_parts = ["bench", command]
            if args:
                cmd_parts.extend(args)

            output = [
                f"🔧 Bench Command: {' '.join(cmd_parts)}",
                "=" * (len(" ".join(cmd_parts)) + 17),
                "",
            ]

            try:
                # Execute command with timeout
                result = subprocess.run(
                    cmd_parts,
                    capture_output=True,
                    text=True,
                    timeout=30,  # 30 second timeout
                    cwd=frappe.get_site_path("../.."),  # Go to bench directory
                )

                if result.returncode == 0:
                    output.append("✅ Command executed successfully:")
                    output.append("")
                    if result.stdout:
                        output.extend(result.stdout.strip().split("\n"))
                else:
                    output.append("⚠️  Command completed with warnings:")
                    output.append("")
                    if result.stdout:
                        output.extend(result.stdout.strip().split("\n"))
                    if result.stderr:
                        output.append("")
                        output.append("Errors/Warnings:")
                        output.extend(result.stderr.strip().split("\n"))

            except subprocess.TimeoutExpired:
                output.append("⏰ Command timed out after 30 seconds")
            except FileNotFoundError:
                output.append(
                    "❌ Bench command not found. Make sure you're in a Frappe environment."
                )
            except Exception as e:
                output.append(f"❌ Error executing command: {str(e)}")

            return "\n".join(output)

        except Exception as e:
            return f"❌ Error with bench command: {str(e)}"

    async def get_process_info(self) -> str:
        """Get information about running processes."""
        try:
            output = ["🔄 Process Information", "=" * 25, ""]

            # Try to get bench processes
            try:
                result = subprocess.run(
                    ["bench", "status"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=frappe.get_site_path("../.."),
                )

                if result.returncode == 0 and result.stdout:
                    output.append("📊 Bench Process Status:")
                    output.extend(result.stdout.strip().split("\n"))
                else:
                    output.append("⚠️  Could not get bench status")

            except Exception:
                output.append("⚠️  Bench status not available")

            # System load info
            try:
                if hasattr(os, "getloadavg"):
                    load1, load5, load15 = os.getloadavg()
                    output.extend(
                        [
                            "",
                            "📈 System Load:",
                            f"  • 1 min: {load1:.2f}",
                            f"  • 5 min: {load5:.2f}",
                            f"  • 15 min: {load15:.2f}",
                        ]
                    )
            except Exception:
                pass

            return "\n".join(output)

        except Exception as e:
            return f"❌ Error getting process info: {str(e)}"

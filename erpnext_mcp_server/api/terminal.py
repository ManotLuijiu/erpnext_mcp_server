import json
import os
import sys
from io import StringIO

import frappe
import requests
from frappe import _
from frappe.realtime import publish_realtime
from frappe.utils import now_datetime
from frappe.utils.response import build_response
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# This will be your MCP server instance - we'll create a placeholder for now
# In a real implementation, you'd import your MCP server
mcp_server = None


@frappe.whitelist()
def get_mcp_settings():
    """Get MCP Server settings"""
    try:
        # Check if user has permissions
        if not frappe.has_permission("MCP Settings", "read"):
            frappe.throw(
                _("You don't have permission to access MCP Settings"),
                frappe.PermissionError,
            )

        # Check if settings exist, if not create them
        if not frappe.db.exists("MCP Settings"):
            create_default_settings()

        settings = frappe.get_single("MCP Settings")

        # If settings are empty, try to get from environment variables
        api_url = settings.api_url or os.environ.get("MCP_API_URL")
        websocket_url = settings.websocket_url or os.environ.get("MCP_WEBSOCKET_URL")
        auto_reconnect = settings.auto_reconnect

        # Also check Frappe site config for settings
        site_config = frappe.get_site_config()
        if not api_url and site_config.get("mcp_api_url"):
            api_url = site_config.get("mcp_api_url")
        if not websocket_url and site_config.get("mcp_websocket_url"):
            websocket_url = site_config.get("mcp_websocket_url")

        return {
            "api_url": api_url,
            "websocket_url": websocket_url,
            "auto_reconnect": auto_reconnect,
            "is_configured": bool(api_url and websocket_url),
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


def create_default_settings():
    """Create default MCP settings document"""
    try:
        settings = frappe.new_doc("MCP Settings")

        # Try to get values from environment variables
        settings.api_url = os.environ.get("MCP_API_URL", "")
        settings.websocket_url = os.environ.get("MCP_WEBSOCKET_URL", "")
        settings.api_key = os.environ.get("MCP_API_KEY", "")
        settings.api_secret = os.environ.get("MCP_API_SECRET", "")
        settings.default_timeout = 30
        settings.auto_reconnect = 1

        # Also check Frappe site config for settings
        site_config = frappe.get_site_config()
        if not settings.api_url and site_config.get("mcp_api_url"):
            settings.api_url = site_config.get("mcp_api_url")
        if not settings.websocket_url and site_config.get("mcp_websocket_url"):
            settings.websocket_url = site_config.get("mcp_websocket_url")
        if not settings.api_key and site_config.get("mcp_api_key"):
            settings.api_key = site_config.get("mcp_api_key")
        if not settings.api_secret and site_config.get("mcp_api_secret"):
            settings.api_secret = site_config.get("mcp_api_secret")

        settings.insert(ignore_permissions=True)
        frappe.db.commit()

        return settings
    except Exception as e:
        frappe.log_error(
            f"Error creating default MCP settings: {str(e)}", "MCP Settings Error"
        )
        return None


@frappe.whitelist()
def get_mcp_token():
    """Get authentication token from MCP server"""
    try:
        # Check if user has permissions
        if not frappe.has_permission("MCP Settings", "read"):
            frappe.throw(
                _("You don't have permission to access MCP Server"),
                frappe.PermissionError,
            )

        # Get MCP settings
        settings = frappe.get_single("MCP Settings")

        print(f"settings {settings}")

        if not settings.api_url or not settings.api_key or not settings.api_secret:  # type: ignore
            frappe.throw(_("MCP Server settings not configured correctly"))

        # Make API request to get token
        response = requests.post(
            f"{settings.api_url}/auth/token",  # type: ignore
            headers={"Content-Type": "application/json"},
            data=json.dumps(
                {
                    "api_key": settings.api_key,  # type: ignore
                    "api_secret": settings.api_secret,  # type: ignore
                    "user": frappe.session.user,  # Include user information for tracking
                }
            ),
            timeout=int(settings.default_timeout or 30),  # type: ignore
        )

        if response.status_code == 200:
            token_data = response.json()

            # Store token in cache for future use (optional, we're also using localStorage)
            expires_in = token_data.get("expires_in", 3600)
            frappe.cache().set_value(
                f"mcp_token:{frappe.session.user}",
                token_data.get("token"),
                expires_in_sec=expires_in,
            )

            # Return token with expiry information
            return {"token": token_data.get("token"), "expires_in": expires_in}
        else:
            frappe.log_error(
                f"Failed to get MCP token: {response.status_code} - {response.text}",
                "MCP Token Request Error",
            )
            return {
                "error": f"Failed to authenticate with MCP Server: {response.status_code}"
            }

    except Exception as e:
        frappe.log_error(f"Error getting MCP token: {str(e)}", "MCP Token Error")
        return {"error": str(e)}


@frappe.whitelist()
def log_terminal_event():
    """Log terminal event for auditing"""
    try:
        event_type = frappe.local.form_dict.get("event_type")
        session_id = frappe.local.form_dict.get("session_id")
        command_type = frappe.local.form_dict.get("command_type")
        details = frappe.local.form_dict.get("details")

        # Create log entry
        log = frappe.new_doc("MCP Terminal Log")
        log.user = frappe.session.user  # type: ignore
        log.timestamp = now_datetime()  # type: ignore
        log.action = event_type  # type: ignore
        log.session_id = session_id  # type: ignore
        log.command_type = command_type  # type: ignore
        log.details = details  # type: ignore
        log.insert(ignore_permissions=True)
        frappe.db.commit()

        return {"success": True}
    except Exception as e:
        frappe.log_error(
            f"Error logging terminal event: {str(e)}", "Terminal Event Log Error"
        )
        return {"error": str(e)}


@frappe.whitelist(allow_guest=False)
def process_command(command):
    """Process a terminal command and return formatted output"""
    handler = MCPTerminalHandler()
    return handler.process_command(command)


def socket_process_command(command, socket):
    """Socket.IO handler for processing commands"""
    handler = MCPTerminalHandler()
    output = handler.process_command(command)

    # Send the response back through Socket.IO
    publish_realtime("terminal_response", {"output": output}, user=frappe.session.user)


# Register Socket.IO event handler
# if hasattr(frappe, 'realtime'):
#     @frappe.realtime.socketio.on('terminal_command')
#     def handle_terminal_command(data):
#         if 'command' in data:
#             socket_process_command(data['command'], frappe.realtime.socketio)


@frappe.whitelist(allow_guest=False)
def connect():
    """WebSocket endpoint for the MCP terminal connection"""
    frappe.response["type"] = "websocket"
    frappe.response["handler"] = (
        "erpnext_mcp_server.erpnext_mcp_server.api.terminal.MCPTerminalHandler"
    )
    return build_response("websocket")


class MCPTerminalHandler:
    """WebSocket handler for the MCP terminal"""

    def __init__(self):
        # self.request = request
        self.user = frappe.session.user
        self.console = Console(file=StringIO(), highlight=True, record=True)

    def on_message(self, message):
        """Handle incoming message from the client"""
        try:
            data = json.loads(message)
            command = data.get("command", "").strip()

            if not command:
                return self.send_output("Please enter a command")

            # Process the command
            output = self.process_command(command)
            return self.send_output(output)

        except Exception as e:
            error_message = f"Error processing command: {str(e)}"
            return self.send_output(error_message, is_error=True)

    def process_command(self, command: str) -> str:
        """Process an MCP command and return formatted output"""
        # Reset the console capture
        self.console = Console(file=StringIO(), highlight=True, record=True)

        # Parse the command
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        # Handle built-in commands
        if cmd == "help":
            self.show_help()
        elif cmd == "query":
            self.cmd_query(args)
        elif cmd == "doc":
            self.cmd_get_doc(args)
        elif cmd == "fields":
            self.cmd_get_fields(args)
        else:
            self.console.print(f"[bold red]Unknown command:[/] [yellow]{cmd}[/]")
            self.console.print("Type [bold green]help[/] for available commands")

        # Get the captured output
        output = (
            self.console.file.getvalue()
            if isinstance(self.console.file, StringIO)
            else ""
        )
        return output

    def send_output(self, output: str, is_error: bool = False) -> str:
        """Send output back to the client"""
        # Convert rich output to ANSI escape sequences that xterm.js can render
        return json.dumps({"output": output, "is_error": is_error})

    def show_help(self) -> None:
        """Show help information"""
        self.console.print(Panel("[bold]ERPNext MCP Terminal Help[/]", expand=False))
        self.console.print()

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Command", style="cyan")
        table.add_column("Description", style="green")
        table.add_column("Example", style="yellow")

        table.add_row("help", "Show this help message", "help")
        table.add_row(
            "query",
            "Query data from DocType",
            "query Customer fields=name,email limit=5",
        )
        table.add_row("doc", "Get a single document", "doc Customer CUST-001")
        table.add_row("fields", "List fields of a DocType", "fields Customer")

        self.console.print(table)

    def cmd_query(self, args: str) -> None:
        """Handle the query command"""
        # Parse arguments like "Customer fields=name,email limit=5"
        if not args:
            self.console.print("[bold red]Error:[/] Missing DocType argument")
            self.console.print(
                "Usage: query [bold]<DocType>[/] [fields=...] [filters=...] [limit=...] [order_by=...]"
            )
            return

        parts = args.split()
        doctype = parts[0]

        # Parse keyword arguments
        kwargs = {}
        for part in parts[1:]:
            if "=" in part:
                key, value = part.split("=", 1)
                if key == "fields":
                    kwargs[key] = value.split(",")
                elif key == "filters":
                    try:
                        kwargs[key] = json.loads(value)
                    except:
                        self.console.print(
                            f"[bold red]Error:[/] Invalid filters format: {value}"
                        )
                        return
                elif key == "limit":
                    try:
                        kwargs[key] = int(value)
                    except:
                        self.console.print(
                            f"[bold red]Error:[/] Invalid limit: {value}"
                        )
                        return
                else:
                    kwargs[key] = value

        try:
            # Use frappe.get_all to query data
            result = frappe.get_all(doctype, **kwargs)

            if not result:
                self.console.print(
                    f"[yellow]No results found for[/] [bold]{doctype}[/]"
                )
                return

            # Create a table for the results
            table = Table(
                title=f"{doctype} Query Results",
                show_header=True,
                header_style="bold magenta",
            )

            # Add columns based on the first result
            columns = list(result[0].keys())
            for column in columns:
                table.add_column(column, style="cyan")

            # Add rows
            for row in result:
                table.add_row(*[str(row.get(col, "")) for col in columns])

            self.console.print(table)
            self.console.print(
                f"[green]Retrieved[/] [bold]{len(result)}[/] [green]records[/]"
            )

        except Exception as e:
            self.console.print(f"[bold red]Error:[/] {str(e)}")

    def cmd_get_doc(self, args: str) -> None:
        """Handle the doc command"""
        if not args:
            self.console.print("[bold red]Error:[/] Missing arguments")
            self.console.print("Usage: doc [bold]<DocType> <name>[/]")
            return

        parts = args.split(maxsplit=1)
        if len(parts) != 2:
            self.console.print("[bold red]Error:[/] Missing document name")
            return

        doctype, name = parts

        try:
            doc = frappe.get_doc(doctype, name)

            # Create a panel with document info
            self.console.print(Panel(f"[bold]{doctype}:[/] {name}", style="green"))

            # Create a table for field values
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="yellow")

            # Add standard fields
            for key, value in doc.as_dict().items():
                if key.startswith("_"):
                    continue

                if isinstance(value, (list, dict)):
                    value = json.dumps(value, indent=2)
                table.add_row(key, str(value))

            self.console.print(table)

        except Exception as e:
            self.console.print(f"[bold red]Error:[/] {str(e)}")

    def cmd_get_fields(self, args: str) -> None:
        """Handle the fields command"""
        if not args:
            self.console.print("[bold red]Error:[/] Missing DocType argument")
            self.console.print("Usage: fields [bold]<DocType>[/]")
            return

        doctype = args.strip()

        try:
            meta = frappe.get_meta(doctype)

            # Create a table for the fields
            table = Table(
                title=f"{doctype} Fields", show_header=True, header_style="bold magenta"
            )
            table.add_column("Fieldname", style="cyan")
            table.add_column("Label", style="yellow")
            table.add_column("Type", style="green")
            table.add_column("Required", style="red")

            # Add rows for each field
            for field in meta.fields:
                required = "✓" if field.reqd else ""
                table.add_row(field.fieldname, field.label, field.fieldtype, required)

            self.console.print(table)
            self.console.print(f"[green]Total fields:[/] [bold]{len(meta.fields)}[/]")

        except Exception as e:
            self.console.print(f"[bold red]Error:[/] {str(e)}")

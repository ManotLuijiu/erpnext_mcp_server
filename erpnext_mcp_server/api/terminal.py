import json
import sys
from io import StringIO

import frappe
from frappe.realtime import publish_realtime
from frappe.utils.response import build_response
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# This will be your MCP server instance - we'll create a placeholder for now
# In a real implementation, you'd import your MCP server
mcp_server = None


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

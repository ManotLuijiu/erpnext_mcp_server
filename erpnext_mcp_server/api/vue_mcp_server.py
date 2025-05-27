import subprocess

import frappe
import mcp.server.stdio
import mcp.types as types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions

# Create a server instance
server = Server("erpnext-mcp-server")

print(f"server {server}")


@server.list_prompts()
async def handle_list_prompts() -> list[types.Prompt]:
    return [
        types.Prompt(
            name="erpnext-mcp-prompt",
            description="An ERPNext MCP prompt template",
            arguments=[
                types.PromptArgument(
                    name="arg1", description="ERPNext MCP argument", required=True
                )
            ],
        )
    ]


@server.get_prompt()
async def handle_get_prompt(
    name: str, arguments: dict[str, str] | None
) -> types.GetPromptResult:
    if name != "erpnext-mcp-prompt":
        raise ValueError(f"Unknown prompt: {name}")

    return types.GetPromptResult(
        description="ERPNext MCP prompt",
        messages=[
            types.PromptMessage(
                role="user",
                content=types.TextContent(type="text", text="ERPNext MCP prompt text"),
            )
        ],
    )


async def run():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="erpnext-mcp-server",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(run())


@frappe.whitelist()
def execute_terminal_command(command):
    """Execute terminal command and send realtime updates"""
    try:
        # Security check - only allow certain commands
        allowed_commands = [
            "pwd",
            "ls",
            "whoami",
            "get_document",
            "search_documents",
            "execute_sql",
            "list_files",
            "bench_command",
            "list_doctypes",
        ]
        base_command = command.split()[0] if command else ""

        if base_command not in allowed_commands:
            frappe.publish_realtime(
                event="terminal_output",
                message={
                    "type": "error",
                    "data": f"Command not allowed: {base_command}",
                },
                user=frappe.session.user,
            )
            frappe.msgprint(f"Command {base_command} not allowed")
            return {"success": False, "error": "Command not allowed"}

        # Echo the command
        # Publish initial response
        frappe.publish_realtime(
            event="terminal_output",
            message={"type": "output", "data": f"Executing: {command}"},
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

        return {"success": True}

    except Exception as e:
        error_msg = f"Error: {str(e)}\n"
        frappe.publish_realtime(
            event="terminal_output",
            # message={"type": "error", "data": f"Error: {str(e)}\n"},
            message={"type": "stderr", "data": error_msg},
            user=frappe.session.user,
        )
        return {"success": False, "error": str(e)}

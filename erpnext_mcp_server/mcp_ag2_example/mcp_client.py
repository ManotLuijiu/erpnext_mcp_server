"""
MCP Client Script - Simple terminal client for MCP
This script handles MCP protocol interaction in terminal environments
"""

import asyncio
import json
import os
import sys
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional

# Import MCP client libraries
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Prompt, Resource, Tool
from pydantic import AnyUrl, HttpUrl, ValidationError


class MCPClient:
    """Client for Model Context Protocol (MCP) servers"""

    def __init__(self):
        """Initialize the MCP client"""
        self.exit_stack = AsyncExitStack()
        self.session = None
        self.stdio = None
        self.write = None
        self.tools = []
        self.resources = []
        self.prompts = []

    async def connect(self, server_path: str):
        """Connect to an MCP server

        Args:
            server_path: Path to the server script or binary to execute
        """
        try:
            # Check if path is executable and exists
            if not os.path.exists(server_path):
                print(f"Error: Server not found at {server_path}")
                return False

            # Prepare server parameters
            server_params = StdioServerParameters(
                command=server_path, args=[], env=None
            )

            # Create stdio transport
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            self.stdio, self.write = stdio_transport

            # Create client session
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(self.stdio, self.write)
            )

            # Initialize the session
            await self.session.initialize()

            # Get available capabilities
            try:
                tool_response = await self.session.list_tools()
                self.tools = tool_response.tools
                print(f"Server provides {len(self.tools)} tools:")
                for tool in self.tools:
                    print(f"  - {tool.name}: {tool.description}")
            except Exception as e:
                print(f"Error listing tools: {str(e)}")

            try:
                resource_response = await self.session.list_resources()
                self.resources = resource_response.resources
                if self.resources:
                    print(f"Server provides {len(self.resources)} resources:")
                    for resource in self.resources:
                        print(f"  - {resource.name}: {resource.description}")
            except Exception as e:
                print(f"Error listing resources: {str(e)}")

            try:
                prompt_response = await self.session.list_prompts()
                self.prompts = prompt_response.prompts
                if self.prompts:
                    print(f"Server provides {len(self.prompts)} prompts:")
                    for prompt in self.prompts:
                        print(f"  - {prompt.name}: {prompt.description}")
            except Exception as e:
                print(f"Error listing prompts: {str(e)}")

            return True

        except Exception as e:
            print(f"Error connecting to MCP server: {str(e)}")
            return False

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = {}):
        """Call an MCP tool

        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool
        """
        if not self.session:
            print("Error: Not connected to an MCP server")
            return None

        try:
            # Find the tool
            tool = next((t for t in self.tools if t.name == tool_name), None)
            if not tool:
                print(f"Error: Tool '{tool_name}' not found")
                return None

            # Call the tool
            print(f"Calling tool: {tool_name}")
            if arguments:
                print(f"Arguments: {json.dumps(arguments, indent=2)}")

            response = await self.session.call_tool(tool_name, arguments or {})
            return response

        except Exception as e:
            print(f"Error calling tool: {str(e)}")
            return None

    async def read_resource(self, uri: str):
        """Read an MCP resource

        Args:
            uri: URI of the resource to read
        """
        if not self.session:
            print("Error: Not connected to an MCP server")
            return None

        try:
            validated_uri = AnyUrl(uri)
            response = await self.session.read_resource(validated_uri)
        except ValidationError as e:
            print(f"Error: Invalid URI format - {e}")
            return None
        except Exception as e:
            print(f"Error reading resource: {str(e)}")
            return None

        return response

    async def disconnect(self):
        """Disconnect from the MCP server"""
        if self.exit_stack:
            await self.exit_stack.aclose()
            self.session = None
            self.stdio = None
            self.write = None
            print("Disconnected from MCP server")


async def main():
    """Main entry point for the MCP client terminal"""
    client = MCPClient()

    # Check if server path was provided
    if len(sys.argv) < 2:
        print("Usage: mcp_client.py <path_to_mcp_server>")
        return

    server_path = sys.argv[1]

    # Connect to the server
    connected = await client.connect(server_path)
    if not connected:
        return

    # Interactive loop
    try:
        while True:
            command = input("mcp> ")

            if command.lower() in ("exit", "quit"):
                break

            elif command.lower() == "help":
                print("Available commands:")
                print("  tools - List available tools")
                print("  resources - List available resources")
                print("  prompts - List available prompts")
                print("  call <tool_name> [<json_args>] - Call a tool")
                print("  read <uri> - Read a resource")
                print("  exit/quit - Exit the client")

            elif command.lower() == "tools":
                for tool in client.tools:
                    print(f"{tool.name}: {tool.description}")
                    if hasattr(tool, "inputSchema") and tool.inputSchema:
                        print(
                            f"  Input schema: {json.dumps(tool.inputSchema, indent=2)}"
                        )

            elif command.lower() == "resources":
                for resource in client.resources:
                    print(f"{resource.name} ({resource.uri}): {resource.description}")

            elif command.lower() == "prompts":
                for prompt in client.prompts:
                    print(f"{prompt.name}: {prompt.description}")

            elif command.lower().startswith("call "):
                parts = command[5:].strip().split(" ", 1)
                tool_name = parts[0]
                args = {}

                if len(parts) > 1:
                    try:
                        args = json.loads(parts[1])
                    except json.JSONDecodeError:
                        print("Error: Arguments must be valid JSON")
                        continue

                response = await client.call_tool(tool_name, args)
                if response:
                    print("Response:")
                    if hasattr(response, "content"):
                        for content in response.content:
                            if hasattr(content, "text"):
                                if hasattr(content, "text"):
                                    if hasattr(content, "text"):
                                        print(content.text)  # type: ignore
                                    elif hasattr(content, "image"):
                                        print("[Image content]")
                                    elif hasattr(content, "embeddedResource"):
                                        print("[Embedded resource content]")
                                    else:
                                        print("[Unknown content type]")
                                elif hasattr(content, "image"):
                                    print("[Image content]")
                                elif hasattr(content, "embeddedResource"):
                                    print("[Embedded resource content]")
                                else:
                                    print("[Unknown content type]")
                            else:
                                print(content)
                    else:
                        print(response)

            elif command.lower().startswith("read "):
                uri = command[5:].strip()
                response = await client.read_resource(uri)
                if response:
                    print("Resource content:")
                    print(response)

            else:
                print(f"Unknown command: {command}")
                print("Type 'help' for available commands")

    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

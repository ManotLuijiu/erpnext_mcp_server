import asyncio
import sys
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from anthropic import Anthropic
from anthropic.types import (
    MessageParam,
    ToolParam,
    ContentBlockParam,
    TextBlockParam,
    ToolUseBlockParam,
)
from typing import Any, Dict, List, Union, cast, Optional as OptionalType
from dotenv import load_dotenv

load_dotenv()


class ERPNextMCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic()

    async def connect_to_server(self, server_script_path: str):
        """
        Connect to an ERPNext MCP Server

        Args:
            server_script_path (str): Path to the MCP Sever script
        """
        is_python = server_script_path.endswith(".py")

        if not is_python:
            raise ValueError("ERPNext MCP Server script must be a .py file")

        server_params = StdioServerParameters(
            command="python", args=[server_script_path], env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print(
            "\n🔌 Connected to ERPNext MCP server with tools:",
            [tool.name for tool in tools],
        )

    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available tools

        Args:
            query (str): _description_

        Returns:
            str: _description_

        Raises:
            ValueError: If not connected to an MCP server
        """
        if self.session is None:
            raise ValueError(
                "Not connected to an MCP server. Call connect_to_server() first."
            )
        # Create properly typed messages
        messages: List[MessageParam] = [{"role": "user", "content": query}]

        response = await self.session.list_tools()
        # Create properly typed tools
        available_tools: List[ToolParam] = [
            cast(
                ToolParam,
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema,
                },
            )
            for tool in response.tools
        ]

        # Initial Claude API call
        response = self.anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            messages=messages,
            tools=available_tools,
        )

        # Process response and handle tool calls
        final_text = []

        for content in response.content:
            if content.type == "text":
                final_text.append(content.text)
            elif content.type == "tool_use":
                tool_name = content.name
                tool_args = cast(Dict[str, Any], content.input)

                # Execute tool call
                result = await self.session.call_tool(tool_name, tool_args)
                final_text.append(
                    f"\n📋 [Calling tool {tool_name} with args {tool_args}]"
                )

                # Continue conversation with tool results
                # Create properly typed tool use block
                tool_use_block: ToolUseBlockParam = {
                    "type": "tool_use",
                    "id": f"tool_{tool_name}_{hash(str(tool_args))}",  # Generate a unique ID
                    "name": tool_name,
                    "input": tool_args,
                }

                messages.append({"role": "assistant", "content": [tool_use_block]})

                # Extract text content safely
                result_text = "No content returned"
                if result.content and len(result.content) > 0:
                    # Try to get text content if it exists
                    content_block = result.content[0]
                    if content_block.type == "text" and hasattr(content_block, "text"):
                        result_text = content_block.text

                messages.append({"role": "user", "content": result_text})

                # Get next response from Claude
                response = self.anthropic.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1000,
                    messages=messages,
                )

                # Extract text content safely
                if response.content and len(response.content) > 0:
                    content_block = response.content[0]
                    if content_block.type == "text" and hasattr(content_block, "text"):
                        final_text.append(content_block.text)
                    else:
                        final_text.append(f"[Content of type {content_block.type}]")
                else:
                    final_text.append("[No content returned]")

        return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\n🚀 ERPNext MCP Client Started!")
        print("💬 Type your queries or 'quit' to exit.")
        print("📝 Try queries like:")
        print("   - list all doctypes")
        print("   - show me info about Customer doctype")
        print("   - what fields are in Sales Invoice?")

        while True:
            try:
                query = input("\n💬 Query: ").strip()

                if query.lower() == "quit":
                    print("\n👋 Goodbye!")
                    break

                if not query:
                    continue

                print("\n🤔 Processing...")
                response = await self.process_query(query)
                print("\n✅ Response:")
                print(response)

            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()


async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        print("Example: python client.py mcp_erpnext/local_server.py")
        sys.exit(1)

    client = ERPNextMCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

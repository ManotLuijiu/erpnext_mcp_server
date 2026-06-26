"""
Entry point for running MCP server via:
  python -m erpnext_mcp_server.mcp.server

Or directly:
  python -m erpnext_mcp_server.mcp
"""

import asyncio
import os
import sys

# Add bench paths
BENCH_PATH = os.getenv("BENCH_PATH", "/home/frappe/frappe-bench")
sys.path.insert(0, os.path.join(BENCH_PATH, "apps", "frappe"))
sys.path.insert(0, BENCH_PATH)

# Change to bench directory for relative path resolution
os.chdir(BENCH_PATH)


async def main():
    """Main entry point - runs the MCP stdio server."""
    # Create initialization options
    from mcp.server import InitializationOptions
    from mcp.server.stdio import stdio_server
    from mcp.types import ServerCapabilities, ToolsCapability

    # Import the server module
    from erpnext_mcp_server.mcp.server import server

    options = InitializationOptions(
        server_name="erpnext-mcp-server",
        server_version="1.0.0",
        capabilities=ServerCapabilities(tools=ToolsCapability()),
    )

    # Run stdio server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream=read_stream,
            write_stream=write_stream,
            initialization_options=options,
        )


if __name__ == "__main__":
    asyncio.run(main())

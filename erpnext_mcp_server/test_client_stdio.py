# erpnext_mcp_server/test_client_stdio.py (fixed version)
import asyncio
import subprocess
import json
import sys
import time


async def test_mcp_stdio():
    """Test MCP server using stdio"""

    # Start the server process
    print("Starting MCP server...")
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "erpnext_mcp_server.mcp.local_server",
        "--site",
        "moo.localhost",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    # Wait a moment for the server to start
    await asyncio.sleep(1)

    # Check if the process is still running
    if process.returncode is not None:
        print(f"Server process exited with code: {process.returncode}")
        stderr = await process.stderr.read()
        print(f"Error output: {stderr.decode()}")
        return

    try:
        # Test 1: Initialize
        print("\n=== Initializing ===")
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        }

        print(f"Sending: {json.dumps(init_request)}")
        process.stdin.write((json.dumps(init_request) + "\n").encode())
        await process.stdin.drain()

        # Try to read response with timeout
        try:
            response = await asyncio.wait_for(process.stdout.readline(), timeout=5)
            if response:
                print(f"Init response: {response.decode().strip()}")
            else:
                print("No response received")
                # Check for errors
                stderr = await process.stderr.read()
                if stderr:
                    print(f"Server error: {stderr.decode()}")
                return
        except asyncio.TimeoutError:
            print("Timeout waiting for response")
            return

        # Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        }

        print(f"\nSending: {json.dumps(initialized_notification)}")
        process.stdin.write((json.dumps(initialized_notification) + "\n").encode())
        await process.stdin.drain()

        # Test 2: List tools
        print("\n=== Listing Tools ===")
        list_tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        }

        print(f"Sending: {json.dumps(list_tools_request)}")
        process.stdin.write((json.dumps(list_tools_request) + "\n").encode())
        await process.stdin.drain()

        try:
            response = await asyncio.wait_for(process.stdout.readline(), timeout=5)
            if response:
                print(f"List tools response: {response.decode().strip()}")
        except asyncio.TimeoutError:
            print("Timeout waiting for response")

        # Test 3: Call tool
        print("\n=== Calling Tool ===")
        call_tool_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "get_customer_info",
                "arguments": {"customer_name": "_Test Customer"},
            },
        }

        print(f"Sending: {json.dumps(call_tool_request)}")
        process.stdin.write((json.dumps(call_tool_request) + "\n").encode())
        await process.stdin.drain()

        try:
            response = await asyncio.wait_for(process.stdout.readline(), timeout=5)
            if response:
                print(f"Call tool response: {response.decode().strip()}")
        except asyncio.TimeoutError:
            print("Timeout waiting for response")

    except Exception as e:
        print(f"Error during test: {e}")
        # Try to get more error info
        stderr = await process.stderr.read()
        if stderr:
            print(f"Server stderr: {stderr.decode()}")

    finally:
        # Clean up
        print("\nCleaning up...")
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=5)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()


if __name__ == "__main__":
    asyncio.run(test_mcp_stdio())

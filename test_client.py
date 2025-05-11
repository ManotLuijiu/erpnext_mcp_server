import asyncio
import httpx
import json


async def test_mcp_client():
    """Simple client to test local MCP server"""

    # Test connection
    base_url = "http://localhost:8100/mcp"

    try:
        # Test 1: List tools
        print("=== Testing List Tools ===")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                base_url,
                json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
        print("Response:", response.json())

        # Test 2: Call tool
        async with httpx.AsyncClient() as client:
            response = await client.post(
                base_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "get_customer_info",
                        "arguments": {
                            "customer_name": "CUST-001"  # Replace with actual customer
                        },
                    },
                },
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
        print("Response:", response.json())
        print("Response:", response.json())

    except Exception as e:
        print(f"Error: {e}")


# Simple test runner
async def main():
    """Run tests"""
    await test_mcp_client()


if __name__ == "__main__":
    asyncio.run(main())

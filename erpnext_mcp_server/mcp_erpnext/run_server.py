import sys
from erpnext_mcp_server.mcp_erpnext.tools.list_doctypes import mcp

if __name__ == "__main__":
    # Run the server with stdio transport by default
    transport = sys.argv[1] if len(sys.argv) > 1 else 'stdio'
    mcp.run(transport=transport)
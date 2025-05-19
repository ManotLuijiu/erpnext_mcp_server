import './mcp_terminal/socketio_client';
frappe.provide('frappe.chat_mcp');

/**
 * MCP Client for Chat Integration
 * This client allows the chat bot to communicate with the MCP server
 */
class ChatMCPClient {
  constructor() {
    this.mcpServerRunning = false;
    this.mcp_base_url = null;
    this.initMCPStatus();
  }

  async initMCPStatus() {
    try {
      // First check if MCP info is available in boot
      if (frappe.boot.mcp_server) {
        this.mcpServerRunning = frappe.boot.mcp_server.is_running;

        // Set the base URL based on transport type
        if (this.mcpServerRunning) {
          const transport = frappe.boot.mcp_server.transport;
          const port = frappe.boot.mcp_server.port || 8000;

          console.log('port', port);

          if (transport === 'sse') {
            // For SSE transport, use regular HTTP endpoint
            this.mcp_base_url = frappe.urllib.get_base_url() + '/api/mcp';
          } else {
            // For stdio transport, we need to use our proxy
            this.mcp_base_url =
              frappe.urllib.get_base_url() +
              '/api/method/erpnext_mcp_server.erpnext_mcp_server.api.mcp_proxy.query';
          }
        }

        return;
      }

      // If not in boot, check status via API
      // const response = await this.checkMCPServerStatus();
      // this.mcpServerRunning = response.is_running;

      // Set the base URL based on transport type
      if (this.mcpServerRunning) {
        if (response.transport === 'sse') {
          // For SSE transport, use regular HTTP endpoint
          this.mcp_base_url = frappe.urllib.get_base_url() + '/api/mcp';
        } else {
          // For stdio transport, we need to use our proxy
          this.mcp_base_url =
            frappe.urllib.get_base_url() +
            '/api/method/erpnext_mcp_server.erpnext_mcp_server.api.mcp_proxy.query';
        }
      }
    } catch (error) {
      console.error('Failed to check MCP server status:', error);
      this.mcpServerRunning = false;
    }
  }

  // async checkMCPServerStatus() {
  //     // Check if MCP server is running
  //     try {
  //         const response = await frappe.call({
  //             method: "erpnext_mcp_server.erpnext_mcp_server.api.mcp_server.get_status",
  //             async: true
  //         });

  //         return response.message || { is_running: false, status: 'Unknown' };
  //     } catch (error) {
  //         console.error("Error checking MCP status:", error);
  //         return { is_running: false, status: 'Error' };
  //     }
  // }

  async startMCPServer() {
    try {
      const response = await frappe.call({
        method:
          'erpnext_mcp_server.erpnext_mcp_server.api.mcp_server.start_server',
        async: true,
      });

      if (response.message && response.message.status === 'success') {
        // Wait a moment for the server to start
        await new Promise((resolve) => setTimeout(resolve, 2000));

        // Check status again
        await this.initMCPStatus();
        return { success: this.mcpServerRunning };
      }

      return {
        success: false,
        message: response.message?.message || 'Failed to start MCP server',
      };
    } catch (error) {
      console.error('Error starting MCP server:', error);
      return { success: false, message: error.message || 'Unknown error' };
    }
  }

  async stopMCPServer() {
    try {
      const response = await frappe.call({
        method:
          'erpnext_mcp_server.erpnext_mcp_server.api.mcp_server.stop_server',
        async: true,
      });

      if (response.message && response.message.status === 'success') {
        this.mcpServerRunning = false;
        return { success: true };
      }

      return {
        success: false,
        message: response.message?.message || 'Failed to stop MCP server',
      };
    } catch (error) {
      console.error('Error stopping MCP server:', error);
      return { success: false, message: error.message || 'Unknown error' };
    }
  }

  async queryMCP(query, context = {}) {
    if (!this.mcpServerRunning || !this.mcp_base_url) {
      return {
        error: 'MCP server is not running. Please start the server first.',
      };
    }

    try {
      // Format the query for MCP
      const payload = {
        query: query,
        context: context,
      };

      // Send request to the MCP server through our proxy
      const response = await frappe.call({
        method: 'erpnext_mcp_server.erpnext_mcp_server.api.mcp_proxy.query',
        args: payload,
        async: true,
      });

      return response.message || { error: 'No response from MCP server' };
    } catch (error) {
      console.error('Error querying MCP:', error);
      return { error: error.message || 'Failed to query MCP server' };
    }
  }

  isRunning() {
    return this.mcpServerRunning;
  }
}

// Create a global instance for reuse
frappe.chat_mcp = new ChatMCPClient();

// Keep the MCP status updated
$(document).ready(function () {
  // Update MCP status every 30 seconds
  setInterval(function () {
    if (frappe.chat_mcp) {
      frappe.chat_mcp.initMCPStatus();
    }
  }, 30000);
});

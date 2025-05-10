(() => {
  // ../erpnext_mcp_server/erpnext_mcp_server/public/js/erpnext_mcp_server.bundle.js
  frappe.provide("frappe.chat_mcp");
  var ChatMCPClient = class {
    constructor() {
      this.mcpServerRunning = false;
      this.mcp_base_url = null;
      this.initMCPStatus();
    }
    async initMCPStatus() {
      try {
        if (frappe.boot.mcp_server) {
          this.mcpServerRunning = frappe.boot.mcp_server.is_running;
          if (this.mcpServerRunning) {
            const transport = frappe.boot.mcp_server.transport;
            const port = frappe.boot.mcp_server.port || 8e3;
            if (transport === "sse") {
              this.mcp_base_url = frappe.urllib.get_base_url() + "/api/mcp";
            } else {
              this.mcp_base_url = frappe.urllib.get_base_url() + "/api/method/erpnext_mcp_server.erpnext_mcp_server.api.mcp_proxy.query";
            }
          }
          return;
        }
        const response = await this.checkMCPServerStatus();
        this.mcpServerRunning = response.is_running;
        if (this.mcpServerRunning) {
          if (response.transport === "sse") {
            this.mcp_base_url = frappe.urllib.get_base_url() + "/api/mcp";
          } else {
            this.mcp_base_url = frappe.urllib.get_base_url() + "/api/method/erpnext_mcp_server.erpnext_mcp_server.api.mcp_proxy.query";
          }
        }
      } catch (error) {
        console.error("Failed to check MCP server status:", error);
        this.mcpServerRunning = false;
      }
    }
    async checkMCPServerStatus() {
      try {
        const response = await frappe.call({
          method: "erpnext_mcp_server.erpnext_mcp_server.api.mcp_server.get_status",
          async: true
        });
        return response.message || { is_running: false, status: "Unknown" };
      } catch (error) {
        console.error("Error checking MCP status:", error);
        return { is_running: false, status: "Error" };
      }
    }
    async startMCPServer() {
      var _a;
      try {
        const response = await frappe.call({
          method: "erpnext_mcp_server.erpnext_mcp_server.api.mcp_server.start_server",
          async: true
        });
        if (response.message && response.message.status === "success") {
          await new Promise((resolve) => setTimeout(resolve, 2e3));
          await this.initMCPStatus();
          return { success: this.mcpServerRunning };
        }
        return { success: false, message: ((_a = response.message) == null ? void 0 : _a.message) || "Failed to start MCP server" };
      } catch (error) {
        console.error("Error starting MCP server:", error);
        return { success: false, message: error.message || "Unknown error" };
      }
    }
    async stopMCPServer() {
      var _a;
      try {
        const response = await frappe.call({
          method: "erpnext_mcp_server.erpnext_mcp_server.api.mcp_server.stop_server",
          async: true
        });
        if (response.message && response.message.status === "success") {
          this.mcpServerRunning = false;
          return { success: true };
        }
        return { success: false, message: ((_a = response.message) == null ? void 0 : _a.message) || "Failed to stop MCP server" };
      } catch (error) {
        console.error("Error stopping MCP server:", error);
        return { success: false, message: error.message || "Unknown error" };
      }
    }
    async queryMCP(query, context = {}) {
      if (!this.mcpServerRunning || !this.mcp_base_url) {
        return { error: "MCP server is not running. Please start the server first." };
      }
      try {
        const payload = {
          query,
          context
        };
        const response = await frappe.call({
          method: "erpnext_mcp_server.erpnext_mcp_server.api.mcp_proxy.query",
          args: payload,
          async: true
        });
        return response.message || { error: "No response from MCP server" };
      } catch (error) {
        console.error("Error querying MCP:", error);
        return { error: error.message || "Failed to query MCP server" };
      }
    }
    isRunning() {
      return this.mcpServerRunning;
    }
  };
  frappe.chat_mcp = new ChatMCPClient();
  $(document).ready(function() {
    setInterval(function() {
      if (frappe.chat_mcp) {
        frappe.chat_mcp.initMCPStatus();
      }
    }, 3e4);
  });
})();
//# sourceMappingURL=erpnext_mcp_server.bundle.YVGBBX73.js.map

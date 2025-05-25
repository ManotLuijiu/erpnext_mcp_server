frappe.pages['mcp-chatbot'].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: __('ERPNext MCP Chatbot'),
    single_column: true,
  });

  // Create container
  const container = $(`
    <div class="mcp-terminal-container">
      <div id="mcp-terminal-app" style="height: calc(100vh - 150px); min-height: 600px;">
        <div id="terminal" style="height: 100%; width: 100%;"></div>
      </div>
    </div>
  `);

  page.main.append(container);

  // Initialize terminal
  frappe.require('mcp_chatbot.bundle.js').then(() => {
    window.initMCPTerminal('mcp-terminal-app').catch((error) => {
      container.html(`
        <div class="error-message">
          Failed to load terminal: ${error.message}
          <button onclick="location.reload()">Retry</button>
        </div>
      `);
    });
  });
};

frappe.pages['mcp-terminal'].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: __('MCP Terminal'),
    single_column: true,
  });

  // Add the terminal class to the wrapper for styling
  $(wrapper).addClass('mcp-terminal-page');

  // Initialize the terminal
  frappe.require('mcp_terminal.bundle.jsx', () => {
    frappe.mcp_terminal = new frappe.ui.McpTerminal({
      page: page,
      wrapper: page.body,
    });
  });
};

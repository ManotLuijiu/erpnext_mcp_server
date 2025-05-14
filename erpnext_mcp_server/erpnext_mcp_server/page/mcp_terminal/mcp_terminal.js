frappe.pages['mcp-terminal'].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: __('MCP Terminal'),
    single_column: true,
  });

  // Set indicator to show beta status
  page.set_indicator('Beta', 'orange');

  // Add page actions
  page.add_menu_item('Settings', function () {
    frappe.set_route('Form', 'MCP Settings');
  });

  page.add_menu_item('Clear Token', function () {
    localStorage.removeItem('mcp_token');
    localStorage.removeItem('mcp_token_data');
    frappe.show_alert(
      {
        message: __('MCP token cleared'),
        indicator: 'blue',
      },
      3,
    );
  });

  page.add_menu_item('View Logs', function () {
    frappe.set_route('List', 'MCP Terminal Log');
  });

  // Create a global connect function to be used by the button
  frappe.mcp_terminal_connect = function () {
    if (frappe.mcp_terminal?.connect) {
      frappe.mcp_terminal.connect();

      // Update button UI
      $('.mcp-connect-btn')
        .removeClass('btn-primary')
        .addClass('btn-default')
        .html(__('Connecting...'));
    }
  };

  // Load CSS styles
  // frappe.require(['erpnext_mcp_server/css/mcp_terminal.css']);

  // Add help section
  const helpHTML = `
    <div class="mcp-terminal-help mb-4">
      <div class="alert alert-info">
        <div class="d-flex justify-content-between align-items-center">
           <div class="flex-grow-1">
            <h5 class="m-0">${__('MCP Terminal')}</h5>
            <p class="m-0">${__('Connect to your MCP Server and run commands directly from your browser')}</p>
          </div>
          <div class="ml-3">
            <button class="btn btn-primary btn-sm mcp-connect-btn" onclick="frappe.mcp_terminal_connect()">
              ${__('Connect MCP')}
            </button>
          </div>
        </div>
      </div>
    </div>
  `;
  $(page.body).prepend(helpHTML);

  // Add the terminal class to the wrapper for styling
  // $(wrapper).addClass('mcp-terminal-page')

  // Initialize the terminal
  frappe.require('mcp_terminal.bundle.jsx', () => {
    frappe.mcp_terminal = erpnext_mcp_server.mcp_terminal.create(page.body);
    // frappe.mcp_terminal = new frappe.ui.McpTerminal({
    //   page: page,
    //   wrapper: page.body,
    // })
  });
};

// frappe.pages['mcp-terminal'].on_page_hide = function () {
//   // Optionally destroy the terminal instance when the page is hidden
//   if (frappe.pages['mcp_terminal'].mcp_terminal) {
//     frappe.pages['mcp_terminal'].mcp_terminal.destroy();
//   }
// };

frappe.pages['mcp-terminal'].on_page_hide = function () {
  // Optionally destroy the terminal instance when the page is hidden
  if (frappe.mcp_terminal) {
    frappe.mcp_terminal.destroy();
  }
};

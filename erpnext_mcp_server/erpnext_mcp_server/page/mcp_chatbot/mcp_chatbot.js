frappe.pages['mcp-chatbot'].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: __('ERPNext MCP Chatbot'),
    single_column: true,
  });

  // Set page icon
  page.main.addClass('mcp-terminal-page');

  // Create the container for Vue app
  const container = $(`
			<div class="mcp-terminal-container">
			<div id="mcp-terminal-app" style="height: calc(100vh - 150px); min-height: 600px;">
				<div class="loading-container" style="
				display: flex; 
				justify-content: center; 
				align-items: center; 
				height: 100%; 
				flex-direction: column;
				color: #8D99AE;
				">
				<div class="spinner" style="
					width: 40px; 
					height: 40px; 
					border: 4px solid #f3f3f3; 
					border-top: 4px solid #5e72e4; 
					border-radius: 50%; 
					animation: spin 1s linear infinite;
					margin-bottom: 20px;
				"></div>
				<div>Loading MCP Terminal...</div>
				</div>
			</div>
			</div>
		`);

  // Add loading spinner animation
  const style = document.createElement('style');
  style.textContent = `
	 @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }
    
    .mcp-terminal-page .layout-main-section {
      padding: 0;
      margin: 0;
    }
    
    .mcp-terminal-container {
      height: 100%;
      width: 100%;
      background: #1e1e1e;
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
  `;

  document.head.appendChild(style);

  // Append container to page
  page.main.append(container);

  // Initialize the Vue.js application
  const initializeApp = async () => {
    try {
      // Wait for frappe to be ready if needed
      if (!frappe.session.user) {
        await new Promise((resolve) => {
          frappe.ready(() => resolve());
        });
      }

      // Load the MCP Terminal bundle
      const { initMCPTerminal } = await import(
        '/assets/erpnext_mcp_server/js/mcp_terminal/mcp_terminal.bundle.js'
      );

      // Initialize the terminal
      await initMCPTerminal('mcp-terminal-app');
    } catch (error) {
      console.error('Failed to initialize MCP Terminal:', error);

      // Show error message
      const errorContainer = $(`
        <div style="
          display: flex; 
          justify-content: center; 
          align-items: center; 
          height: 100%; 
          flex-direction: column;
          color: #e74c3c;
          text-align: center;
          padding: 20px;
        ">
          <div style="font-size: 48px; margin-bottom: 20px;">⚠️</div>
          <div style="font-size: 18px; margin-bottom: 10px;">Failed to Load Terminal</div>
          <div style="font-size: 14px; color: #7f8c8d; max-width: 400px;">
            ${error.message || 'Unknown error occurred while loading the MCP Terminal.'}
          </div>
          <button class="btn btn-primary btn-sm" onclick="location.reload()" style="margin-top: 20px;">
            Retry
          </button>
        </div>
      `);

      container.find('#mcp-terminal-app').html(errorContainer);
    }
  };

  // Initialize when page loads
  setTimeout(initializeApp, 100);

  // Handle page refresh/cleanup
  page.on_page_show = function () {
    // Refresh terminal if needed
    console.log('MCP Terminal page shown');
  };

  // Cleanup when leaving page
  $(window).on('beforeunload', function () {
    // Any cleanup needed
    console.log('MCP Terminal page unloading');
  });
};

// Page refresh handler
frappe.pages['mcp-terminal'].refresh = function () {
  // Handle page refresh if needed
  console.log('MCP Terminal page refreshed');
};

frappe.pages['mcp-chatbot'].on_page_show = function (wrapper) {
  load_desk_page(wrapper);
};

function load_desk_page(wrapper) {
  let $parent = $(wrapper).find('.layout-main-section');
  $parent.empty();

  frappe.require('mcp_chatbot.bundle.js').then(() => {
    frappe.mcp_chatbot = new frappe.ui.McpChatbot({
      wrapper: $parent,
      page: wrapper.page,
    });
  });
}

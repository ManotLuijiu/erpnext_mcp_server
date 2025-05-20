frappe.pages['mcp-terminal'].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: __('MCP Terminal'),
    single_column: true,
  });

  const socketTransport = frappe.realtime.socket.io?.engine?.transport?.name;
  console.log('socketTransport', socketTransport);

  // Set indicator to show beta status
  page.set_indicator('Beta', 'orange');

  // const terminalIcon = `
  // <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16"><path d="M0 2.75C0 1.784.784 1 1.75 1h12.5c.966 0 1.75.784 1.75 1.75v10.5A1.75 1.75 0 0 1 14.25 15H1.75A1.75 1.75 0 0 1 0 13.25Zm1.75-.25a.25.25 0 0 0-.25.25v10.5c0 .138.112.25.25.25h12.5a.25.25 0 0 0 .25-.25V2.75a.25.25 0 0 0-.25-.25ZM7.25 8a.749.749 0 0 1-.22.53l-2.25 2.25a.749.749 0 0 1-1.275-.326.749.749 0 0 1 .215-.734L5.44 8 3.72 6.28a.749.749 0 0 1 .326-1.275.749.749 0 0 1 .734.215l2.25 2.25c.141.14.22.331.22.53Zm1.5 1.5h3a.75.75 0 0 1 0 1.5h-3a.75.75 0 0 1 0-1.5Z"></path></svg>
  // `;

  // Add connect button
  page
    .set_primary_action(
      __('Connect MCP'),
      function () {
        // Toggle connect/disconnect
        const $btn = $('.mcp-connect-btn');

        if ($btn.hasClass('btn-success')) {
          // Currently connected, disconnect
          if (window.TerminalApp && window.TerminalApp.disconnectFromServer) {
            window.TerminalApp.disconnectFromServer();
          }
        } else {
          // Currently disconnected, connect
          if (window.TerminalApp && window.TerminalApp.connectToServer) {
            window.TerminalApp.connectToServer();
          }
        }
      },
      'integration'
    )
    .addClass('mcp-connect-btn');

  const $pageActions = $(wrapper).find('.page-actions');
  console.log($pageActions);

  // Create a global connect function to be used by the button
  // frappe.mcp_terminal_connect = function () {
  //   if (frappe.mcp_terminal?.connect) {
  //     frappe.mcp_terminal.connect();

  //     // Update button UI
  //     $('.mcp-connect-btn')
  //       .prop('disabled', true)
  //       .html(
  //         `<i class="fa fa-spinner fa-spin mr-1"></i> ${__('Connecting...')}`
  //       );
  //   }
  // };

  // Add SVG terminal icon to the page header
  // try {
  //   // Option 1: Try to add to standard Frappe page actions
  //   const $pageActions = $(wrapper).find('.page-actions');
  //   if ($pageActions.length > 0) {
  //     const svgHtml = `
  //       <div class="page-icon-group">
  //         <div class="page-icon">
  //           <img src="/assets/erpnext_mcp_server/images/icons/terminal-svgrepo-com.svg"
  //                alt="Terminal Icon"
  //                style="width: 24px; height: 24px; margin-right: 8px;">
  //         </div>
  //       </div>
  //     `;
  //     $pageActions.prepend(svgHtml);
  //   }
  //   // Option 2: If page actions not found, add to page head
  //   else {
  //     const $pageHead = $(wrapper).find('.page-head');
  //     if ($pageHead.length > 0) {
  //       const svgHtml = `
  //         <div class="d-flex align-items-center mr-2" style="margin-top: 3px;">
  //           <img src="/assets/erpnext_mcp_server/images/icons/terminal-svgrepo-com.svg"
  //                alt="Terminal Icon"
  //                style="width: 24px; height: 24px;">
  //         </div>
  //       `;
  //       $pageHead.prepend(svgHtml);
  //     }
  //     // Option 3: Last resort, add to title
  //     else {
  //       const $title = $(wrapper).find('.title-text');
  //       if ($title.length > 0) {
  //         const svgHtml = `
  //           <img src="/assets/erpnext_mcp_server/images/icons/terminal-svgrepo-com.svg"
  //                alt="Terminal Icon"
  //                style="width: 18px; height: 18px; margin-right: 8px; vertical-align: text-bottom;">
  //         `;
  //         $title.prepend(svgHtml);
  //       }
  //     }
  //   }
  // } catch (error) {
  //   console.warn('Failed to add SVG icon to page:', error);
  //   // Non-critical error, continue with the rest of the page setup
  // }

  // Add page menu items
  // page.add_menu_item('View Logs', function () {
  //   frappe.set_route('List', 'MCP Terminal Log');
  // });

  // Add help menu with keyboard shortcuts
  page.add_menu_item(__('Keyboard Shortcuts'), function () {
    frappe.msgprint(
      __(`
        <h4>Terminal Keyboard Shortcuts</h4>
        <ul>
          <li><strong>Ctrl+C</strong>: Interrupt current process</li>
          <li><strong>Ctrl+D</strong>: Send EOF</li>
          <li><strong>Ctrl+L</strong>: Clear screen</li>
          <li><strong>Up/Down arrows</strong>: Navigate command history</li>
          <li><strong>Ctrl+A</strong>: Move cursor to beginning of line</li>
          <li><strong>Ctrl+E</strong>: Move cursor to end of line</li>
          <li><strong>Ctrl+K</strong>: Delete from cursor to end of line</li>
          <li><strong>Ctrl+U</strong>: Delete from start of line to cursor</li>
        </ul>
      `),
      __('Terminal Keyboard Shortcuts')
    );
  });

  // Create the terminal container in the page
  // $(
  //   '<div id="mcp-terminal-react-root" class="mcp-terminal-container"></div>'
  // ).appendTo(page.main);
  $('<div id="mcp-terminal-react-root"></div>').appendTo(page.main);

  // Add settings menu
  page.add_menu_item(__('Terminal Settings'), function () {
    // Show a dialog with terminal settings
    let d = new frappe.ui.Dialog({
      title: __('Terminal Settings'),
      fields: [
        {
          label: __('Font Size'),
          fieldname: 'font_size',
          fieldtype: 'Int',
          default: 14,
          description: __('Terminal font size in pixels'),
        },
        {
          label: __('Theme'),
          fieldname: 'theme',
          fieldtype: 'Select',
          options: [
            { value: 'dark', label: __('Dark (Tokyo Night)') },
            { value: 'light', label: __('Light') },
          ],
          default: 'dark',
        },
      ],
      primary_action_label: __('Apply'),
      primary_action: function (values) {
        // Apply settings to terminal
        if (window.TerminalApp && window.TerminalApp.applySettings) {
          window.TerminalApp.applySettings(values);
        }
        d.hide();
      },
    });
    d.show();
  });

  // Create the terminal container in the page
  // $(frappe.render_template('mcp_terminal', {})).appendTo(page.main);

  // Add help section with connect button and SVG icon
  const helpHTML = `
    <div class="mcp-terminal-help mb-4">
      <div class="alert">
        <div class="d-flex justify-content-between align-items-center">
          <div class="flex-grow-1 d-flex">
            <img src="/assets/erpnext_mcp_server/images/icons/terminal-svgrepo-com.svg" 
                 alt="Terminal Icon" 
                 style="width: 24px; height: 24px; margin-right: 10px;">
            <div>
              <h5 class="m-0">${__('MCP Terminal')}</h5>
              <p class="m-0">${__('Connect to your MCP Server and run commands directly from your browser')}</p>
            </div>
          </div>
          <div class="ml-3">
            <button class="btn btn-primary btn-sm mcp-connect-btn">
              <i class="fa fa-plug mr-1"></i> ${__('Connect MCP')}
            </button>
          </div>
        </div>
      </div>
    </div>
  `;
  $(page.body).prepend(helpHTML);

  // Initialize socket connection
  if (!frappe.realtime.socket || !frappe.realtime.socket.connected) {
    frappe.realtime.connect();
  }

  // Initialize the terminal
  frappe.require('mcp_terminal.bundle.jsx', () => {
    // Create a container div and append it to page.body
    const terminalContainer = $(
      '<div class="mcp-terminal-container"></div>'
    ).appendTo(page.body);
    // Pass the DOM element, not the jQuery object
    frappe.mcp_terminal = erpnext_mcp_server.mcp_terminal.create(
      terminalContainer[0]
    );
    console.log('MCP Terminal bundle loaded');
  });
};

frappe.pages['mcp-terminal'].on_page_show = function () {
  // When page is shown, focus the terminal
  if (window.TerminalApp && window.TerminalApp.focusTerminal) {
    window.TerminalApp.focusTerminal();
  }
};

frappe.pages['mcp-terminal'].on_page_hide = function () {
  // Destroy the terminal instance when the page is hidden
  if (frappe.mcp_terminal) {
    frappe.mcp_terminal.destroy();
  }
};

import * as React from 'react';
import App from './App';
import { createRoot } from 'react-dom/client';

// Add CSS for terminal
// frappe.require_css('/assets/erpnext_mcp_server/css/xterm.css');
// frappe.require_css('/assets/erpnext_mcp_server/css/terminal.css');

class McpTerminal {
  constructor({ page, wrapper }) {
    this.$wrapper = $(wrapper);
    this.page = page;

    this.init();
  }

  init() {
    this.setup_page_actions();
    this.setup_app();
    // Load xterm FitAddon before setting up the app
    // frappe.require('/assets/erpnext_mcp_server/js/xterm-addon-fit.js', () => {
    //   this.setup_app();
    // });
  }

  setup_page_actions() {
    // Set up help action
    this.page.add_menu_item('Documentation', () => {
      window.open('https://modelcontextprotocol.io/introduction', '_blank');
    });
  }

  setup_app() {
    // create and mount the react app
    const root = createRoot(this.$wrapper.get(0));
    root.render(<App />);
    this.$mcp_terminal = root;
  }
}

frappe.provide('frappe.ui');
frappe.ui.McpTerminal = McpTerminal;
export default McpTerminal;

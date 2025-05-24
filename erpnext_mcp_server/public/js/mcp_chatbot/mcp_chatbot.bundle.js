import { createApp } from 'vue';
import { createRouter, createWebHashHistory } from 'vue-router';
import io from 'socket.io-client';
import App from './App.vue';

// Load xterm.js and addons
const loadXterm = async () => {
  // Load xterm.js CSS
  const xtermCSS = document.createElement('link');
  xtermCSS.rel = 'stylesheet';
  xtermCSS.href = '/assets/node_modules/xterm/css/xterm.css';
  document.head.appendChild(xtermCSS);

  // Load xterm.js scripts if not already loaded
  if (!window.Terminal) {
    await import('/assets/node_modules/xterm/lib/xterm.js');
  }

  if (!window.FitAddon) {
    await import('/assets/node_modules/xterm-addon-fit/lib/xterm-addon-fit.js');
  }
};

// Router configuration
const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/',
      name: 'Terminal',
      component: App,
    },
  ],
});

// Initialize the application
export const initMCPTerminal = async (containerId) => {
  try {
    // Load xterm.js dependencies
    await loadXterm();

    // Create Vue app
    const app = createApp(App);

    // Use router
    app.use(router);

    // Global properties
    app.config.globalProperties.$frappe = window.frappe;
    app.config.globalProperties.$io = io;

    // Error handler
    app.config.errorHandler = (err, vm, info) => {
      console.error('Vue Error:', err);
      console.error('Component:', vm);
      console.error('Info:', info);
    };

    // Mount the app
    const container = document.getElementById(containerId);
    if (!container) {
      throw new Error(`Container with ID '${containerId}' not found`);
    }

    app.mount(container);

    console.log('MCP Terminal Vue app initialized successfully');
    return app;
  } catch (error) {
    console.error('Failed to initialize MCP Terminal:', error);
    throw error;
  }
};

// Auto-initialize if container exists
document.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById('mcp-terminal-app');
  if (container) {
    initMCPTerminal('mcp-terminal-app');
  }
});

// Export for manual initialization
window.initMCPTerminal = initMCPTerminal;

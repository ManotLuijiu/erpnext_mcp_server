import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
// import './socketio_client';

// Ensure the component is available in the global namespace
window.erpnext_mcp_server = window.erpnext_mcp_server || {};
window.erpnext_mcp_server.mcp_terminal = {
  // Initialize the terminal when called by Frappe
  create: function (container) {
    // Create a React root
    const root = createRoot(container);

    console.log('root', root);

    // Create a reference to the App component
    const appRef = React.createRef();

    console.log('appRef', appRef);

    // Render the App component
    root.render(<App ref={appRef} />);

    // Expose methods to the global scope for Frappe to use
    window.TerminalApp = {
      connectToServer: function () {
        if (appRef.current && appRef.current.connectToServer) {
          return appRef.current.connectToServer();
        }
        return false;
      },

      disconnectFromServer: function () {
        if (appRef.current && appRef.current.disconnectFromServer) {
          return appRef.current.disconnectFromServer();
        }
        return false;
      },

      focusTerminal: function () {
        if (appRef.current && appRef.current.focusTerminal) {
          appRef.current.focusTerminal();
        }
      },

      applySettings: function (settings) {
        if (appRef.current && appRef.current.applySettings) {
          appRef.current.applySettings(settings);
        }
      },

      getConnectionStatus: function () {
        if (appRef.current && appRef.current.getConnectionStatus) {
          return appRef.current.getConnectionStatus();
        }
        return { isConnected: false, status: 'unknown' };
      },
    };

    return appRef.current;
  },
};

// Auto-initialize if the container exists
// (function () {
//   document.addEventListener('DOMContentLoaded', function () {
//     // Check if the container exists
//     const container = document.getElementById('mcp-terminal-react-root');
//     console.log('container', container);
//     if (container) {
//       console.log('Auto-initializing MCP Terminal');
//       window.erpnext_mcp_server.mcp_terminal.create(container);
//     }
//   });
// })();

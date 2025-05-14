import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';

// This file is the entry point for Webpack
// It will render our React app into the designated container

frappe.provide('erpnext_mcp_server.mcp_terminal');

erpnext_mcp_server.mcp_terminal.create = function(wrapper) {
  // Ensure we have a DOM element, not a jQuery object
  const containerElement = wrapper instanceof jQuery ? wrapper[0] : wrapper;

  // Create a container for our React app
  const container = document.createElement('div');
  container.className = 'mcp-terminal-page-wrapper';

  // Append to the container element
  if (containerElement && containerElement.appendChild) {
    containerElement.appendChild(container);
  } else {
    console.error('Invalid wrapper element provided to mcp_terminal.create');
    // Fallback: try to append to body if wrapper is invalid
    document.body.appendChild(container);
  }
  
  // Create the React app and keep a reference to it
  const root = createRoot(container);
  // Create a ref that we'll attach to the App component
  let appInstance = null;
  
  // Define a ref callback function to capture the App component instance
  const setAppRef = (ref) => {
    appInstance = ref;
  };
  
  // Render our React app with the ref callback
  root.render(<App ref={setAppRef} />);
  
  // Return methods that can be called from outside
  return {
    destroy: () => {
      try {
        // Disconnect if connected
        if (appInstance) {
          appInstance.disconnectFromServer();
        }
        
        // Unmount the component
        root.unmount();
        
        // Also remove the container element
        if (container && container.parentNode) {
          container.parentNode.removeChild(container);
        }
      } catch (error) {
        console.error('Error destroying MCP terminal:', error);
      }
    },
    connect: () => {
      if (appInstance) {
        return appInstance.connectToServer();
      }
      return false;
    },
    disconnect: () => {
      if (appInstance) {
        return appInstance.disconnectFromServer();
      }
      return false;
    },
    getStatus: () => {
      if (appInstance) {
        return appInstance.getConnectionStatus();
      }
      return { isConnected: false, status: { type: 'unknown', message: 'Unknown' } };
    }
  };
};
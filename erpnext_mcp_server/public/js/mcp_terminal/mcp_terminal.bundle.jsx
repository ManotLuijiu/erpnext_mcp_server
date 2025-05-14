import React, {useRef} from 'react';
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
  // wrapper.appendChild(container);

  // Append to the container element
  if (containerElement && containerElement.appendChild) {
    containerElement.appendChild(container);
  } else {
    console.error('Invalid wrapper element provided to mcp_terminal.create');
    // Fallback: try to append to body if wrapper is invalid
    document.body.appendChild(container);
  }
  
  // Render our React app
  // const root = createRoot(container);
  // let appRef = null;
  // root.render(<App />);

  // Create a ref to access the App's methods
  const appRef = useRef();

   // Render our React app
  const root = createRoot(container);
  root.render(<App ref={appRef} />);
  
  // Return methods that can be called from outside
  return {
    destroy: () => {
      try {
        // Disconnect if connected
        if (appRef.current) {
          appRef.current.disconnectFromServer();
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
      if (appRef.current) {
        return appRef.current.connectToServer();
      }
      return false;
    },
    disconnect: () => {
      if (appRef.current) {
        return appRef.current.disconnectFromServer();
      }
      return false;
    },
    getStatus: () => {
      if (appRef.current) {
        return appRef.current.getConnectionStatus();
      }
      return { isConnected: false, status: { type: 'unknown', message: 'Unknown' } };
    }
  };
};
import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';

// This file is the entry point for Webpack
// It will render our React app into the designated container

frappe.provide('erpnext_mcp_server.mcp_terminal');

erpnext_mcp_server.mcp_terminal.create = function(wrapper) {
  // Create a container for our React app
  const container = document.createElement('div');
  container.className = 'mcp-terminal-page-wrapper';
  wrapper.appendChild(container);
  
  // Render our React app
  // const root = createRoot(container);
  // let appRef = null;
  // root.render(<App />);

  // Create React root
  const root = createRoot(container);
  
  // Create app ref to access its methods
  let appRef = null;
  
  // Render our React app
  root.render(<App ref={(ref) => { appRef = ref; }} />);
  
  return {
    destroy: () => {
      root.unmount();
    },
    connect: () => {
      if (appRef && appRef.connectToServer) {
        appRef.connectToServer();
        return true
      }
      return false
    }
  };
};
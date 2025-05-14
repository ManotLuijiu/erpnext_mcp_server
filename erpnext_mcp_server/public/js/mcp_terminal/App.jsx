import React, { useEffect, useRef, useState } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';

import './styles/terminal.css';
import './styles/xterm.css';

const App = () => {
  const terminalRef = useRef(null);
  const [terminal, setTerminal] = useState(null);
  const [socket, setSocket] = useState(null);
  // const [commandBuffer, setCommandBuffer] = useState('');
  const fitAddonRef = useRef(null);
  const terminalInstance = useRef(null);
  const socketRef = useRef(null);
  const commandBuffer = useRef('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    // Initialize terminal and WebSocket when component mounts
    initTerminal();

    // Connect to Frappe's existing Socket.IO
    setupSocketIO();

    // Clean up when component unmounts
    return () => {
      if (terminalInstance.current) {
        terminalInstance.current.dispose();
      }

      // Disconnect from specific events
      if (frappe.realtime) {
        frappe.realtime.off('terminal_response');
      }
    };
  }, []);

  const initTerminal = () => {
    // Make sure the Terminal constructor exists (loaded by frappe.require)
    if (typeof Terminal === 'undefined') {
      console.error(
        'Terminal is not defined. Make sure xterm.js is properly loaded.'
      );
      return;
    }

    // Create terminal instance
    const term = new Terminal({
      cursorBlink: true,
      theme: {
        background: '#1e1e1e',
        foreground: '#f0f0f0',
      },
      fontSize: 14,
      fontFamily: 'Menlo, Monaco, "Courier New", monospace',
      rows: 24,
      cols: 80,
      scrollback: 1000,
      convertEol: true,
    });

    // Create fit addon to make terminal resize with container
    // fitAddonRef.current = new FitAddon();
    // term.loadAddon(fitAddonRef.current);

    // Open terminal in the DOM element
    term.open(terminalRef.current);
    terminalInstance.current = term;
    // fitAddonRef.current.fit();

    // Welcome message
    term.writeln('ERPNext MCP Terminal');
    term.writeln('Type "help" for available commands');
    term.writeln('');

    // Handle key input
    term.onKey((e) => {
      const ev = e.domEvent;
      const key = e.key;

      // Handle special keys
      if (ev.keyCode === 13) {
        // Enter
        term.writeln('');
        if (commandBuffer.trim()) {
          processCommand(commandBuffer.trim());
        } else {
          showPrompt();
        }
        setCommandBuffer('');
      } else if (ev.keyCode === 8) {
        // Backspace
        if (commandBuffer.length > 0) {
          setCommandBuffer(commandBuffer.slice(0, -1));
          // Move cursor backward, write space, then move cursor backward again
          term.write('\b \b');
        }
      } else {
        // Regular character
        setCommandBuffer((prev) => prev + key);
        term.write(key);
      }
    });

    // Store terminal instance in state
    setTerminal(term);

    // Connect to WebSocket
    connectWebSocket(term);

    // Show initial prompt
    setTimeout(() => {
      showPrompt(term);

      // Add window resize handler
      window.addEventListener('resize', () => {
        if (fitAddonRef.current) {
          fitAddonRef.current.fit();
        }
      });
    }, 100);
  };

  function getWebSocketPort() {
    // Check if Frappe's Socket.IO is connected and use its host
    if (
      frappe.realtime &&
      frappe.realtime.socket &&
      frappe.realtime.socket.io &&
      frappe.realtime.socket.io.uri
    ) {
      // Parse the URI to extract the port
      const uri = new URL(frappe.realtime.socket.io.uri);
      if (uri.port) {
        return uri.port;
      }
    }

    // Otherwise check configuration
    if (frappe.socketio && frappe.socketio.port) {
      return frappe.socketio.port;
    }

    if (frappe.boot && frappe.boot.socketio_port) {
      return frappe.boot.socketio_port;
    }

    // Default port
    return 9000;
  }

  const connectWebSocket = (term) => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const hostname = window.location.hostname;
    const socketPort = getWebSocketPort();

    console.log('protocol', protocol);
    console.log('protocol', protocol);
    console.log('protocol', protocol);

    // const url = `${protocol}//${window.location.host}/api/method/erpnext_mcp_server.api.terminal.connect`;

    const url = `${protocol}//${hostname}:${socketPort}/api/method/erpnext_mcp_server.api.terminal.connect`;

    console.log('WebSocket URL:', url);

    console.log('window.location.host', window.location.host);
    console.log('url', url);

    const ws = new WebSocket(url);
    socketRef.current = ws;

    console.log('ws', ws);

    ws.onopen = () => {
      term.writeln('Connected to MCP server');
      showPrompt(term);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.output) {
        // Process ANSI escape sequences from rich
        term.write(data.output);
      }
      showPrompt(term);
    };

    ws.onclose = () => {
      term.writeln('Disconnected from MCP server');
      // Try to reconnect after delay
      setTimeout(() => connectWebSocket(term), 3000);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      term.writeln('Error: WebSocket connection failed');
    };

    setSocket(ws);
  };

  const showPrompt = (term = terminal) => {
    if (term) {
      term.write('\r\n> ');
    }
  };

  const processCommand = (command) => {
    if (command === 'clear') {
      terminal.clear();
      showPrompt();
      return;
    }

    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ command: command }));
    } else {
      terminal.writeln('Error: WebSocket connection not available');
      showPrompt();
    }
  };

  return (
    <div className="mcp-terminal-container">
      <div
        ref={terminalRef}
        className="mcp-terminal"
        style={{ width: '100%', height: '550px' }}
      />
    </div>
  );
};

export default App;

import React, { useEffect, useRef, useState } from 'react';
import { Terminal } from '@xterm/xterm';
import '@xterm/xterm/css/xterm.css';

export default function App() {
  const terminalRef = useRef(null);
  const terminalInstanceRef = useRef(null);
  const currentLineBuffer = useRef('');
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  console.log('terminalRef', terminalRef);
  console.log('terminalInstanceRef', terminalInstanceRef);

  console.log('user', frappe.session.user);

  // Function to start the MCP server
  const connectMCP = () => {
    if (terminalInstanceRef.current) {
      setIsLoading(true);
      terminalInstanceRef.current.write('Connecting to MCP Server...\r\n');
      const user = frappe.session.user;

      // Call backend to start MCP process
      frappe.call({
        method:
          'erpnext_mcp_server.handlers.socket_handlers.start_mcp_process_api',
        args: { user: user },
        callback: function (r) {
          setIsLoading(false);
          console.log('r', r);
          if (r.message && r.message.success) {
            terminalInstanceRef.current.write('MCP Server connected.\r\n');
            setIsConnected(true);
          } else {
            const errorMsg = r.message?.error || 'Unknown error';
            terminalInstanceRef.current.write(
              'Failed to connect: ' +
                errorMsg +
                (r.message?.error || 'Unknown error') +
                '\r\n'
            );
            console.error('MCP connection error: ', errorMsg);
          }
        },
        error: function (err) {
          setIsLoading(false);
          const errorMsg = err.message || 'Unknown error';
          terminalInstanceRef.current.write(
            'Connection error: ' + errorMsg + '\r\n'
          );
          console.error('MCP connection error:', err);
        },
      });
    }
  };

  // Function to disconnect from MCP server
  const disconnectMCP = () => {
    if (terminalInstanceRef.current) {
      terminalInstanceRef.current.write(
        '\r\nDisconnecting from MCP Server...\r\n'
      );

      const user = frappe.session.user;
      console.log('user disconnectMCP', user);

      frappe.call({
        method: 'erpnext_mcp_server.handlers.socket_handlers.stop_mcp_process',
        args: { user: user },
        callback: function (r) {
          if (r.message && r.message.success) {
            terminalInstanceRef.current.write('Disconnected successfully.\r\n');
            setIsConnected(false);
          } else {
            const errorMsg = r.message?.error || 'Unknown error';
            terminalInstanceRef.current.write(
              'Failed to disconnect: ' + errorMsg + '\r\n'
            );
          }
        },
      });
    }
  };

  useEffect(() => {
    // Debug any socket.io events
    const handleSocketEvent = (data) => {
      console.log('Socket.io event received:', data);
    };

    // Listen to all events (debugging)
    frappe.realtime.socket.onAny(handleSocketEvent);

    return () => {
      // Clean up
      frappe.realtime.socket.offAny(handleSocketEvent);
    };
  }, []);

  useEffect(() => {
    if (!terminalRef.current) return;

    console.log('terminalRef.current', terminalRef.current);

    // Initialize terminal
    const term = new Terminal({
      cursorBlink: true,
      theme: {
        background: '#1e1e1e',
        foreground: '#f0f0f0',
      },
      // rows: 24,
      // cols: 80,
    });

    console.log('term', term);

    term.open(terminalRef.current);
    terminalInstanceRef.current = term;

    console.log('terminalInstanceRef.current', terminalInstanceRef.current);

    // Initial greeting
    term.write(
      'MCP Terminal Connected. Type a command and press Enter.\r\n\r\n'
    );
    // Initial greeting
    term.write('MCP Terminal\r\n');
    term.write('-------------\r\n');
    term.write('Click "Connect MCP" to start the server.\r\n\r\n');

    // Test socket.io
    // frappe.realtime.on('item_connector', (data) => {
    //   console.log('data testing socket.io', data);
    // });

    // Set up socket.io connection
    frappe.realtime.on('mcp_terminal_output', (data) => {
      console.log('data mcp_terminal_output', data);
      if (terminalInstanceRef.current) {
        terminalInstanceRef.current.write(data);
      }
    });

    // Handle terminal input - using a difference approach
    currentLineBuffer.current = '';

    console.log('currentLineBuffer.current', currentLineBuffer.current);

    // Handle terminal input
    term.onKey(({ key, domEvent }) => {
      // If not connected, ignore input
      if (!isConnected) {
        if (domEvent.key === 'Enter') {
          term.write('\r\n');
        }
        return;
      }

      // Special key handling
      if (domEvent.key === 'Enter') {
        const command = currentLineBuffer.current;

        // Echo the command locally immediately
        term.write('\r\n');

        // Only send non-empty commands
        if (command.trim()) {
          // Send the command via Ajax call
          frappe.call({
            method:
              'erpnext_mcp_server.handlers.socket_handlers.send_terminal_input',
            args: {
              command: command,
            },
            callback: function (r) {
              if (r.message && !r.message.success) {
                // Only show error if command sending failed
                const errorMsg = r.message.error || 'Failed to send command';
                term.write('\r\nError: ' + errorMsg + '\r\n');
                console.error('Command error:', errorMsg);
              }
            },
            error: function (err) {
              term.write(
                '\r\nError sending command: ' +
                  (err.message || 'Unknown error') +
                  '\r\n'
              );
              console.error('Command error:', err);
            },
          });
        }

        // Get the current line
        // const currentLine = getCurrentLine(term);

        // console.log('currentLine', currentLine);

        // Testing socket.io
        // frappe.realtime.emit('item_connector', (data) => {
        //   console.log(data);
        // });

        // Send command to server
        frappe.realtime.emit('mcp_terminal_input', {
          command: currentLineBuffer.current,
          user: frappe.session.user,
        });

        // Reset buffer and add new line
        currentLineBuffer.current = '';
        term.write('\r\n');
      } else if (domEvent.key === 'Backspace') {
        // Handle backspace properly
        // const pos = term.buffer.active.cursorX;
        // if (pos > 0) {
        //   term.write('\b \b');
        // }
        // Handle backspace
        if (currentLineBuffer.current.length > 0) {
          currentLineBuffer.current = currentLineBuffer.current.slice(0, -1);
          term.write('\b \b');
        }
      } else {
        // Write the character to the terminal
        // Regular character input
        currentLineBuffer.current += key;
        term.write(key);
      }
    });

    // Helper function to get current line content
    // function getCurrentLine(term) {
    //   const currentRow = term.buffer.active.cursorY;
    //   let line = '';

    //   for (let i = 0; i < term.cols; i++) {
    //     const cell = term.buffer.active.getCell(i, currentRow);
    //     if (cell && cell.getChars()) {
    //       line += cell.getChars();
    //     }
    //   }

    //   return line.trim();
    // }

    return () => {
      // Clean up
      if (terminalInstanceRef.current) {
        terminalInstanceRef.current.dispose();
      }
      frappe.realtime.off('mcp_terminal_output');
    };
  }, [isConnected]);

  return (
    <div className="h-full w-full p-4 bg-gray-900">
      <div className="flex items-center justify-between mb-4">
        <div className="text-lg mb-4 text-white">MCP Terminal</div>
        <button
          className={`btn ${isConnected ? 'btn-secondary' : 'btn-primary'}`}
          onClick={
            isConnected
              ? () => {
                  console.log('connected');
                }
              : connectMCP
          }
          disabled={isLoading || isConnected}
        >
          {isLoading
            ? 'Connecting...'
            : isConnected
              ? 'Connected'
              : 'Connect MCP'}
        </button>

        <button
          className="btn btn-secondary"
          onClick={disconnectMCP}
          disabled={!isConnected}
        >
          Disconnect
        </button>

        <button
          className="btn btn-success ml-2"
          onClick={() => {
            frappe.call({
              method:
                'erpnext_mcp_server.handlers.socket_handlers.test_realtime_output',
              callback: function (r) {
                console.log('Realtime Test:', r.message);
              },
            });
          }}
        >
          Test Realtime
        </button>

        <button
          className="btn btn-secondary ml-2"
          onClick={() => {
            frappe.call({
              method:
                'erpnext_mcp_server.handlers.socket_handlers.start_test_echo_process',
              callback: function (r) {
                console.log('Test Echo Process:', r.message);
              },
            });
          }}
        >
          Start Echo Test
        </button>

        <button
          className="btn btn-info ml-2"
          onClick={() => {
            frappe.call({
              method:
                'erpnext_mcp_server.handlers.socket_handlers.test_redis_connection',
              callback: function (r) {
                console.log('Redis Test:', r.message);
                if (terminalInstanceRef.current) {
                  terminalInstanceRef.current.write(
                    '\r\nRedis Test Results: ' +
                      JSON.stringify(r.message, null, 2) +
                      '\r\n'
                  );
                }
              },
            });
          }}
        >
          Test Redis
        </button>
      </div>
      <div
        ref={terminalRef}
        className="h-5/6 w-full border border-gray-700 rounded"
      />
    </div>
  );
}

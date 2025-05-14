import React, { useState, useEffect, useRef, useCallback, forwardRef, useImperativeHandle } from 'react';
import { XTerm } from 'react-xtermjs';
import { FitAddon } from '@xterm/addon-fit';
import { AttachAddon } from '@xterm/addon-attach';

import './styles/xterm.css'
import './styles/terminal.css'

// Use forwardRef to allow parent components to get a ref to this component
const App = forwardRef((props, ref) => {
  const [isConnected, setIsConnected] = useState(false);
  const [status, setStatus] = useState({ type: 'disconnected', message: 'Disconnected' });
  const [terminalHeight, setTerminalHeight] = useState(400);
  const [addons, setAddons] = useState([]);
  const [sessionId, setSessionId] = useState(null);

  // Create refs
  const xtermRef = useRef(null);
  const containerRef = useRef(null);
  const websocketRef = useRef(null);
  const fitAddonRef = useRef(new FitAddon());
  
  // Constants
  const MIN_TERMINAL_HEIGHT = 300;
  const MAX_TERMINAL_HEIGHT = window.innerHeight - 200;

  // Expose methods to parent components through ref
  useImperativeHandle(ref, () => ({
    connectToServer: async () => {
      if (!isConnected) {
        await connect();
        return true;
      }
      return false;
    },
    disconnectFromServer: () => {
      if (isConnected) {
        disconnect();
        return true;
      }
      return false;
    },
    getConnectionStatus: () => {
      return { isConnected, status };
    }
  }));

  // Update terminal dimensions when window is resized
  useEffect(() => {
    const handleResize = () => {
      if (fitAddonRef.current) {
        setTimeout(() => fitAddonRef.current.fit(), 100);
        
        // Also send resize info to server if connected
        if (isConnected && websocketRef.current && xtermRef.current) {
          const { cols, rows } = xtermRef.current.terminal;
          sendWebSocketMessage({
            type: 'resize',
            cols,
            rows
          });
        }
      }
    };

    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [isConnected]);

  // Clean up WebSocket on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, []);
  
  // Function to send message through WebSocket
  const sendWebSocketMessage = (data) => {
    if (websocketRef.current && websocketRef.current.readyState === WebSocket.OPEN) {
      websocketRef.current.send(JSON.stringify(data));
    }
  };

  // Update the Connect MCP button state
  const updateConnectButton = useCallback((connected) => {
    const $button = $('.mcp-connect-btn');
    if (connected) {
      $button.removeClass('btn-primary').addClass('btn-success').html(`
        <i class="fa fa-check mr-1"></i> ${__('Connected')}
      `);
    } else {
      $button.removeClass('btn-success').addClass('btn-primary').html(`
        <i class="fa fa-plug mr-1"></i> ${__('Connect MCP')}
      `);
    }
  }, []);

  // Log terminal events for auditing
  const logTerminalEvent = useCallback((eventType, details = null, commandType = null) => {
    frappe.call({
      method: 'erpnext_mcp_server.api.log_terminal_session',
      args: {
        session_id: sessionId,
        action: eventType,
        details: details,
        command_type: commandType
      },
      callback: function(r) {
        if (r.exc) {
          console.error('Failed to log terminal event:', r.exc);
        }
      }
    });
  }, [sessionId]);

  // Create a terminal session
  const createTerminalSession = async () => {
    try {
      return new Promise((resolve, reject) => {
        frappe.call({
          method: 'erpnext_mcp_server.api.create_terminal_session',
          callback: function(r) {
            if (r.message && r.message.success) {
              setSessionId(r.message.session_id);
              resolve(r.message.session_id);
            } else {
              reject(new Error(r.message?.error || 'Failed to create terminal session'));
            }
          },
          error: function(err) {
            reject(err);
          }
        });
      });
    } catch (error) {
      console.error('Error creating terminal session:', error);
      throw error;
    }
  };

  // Connect to the MCP Server
  const connect = async () => {
    try {
      // Update status
      setStatus({ type: 'connecting', message: 'Connecting...' });
      
      // Update button state
      updateConnectButton(false);
      $('.mcp-connect-btn').html('<i class="fa fa-spinner fa-spin mr-1"></i> ' + __('Connecting...'));
      
      // Create a terminal session
      const session_id = await createTerminalSession();
      
      // Get the WebSocket URL
      const site_name = frappe.boot.sitename || '';
      const websocket_url = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//` +
                            `${window.location.host}/${site_name}/api/websocket/terminal`;
      
      // Close any existing connection
      if (websocketRef.current) {
        websocketRef.current.close();
      }
      
      // Create new WebSocket connection
      websocketRef.current = new WebSocket(websocket_url);
      
      websocketRef.current.onopen = () => {
        // Send authentication data
        sendWebSocketMessage({
          session_id: session_id
        });
      };
      
      websocketRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.error) {
            // Handle error
            if (xtermRef.current) {
              xtermRef.current.terminal.writeln(`\r\n\x1b[31mError: ${data.error}\x1b[0m`);
            }
            
            if (data.close) {
              disconnect();
            }
          } else if (data.message === 'Authentication successful') {
            // Authentication successful, terminal is ready
            setIsConnected(true);
            setStatus({ type: 'connected', message: 'Connected' });
            
            // Update button
            updateConnectButton(true);
            
            // Set up the terminal with dimensions
            if (xtermRef.current && fitAddonRef.current) {
              fitAddonRef.current.fit();
              const { cols, rows } = xtermRef.current.terminal;
              
              // Send terminal dimensions
              sendWebSocketMessage({
                type: 'resize',
                cols,
                rows
              });
              
              // Focus the terminal
              xtermRef.current.terminal.focus();
            }
            
            // Set up ping interval to keep the connection alive
            const pingInterval = setInterval(() => {
              if (websocketRef.current?.readyState === WebSocket.OPEN) {
                sendWebSocketMessage({
                  type: 'ping',
                  time: Date.now()
                });
              } else {
                clearInterval(pingInterval);
              }
            }, 30000); // 30 second ping
            
            // Store interval ID for cleanup
            websocketRef.current.pingInterval = pingInterval;
          } else if (data.type === 'output') {
            // Handle terminal output
            if (xtermRef.current && data.data) {
              xtermRef.current.terminal.write(data.data);
            }
          }
        } catch (error) {
          console.error('Error handling WebSocket message:', error);
        }
      };
      
      websocketRef.current.onclose = (event) => {
        handleDisconnect(event);
      };
      
      websocketRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        if (xtermRef.current) {
          xtermRef.current.terminal.writeln('\r\n\x1b[31mWebSocket error occurred\x1b[0m');
        }
        logTerminalEvent('Error', 'WebSocket error occurred');
      };
      
      // Set up terminal input handler
      if (xtermRef.current) {
        // Remove any existing listeners
        const terminal = xtermRef.current.terminal;
        
        // Add data event listener
        terminal.onData((data) => {
          if (websocketRef.current?.readyState === WebSocket.OPEN) {
            sendWebSocketMessage({
              type: 'input',
              data: data
            });
          }
        });
      }
    } catch (error) {
      console.error('Connection error:', error);
      if (xtermRef.current) {
        xtermRef.current.terminal.writeln(`\r\n\x1b[31mError: ${error.message || 'Connection failed'}\x1b[0m`);
      }
      setStatus({ type: 'error', message: 'Connection error' });
      updateConnectButton(false);
      logTerminalEvent('Error', `Connection error: ${error.message || 'Unknown error'}`);
    }
  };

  // Disconnect from the MCP Server
  const disconnect = () => {
    try {
      // Close WebSocket connection
      if (websocketRef.current) {
        // Clear ping interval
        if (websocketRef.current.pingInterval) {
          clearInterval(websocketRef.current.pingInterval);
        }
        
        // Close the connection
        websocketRef.current.close();
        websocketRef.current = null;
      }
      
      // Close the terminal session on the server
      if (sessionId) {
        frappe.call({
          method: 'erpnext_mcp_server.api.close_terminal_session',
          args: {
            session_id: sessionId
          },
          callback: function(r) {
            if (!r.message || !r.message.success) {
              console.error('Failed to close terminal session:', r.message?.error || 'Unknown error');
            }
          }
        });
      }
      
      // Update state
      setIsConnected(false);
      setStatus({ type: 'disconnected', message: 'Disconnected' });
      
      // Update button
      updateConnectButton(false);
      
      // Log disconnection
      logTerminalEvent('Disconnect', 'Terminal disconnected');
      
      // Clear session ID
      setSessionId(null);
    } catch (error) {
      console.error('Error disconnecting:', error);
    }
  };

  // Handle WebSocket disconnection
  const handleDisconnect = (event) => {
    // Only handle if currently connected
    if (!isConnected) return;
    
    // Clear interval if exists
    if (websocketRef.current && websocketRef.current.pingInterval) {
      clearInterval(websocketRef.current.pingInterval);
    }
    
    setIsConnected(false);
    setStatus({ type: 'disconnected', message: 'Disconnected' });
    
    // Update button
    updateConnectButton(false);
    
    if (xtermRef.current) {
      if (event.wasClean) {
        xtermRef.current.terminal.writeln('\r\n\x1b[33mConnection closed cleanly\x1b[0m');
      } else {
        xtermRef.current.terminal.writeln(`\r\n\x1b[31mConnection closed unexpectedly. Code: ${event.code}\x1b[0m`);
        if (event.reason) {
          xtermRef.current.terminal.writeln(`\x1b[31mReason: ${event.reason}\x1b[0m`);
        }
      }
    }
    
    // Log disconnection details
    logTerminalEvent('Disconnect', `Connection closed: ${event.wasClean ? 'Clean' : 'Unexpected'}, Code: ${event.code}, Reason: ${event.reason || 'None'}`);
  };

  // Handle mouse drag to resize terminal
  const handleMouseDown = (e) => {
    e.preventDefault();
    
    const startY = e.clientY;
    const startHeight = terminalHeight;
    
    const onMouseMove = (mouseMoveEvent) => {
      // Calculate new height
      const deltaY = startY - mouseMoveEvent.clientY;
      const newHeight = startHeight + deltaY;
      
      // Apply constraints
      const newTerminalHeight = Math.max(
        MIN_TERMINAL_HEIGHT, 
        Math.min(newHeight, MAX_TERMINAL_HEIGHT)
      );
      
      setTerminalHeight(newTerminalHeight);
    };
    
    const onMouseUp = () => {
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
      
      // Fit terminal to new size
      if (fitAddonRef.current) {
        setTimeout(() => {
          fitAddonRef.current.fit();
          
          // Send resize info to server if connected
          if (isConnected && websocketRef.current && xtermRef.current) {
            const { cols, rows } = xtermRef.current.terminal;
            sendWebSocketMessage({
              type: 'resize',
              cols,
              rows
            });
          }
        }, 100);
      }
    };
    
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  };

  // Toggle terminal size between min and max
  const toggleSize = () => {
    const newHeight = terminalHeight === MAX_TERMINAL_HEIGHT 
      ? MIN_TERMINAL_HEIGHT
      : MAX_TERMINAL_HEIGHT;
    
    setTerminalHeight(newHeight);
    
    // Fit terminal to new size
    if (fitAddonRef.current) {
      setTimeout(() => {
        fitAddonRef.current.fit();
        
        // Send resize info to server if connected
        if (isConnected && websocketRef.current && xtermRef.current) {
          const { cols, rows } = xtermRef.current.terminal;
          sendWebSocketMessage({
            type: 'resize',
            cols,
            rows
          });
        }
      }, 100);
    }
  };

  return (
    <div className="mcp-terminal-container" ref={containerRef}>
      {/* Terminal resize handle */}
      <div 
        className="terminal-resize-handle"
        onMouseDown={handleMouseDown}
      >
        <i className="fa fa-grip-lines"></i>
      </div>
      
      {/* Terminal header with controls */}
      <div className="terminal-header">
        <div className="terminal-status">
          <span className={`terminal-status-indicator ${status.type}`}></span>
          <span>{status.message}</span>
          {sessionId && <span className="ml-2 text-muted text-xs">Session: {sessionId.substring(0, 8)}...</span>}
        </div>
        
        <div className="terminal-controls">
          <button 
            className={`btn btn-sm ${isConnected ? 'btn-danger' : 'btn-primary'}`}
            onClick={isConnected ? disconnect : connect}
          >
            {isConnected ? 'Disconnect' : 'Connect'}
          </button>
          
          <button 
            className="btn btn-sm btn-icon ml-2"
            onClick={toggleSize}
            title={terminalHeight === MAX_TERMINAL_HEIGHT ? 'Minimize' : 'Maximize'}
          >
            <i className={`fa fa-${terminalHeight === MAX_TERMINAL_HEIGHT ? 'compress' : 'expand'}`}></i>
          </button>
          
          <button
            className="btn btn-sm btn-icon ml-2"
            onClick={() => {
              if (xtermRef.current) {
                xtermRef.current.terminal.clear();
              }
            }}
            title="Clear terminal"
          >
            <i className="fa fa-eraser"></i>
          </button>
        </div>
      </div>
      
      {/* Terminal container */}
      <div 
        className="terminal-container"
        style={{ height: `${terminalHeight}px` }}
      >
        <XTerm 
          ref={xtermRef}
          className="xterm" 
          addons={[fitAddonRef.current]}
          options={{
            cursorBlink: true,
            fontFamily: 'monospace',
            fontSize: 14,
            theme: {
              background: '#1e1e1e',
              foreground: '#f0f0f0'
            }
          }}
        />
      </div>
    </div>
  );
});

export default App;
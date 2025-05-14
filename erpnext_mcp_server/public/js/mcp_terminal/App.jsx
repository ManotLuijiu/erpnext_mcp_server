import React, { useState, useEffect, useRef, useCallback } from 'react';
import { XTerm } from 'react-xtermjs';
import { FitAddon } from '@xterm/addon-fit';
import { AttachAddon } from '@xterm/addon-attach';

function App() {
  const [isConnected, setIsConnected] = useState(false);
  const [status, setStatus] = useState({ type: 'disconnected', message: 'Disconnected' });
  const [terminalHeight, setTerminalHeight] = useState(400);
  const [addons, setAddons] = useState([]);
  const [tokenStatus, setTokenStatus] = useState('');
  const [sessionId, setSessionId] = useState(null);

  const fitAddonRef = useRef(new FitAddon());
  const terminalRef = useRef(null);
  const websocketRef = useRef(null);
  const containerRef = useRef(null);
  
  const MIN_TERMINAL_HEIGHT = 300;
  const MAX_TERMINAL_HEIGHT = window.innerHeight - 200; // Account for headers and footers

  // Generate a unique session ID for tracking terminal usage
  const generateSessionId = useCallback(() => {
    return 'term_' + Math.random().toString(36).substring(2, 15) + 
           Math.random().toString(36).substring(2, 15);
  }, []);

  // Initialize session ID once
  useEffect(() => {
    if (!sessionId) {
      setSessionId(generateSessionId());
    }
  }, [generateSessionId, sessionId]);

  // Log terminal events for auditing
  const logTerminalEvent = useCallback((eventType, details = null, commandType = null) => {
    if (!sessionId) return;
    
    frappe.call({
      method: 'erpnext_mcp_server.api.log_terminal_event',
      args: {
        event_type: eventType,
        session_id: sessionId,
        command_type: commandType,
        details: details
      },
      callback: function(r) {
        if (r.exc) {
          console.error('Failed to log terminal event:', r.exc);
        }
      }
    });
  }, [sessionId]);

  // Update terminal dimensions when window is resized
  useEffect(() => {
    const handleResize = () => {
      if (fitAddonRef.current) {
        setTimeout(() => fitAddonRef.current.fit(), 100);
      }
    };

    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  // Clean up WebSocket on unmount
  useEffect(() => {
    return () => {
      if (websocketRef.current) {
        websocketRef.current.close();
      }
    };
  }, []);

  // Token management functions
  const encryptToken = (token) => {
    try {
      const key = frappe.session.user + '_terminal_key';
      return btoa(unescape(encodeURIComponent(JSON.stringify({
        token,
        key,
        timestamp: Date.now()
      }))));
    } catch (error) {
      console.error('Error encrypting token', error);
      return null;
    }
  };

  const decryptToken = (encryptedToken) => {
    try {
      const data = JSON.parse(decodeURIComponent(escape(atob(encryptedToken))));
      if (data.key !== frappe.session.user + '_terminal_key') {
        return null;
      }
      return data.token;
    } catch (error) {
      console.error('Error decrypting token', error);
      return null;
    }
  };

  const storeToken = (token, expiresIn) => {
    const expiryDate = new Date();
    expiryDate.setSeconds(expiryDate.getSeconds() + expiresIn);
    
    const tokenData = {
      expires_at: expiryDate.toISOString(),
      expires_in: expiresIn
    };
    
    const encryptedToken = encryptToken(token);
    localStorage.setItem('mcp_token', encryptedToken);
    localStorage.setItem('mcp_token_data', JSON.stringify(tokenData));
  };

  const getStoredToken = () => {
    const encryptedToken = localStorage.getItem('mcp_token');
    if (!encryptedToken) return null;
    
    return decryptToken(encryptedToken);
  };

  const getToken = async (silent = false) => {
    if (!silent) {
      setTokenStatus('Requesting token...');
    }
    
    try {
      return new Promise((resolve, reject) => {
        frappe.call({
          method: 'erpnext_mcp_server.api.get_mcp_token',
          callback: function(r) {
            if (r.message && r.message.token) {
              const token = r.message.token;
              const expiresIn = r.message.expires_in || 3600;
              
              storeToken(token, expiresIn);
              
              if (!silent) {
                setTokenStatus('Token received');
                frappe.show_alert({
                  message: __('Token successfully retrieved'),
                  indicator: 'green'
                }, 3);
              }
              
              logTerminalEvent('Token Request', 'Token successfully retrieved');
              resolve({ token, expires_in: expiresIn });
            } else {
              if (!silent) {
                setTokenStatus('Failed to get token');
                frappe.show_alert({
                  message: __('Failed to retrieve token'),
                  indicator: 'red'
                }, 5);
              }
              
              logTerminalEvent('Error', 'Failed to retrieve token');
              reject(new Error(r.message?.error || 'Failed to get token'));
            }
          },
          error: function(err) {
            reject(err);
          }
        });
      });
    } catch (error) {
      console.error('Error getting token:', error);
      if (!silent) {
        setTokenStatus('Error getting token');
      }
      return null;
    }
  };

  const refreshToken = async () => {
    try {
      // Check current token
      const storedToken = getStoredToken();
      const tokenData = localStorage.getItem('mcp_token_data');
      
      if (!storedToken || !tokenData) {
        // No token found, get a new one
        return await getToken(true);
      }
      
      // Parse token data
      const { expires_at } = JSON.parse(tokenData);
      
      // Check if token is about to expire (within 5 minutes)
      const now = Date.now();
      const expiryTime = new Date(expires_at).getTime();
      const fiveMinutesInMs = 5 * 60 * 1000;
      
      if (expiryTime - now < fiveMinutesInMs) {
        if (terminalRef.current) {
          terminalRef.current.terminal.writeln('\r\n\x1b[33mToken is about to expire, refreshing...\x1b[0m');
        }
        return await getToken(true);
      }
      
      return { token: storedToken };
    } catch (error) {
      console.error('Error refreshing token:', error);
      return null;
    }
  };

  // Get MCP Settings from Frappe backend
  const getMCPSettings = async () => {
    return new Promise((resolve, reject) => {
      frappe.call({
        method: 'erpnext_mcp_server.api.get_mcp_settings',
        callback: function(r) {
          if (r.message) {
            resolve(r.message);
          } else {
            reject(new Error('Failed to get MCP settings'));
          }
        },
        error: function(err) {
          reject(err);
        }
      });
    });
  };

  // Connect to the MCP Server via WebSocket
  const connect = async () => {
    try {
      // Update status
      setStatus({ type: 'connecting', message: 'Connecting...' });
      
      // Log connection attempt
      logTerminalEvent('Connect', 'Terminal connection initiated');
      
      // Get settings
      const settings = await getMCPSettings();
      
      if (!settings || !settings.websocket_url) {
        if (terminalRef.current) {
          terminalRef.current.terminal.writeln('\r\n\x1b[31mError: WebSocket URL not configured in MCP Settings\x1b[0m');
        }
        setStatus({ type: 'error', message: 'Configuration error' });
        return;
      }
      
      // Get token with automatic refresh if needed
      const tokenResult = await refreshToken();
      if (!tokenResult || !tokenResult.token) {
        if (terminalRef.current) {
          terminalRef.current.terminal.writeln('\r\n\x1b[31mError: Failed to get authentication token\x1b[0m');
        }
        setStatus({ type: 'error', message: 'Authentication error' });
        return;
      }
      const token = tokenResult.token;
      
      // Close existing connection if any
      disconnect();
      
      // Calculate terminal dimensions
      const dimensions = fitAddonRef.current.proposeDimensions();
      const cols = dimensions ? dimensions.cols : 80;
      const rows = dimensions ? dimensions.rows : 24;
      
      // Build WebSocket URL with parameters
      const wsUrl = new URL(settings.websocket_url);
      wsUrl.searchParams.append('token', token);
      wsUrl.searchParams.append('cols', cols.toString());
      wsUrl.searchParams.append('rows', rows.toString());
      
      // Create WebSocket connection
      websocketRef.current = new WebSocket(wsUrl.toString());
      
      websocketRef.current.onopen = () => {
        // Create attach addon
        const attachAddon = new AttachAddon(websocketRef.current);
        setAddons([fitAddonRef.current, attachAddon]);
        
        // Update state
        setIsConnected(true);
        setStatus({ type: 'connected', message: 'Connected' });
        
        // Clear terminal and focus
        if (terminalRef.current) {
          terminalRef.current.terminal.clear();
          terminalRef.current.terminal.focus();
        }
        
        // Log successful connection
        logTerminalEvent('Connect', 'Terminal connection established', 'Shell');
      };
      
      websocketRef.current.onclose = (event) => {
        handleDisconnect(event);
      };
      
      websocketRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        if (terminalRef.current) {
          terminalRef.current.terminal.writeln('\r\n\x1b[31mWebSocket error occurred\x1b[0m');
        }
        logTerminalEvent('Error', 'WebSocket error occurred');
      };
    } catch (error) {
      console.error('Connection error:', error);
      if (terminalRef.current) {
        terminalRef.current.terminal.writeln(`\r\n\x1b[31mError: ${error.message || 'Connection failed'}\x1b[0m`);
      }
      setStatus({ type: 'error', message: 'Connection error' });
      logTerminalEvent('Error', `Connection error: ${error.message || 'Unknown error'}`);
    }
  };

  // Disconnect from the WebSocket
  const disconnect = () => {
    if (websocketRef.current) {
      websocketRef.current.close();
    }
    
    // Remove the addon from terminal
    setAddons([fitAddonRef.current]);
    
    // Update state
    setIsConnected(false);
    setStatus({ type: 'disconnected', message: 'Disconnected' });
    
    // Log disconnection
    logTerminalEvent('Disconnect', 'Terminal disconnected');
  };

  // Handle WebSocket disconnection
  const handleDisconnect = (event) => {
    // Only handle if currently connected
    if (!isConnected) return;
    
    setIsConnected(false);
    setStatus({ type: 'disconnected', message: 'Disconnected' });
    setAddons([fitAddonRef.current]);
    
    if (terminalRef.current) {
      if (event.wasClean) {
        terminalRef.current.terminal.writeln('\r\n\x1b[33mConnection closed cleanly\x1b[0m');
      } else {
        terminalRef.current.terminal.writeln(`\r\n\x1b[31mConnection closed unexpectedly. Code: ${event.code}\x1b[0m`);
        if (event.reason) {
          terminalRef.current.terminal.writeln(`\x1b[31mReason: ${event.reason}\x1b[0m`);
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
        setTimeout(() => fitAddonRef.current.fit(), 100);
      }
    };
    
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  };

  // Toggle terminal size between min and max
  const toggleSize = () => {
    if (terminalHeight === MAX_TERMINAL_HEIGHT) {
      setTerminalHeight(MIN_TERMINAL_HEIGHT);
    } else {
      setTerminalHeight(MAX_TERMINAL_HEIGHT);
    }
    
    // Fit terminal to new size
    if (fitAddonRef.current) {
      setTimeout(() => fitAddonRef.current.fit(), 100);
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
        </div>
        
        <div className="terminal-controls">
          <button 
            className={`btn btn-sm ${isConnected ? 'btn-danger' : 'btn-primary'}`}
            onClick={isConnected ? disconnect : connect}
          >
            {isConnected ? 'Disconnect' : 'Connect'}
          </button>
          
          <button 
            className="btn btn-sm btn-default ml-2"
            onClick={() => getToken()}
          >
            Get Token
            {tokenStatus && <span className="ml-2">{tokenStatus}</span>}
          </button>
          
          <button 
            className="btn btn-sm btn-icon ml-2"
            onClick={toggleSize}
          >
            <i className={`fa fa-${terminalHeight === MAX_TERMINAL_HEIGHT ? 'compress' : 'expand'}`}></i>
          </button>
        </div>
      </div>
      
      {/* Terminal container */}
      <div 
        className="terminal-container"
        style={{ height: `${terminalHeight}px` }}
      >
        {addons.length >= 2 ? (
          <XTerm 
            ref={terminalRef}
            className="xterm" 
            addons={addons}
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
        ) : (
          <div className="terminal-placeholder">
            <div className="terminal-placeholder-content">
              <i className="fa fa-terminal fa-2x mb-2"></i>
              <p>Terminal ready</p>
              <p className="text-muted">Click "Connect" to start a session</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
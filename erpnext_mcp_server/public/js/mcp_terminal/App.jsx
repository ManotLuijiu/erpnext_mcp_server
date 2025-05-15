import React, {
  useState,
  useEffect,
  useRef,
  useCallback,
  forwardRef,
  useImperativeHandle,
} from 'react';
import { XTerm } from 'react-xtermjs';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
// import { AttachAddon } from '@xterm/addon-attach';
import { io } from 'socket.io-client';
import './styles/xterm.css';
// import './styles/terminal.css';

function App() {
  const terminalRef = useRef(null);
  const socketRef = useRef(null);
  const termRef = useRef(null);
  const fitAddonRef = useRef(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    // let term = null;
    // let fitAddon = null;

    // const initializeTerminal = () => {
    //   term = new Terminal({
    //     cursorBlink: true,
    //     fontSize: 14,
    //     fontFamily: 'Menlo, Monaco, "Courier New", monospace',
    //     theme: {
    //       background: '#1a1b26',
    //       foreground: '#a9b1d6',
    //       cursor: '#c0caf5',
    //       selection: '#28344a',
    //       black: '#414868',
    //       red: '#f7768e',
    //       green: '#9ece6a',
    //       yellow: '#e0af68',
    //       blue: '#7aa2f7',
    //       magenta: '#bb9af7',
    //       cyan: '#7dcfff',
    //       white: '#c0caf5',
    //       brightBlack: '#414868',
    //       brightRed: '#f7768e',
    //       brightGreen: '#9ece6a',
    //       brightYellow: '#e0af68',
    //       brightBlue: '#7aa2f7',
    //       brightMagenta: '#bb9af7',
    //       brightCyan: '#7dcfff',
    //       brightWhite: '#c0caf5',
    //     },
    //     rows: 24,
    //     cols: 80,
    //     convertEol: true,
    //     scrollback: 1000,
    //     rendererType: 'canvas',
    //     allowTransparency: true,
    //   });

    //   fitAddon = new FitAddon();
    //   term.loadAddon(fitAddon);
    //   termRef.current = term;

    //   if (terminalRef.current) {
    //     term.open(terminalRef.current);
    //     fitAddon.fit();
    //   }
    // };

    const term = new Terminal({
      cursorBlink: true, // Enable cursor blinking
      fontSize: 14,
      fontFamily: 'Menlo, Monaco, "Courier New", monospace',
      theme: {
        background: '#1a1b26',
        foreground: '#a9b1d6',
        cursor: '#c0caf5',
        cursorAccent: '#1a1b26', // Add cursor accent color
        selection: '#28344a',
        black: '#414868',
        red: '#f7768e',
        green: '#9ece6a',
        yellow: '#e0af68',
        blue: '#7aa2f7',
        magenta: '#bb9af7',
        cyan: '#7dcfff',
        white: '#c0caf5',
        brightBlack: '#414868',
        brightRed: '#f7768e',
        brightGreen: '#9ece6a',
        brightYellow: '#e0af68',
        brightBlue: '#7aa2f7',
        brightMagenta: '#bb9af7',
        brightCyan: '#7dcfff',
        brightWhite: '#c0caf5',
      },
      rows: 24,
      cols: 80,
      convertEol: true,
      scrollback: 1000,
      rendererType: 'canvas',
      allowTransparency: true,
    });

    // Create and load the FitAddon
    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);

    // Store references
    termRef.current = term;
    fitAddonRef.current = fitAddon;

    // Open terminal if the DOM element is available
    if (terminalRef.current) {
      term.open(terminalRef.current);
      fitAddon.fit();

      // Important: Focus the terminal to make cursor work
      term.focus();
    }

    // Create Socket.IO connection - Use Frappe-compatible endpoint
    // Use site URL for production or localhost for development
    // const socketUrl1 = window.location.origin;
    const protocol = window.location.protocol;
    const host = window.location.host;

    const { sitename, socketio_port } = frappe.boot;
    // const testUrl = 'http://localhost:9000';
    console.log('ENV', process.env.NODE_ENV);

    const dev = process.env.NODE_ENV === 'development';

    const socketUrl =
      frappe && !dev
        ? `${window.location.protocol}//${sitename}`
        : 'http://localhost:9000';

    console.log('protocol', protocol);
    console.log('host', host);
    console.log('sitename', sitename);
    console.log('socketio_port', socketio_port);
    console.log('socketUrl', socketUrl);

    // const initializeSocket = () => {
    //   socketRef.current = io(testUrl, {
    //     transports: ['polling', 'websocket'],
    //     reconnection: true,
    //     reconnectionAttempts: Infinity,
    //     reconnectionDelay: 1000,
    //     reconnectionDelayMax: 5000,
    //     timeout: 20000,
    //     autoConnect: true,
    //     forceNew: true,
    //     path: '/socket.io/',
    //     upgrade: true,
    //     rememberUpgrade: true,
    //     rejectUnauthorized: false,
    //   });

    //   console.log('socketRef.current', socketRef.current);

    //   socketRef.current.on('connect_error', (error) => {
    //     console.error('Connection error: ', error);
    //     setIsConnected(false);
    //     if (term) {
    //       term.write(
    //         '\r\n\x1b[31mConnection error. Attempting to reconnect...\x1b[0m\r\n'
    //       );
    //     }
    //   });

    //   socketRef.current.on('connect', () => {
    //     console.log('Connected to server');
    //     setIsConnected(true);
    //     console.log('term onConnected', term);
    //     if (term) {
    //       term.write('\r\n\x1b[32mConnected to server.\x1b[0m\r\n');
    //       fitAddon.fit();
    //       const { rows, cols } = term;

    //       console.log('rows', rows);
    //       console.log('cols', cols);

    //       socketRef.current.emit('resize', { rows, cols });
    //     }
    //   });

    //   socketRef.current.on('disconnect', (reason) => {
    //     console.log('Disconnected from server: ', reason);
    //     setIsConnected(false);
    //     if (term) {
    //       term.write(
    //         '\r\n\x1b[33mDisconnected from server. Reason: ' +
    //           reason +
    //           '\x1b[0m\r\n'
    //       );
    //     }
    //   });

    //   socketRef.current.on('reconnect_attempt', (attemptNumber) => {
    //     console.log('Reconnection attempt:', attemptNumber);
    //     if (term) {
    //       term.write(
    //         '\r\n\x1b[33mAttempting to reconnect... (Attempt ' +
    //           attemptNumber +
    //           ')\x1b[0m\r\n'
    //       );
    //     }
    //   });

    //   socketRef.current.on('reconnect', (attemptNumber) => {
    //     console.log('Reconnected after', attemptNumber, 'attempts');
    //     if (term) {
    //       term.write('\r\n\x1b[32mReconnected to server.\x1b[0m\r\n');
    //     }
    //   });

    //   socketRef.current.on('reconnect_error', (error) => {
    //     console.error('Reconnection error:', error);
    //     if (term) {
    //       term.write(
    //         '\r\n\x1b[31mReconnection error: ' + error.message + '\x1b[0m\r\n'
    //       );
    //     }
    //   });

    //   socketRef.current.on('reconnect_failed', () => {
    //     console.error('Failed to reconnect');
    //     if (term) {
    //       term.write('\r\n\x1b[31mFailed to reconnect to server.\x1b[0m\r\n');
    //     }
    //   });

    //   socketRef.current.on('upgrade', (transport) => {
    //     console.log('Transport upgraded to:', transport.name);
    //     if (term) {
    //       term.write(
    //         '\r\n\x1b[36mTransport upgraded to: ' +
    //           transport.name +
    //           '\x1b[0m\r\n'
    //       );
    //     }
    //   });

    //   socketRef.current.on('upgradeError', (error) => {
    //     console.error('Transport upgrade error:', error);
    //     if (term) {
    //       term.write(
    //         '\r\n\x1b[31mTransport upgrade failed: ' +
    //           error.message +
    //           '\x1b[0m\r\n'
    //       );
    //     }
    //   });

    //   socketRef.current.on('output', (data) => {
    //     if (term) {
    //       term.write(data);
    //     }
    //   });

    //   if (term) {
    //     term.onData((data) => {
    //       if (socketRef.current?.connected) {
    //         socketRef.current.emit('input', data);
    //       }
    //     });
    //   }
    // };

    // Configure Socket.IO connection with Frappe paths
    socketRef.current = io(socketUrl, {
      path: frappe ? '/socket.io/' : '/socket.io',
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: Infinity,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      timeout: 20000,
      autoConnect: true,
    });

    // Socket.IO connection handlers
    socketRef.current.on('connect', () => {
      console.log('Connected to Socket.IO server');
      setIsConnected(true);

      // Notify server about terminal size
      const { rows, cols } = term;
      socketRef.current.emit('terminal:resize', { rows, cols });

      // Send session information to identity this terminal
      socketRef.current.emit('terminal:connect', {
        session_id: frappe.session.user_id || 'anonymous',
      });

      // Write connection message to terminal
      term.write('\r\n\x1b[32mConnected to MCP Server\x1b[0m\r\n');

      // Focus the terminal after connection
      term.focus();
    });

    socketRef.current.on('disconnect', (reason) => {
      console.log('Disconnected from server:', reason);
      setIsConnected(false);
      term.write(
        '\r\n\x1b[33mDisconnected from server: ' + reason + '\x1b[0m\r\n'
      );
    });

    socketRef.current.on('terminal:output', (data) => {
      // Handle output data from server
      console.log('Received data:', data);
      if (typeof data === 'string') {
        term.write(data);
      } else if (data && data.data) {
        term.write(data.data);
      }
    });

    // Set up terminal input handler
    term.onData((data) => {
      if (socketRef.current && socketRef.current.connected) {
        console.log('Sending data:', data);
        socketRef.current.emit('terminal:input', {
          data: data,
        });
      }
    });

    const handleResize = () => {
      if (fitAddon && term) {
        fitAddon.fit();
        const { rows, cols } = term;
        if (socketRef.current?.connected) {
          socketRef.current.emit('resize', { rows, cols });
        }
      }
    };

    window.addEventListener('resize', handleResize);
    handleResize();

    return () => {
      if (term) {
        term.dispose();
      }
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700">
        <div className="container mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 rounded-full bg-red-500"></div>
            <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
            <div className="w-3 h-3 rounded-full bg-green-500"></div>
            <span className="ml-4 text-sm font-medium">Web Bash Terminal</span>
          </div>
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <div
                className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}
              ></div>
              <span className="text-xs text-gray-400">
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-6">
        <div className="bg-gray-800 rounded-lg shadow-xl overflow-hidden border border-gray-700">
          <div
            ref={terminalRef}
            className="h-[calc(100vh-12rem)] w-full"
            style={{ minHeight: '400px' }}
          />
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-gray-800 border-t border-gray-700">
        <div className="container mx-auto px-4 py-2">
          <p className="text-xs text-gray-400 text-center">
            Press Ctrl+C to clear the terminal • Ctrl+L to clear the screen
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;

// Use forwardRef to allow parent components to get a ref to this component
// const App = forwardRef((props, ref) => {
//   console.log('props App.jsx', props);
//   const [isConnected, setIsConnected] = useState(false);
//   const [status, setStatus] = useState({
//     type: 'disconnected',
//     message: 'Disconnected',
//   });
//   const [terminalHeight, setTerminalHeight] = useState(400);
//   const [addons, setAddons] = useState([]);
//   const [sessionId, setSessionId] = useState(null);

//   // Create refs
//   const xtermRef = useRef(null);
//   const containerRef = useRef(null);
//   const socketRef = useRef(null);
//   const fitAddonRef = useRef(new FitAddon());

//   // Constants
//   const MIN_TERMINAL_HEIGHT = 300;
//   const MAX_TERMINAL_HEIGHT = window.innerHeight - 200;

//   // Expose methods to parent components through ref
//   useImperativeHandle(ref, () => ({
//     connectToServer: async () => {
//       if (!isConnected) {
//         await connect();
//         return true;
//       }
//       return false;
//     },
//     disconnectFromServer: () => {
//       if (isConnected) {
//         disconnect();
//         return true;
//       }
//       return false;
//     },
//     getConnectionStatus: () => {
//       return { isConnected, status };
//     },
//   }));

//   // Update terminal dimensions when window is resized
//   useEffect(() => {
//     const handleResize = () => {
//       if (fitAddonRef.current) {
//         setTimeout(() => fitAddonRef.current.fit(), 100);
//       }
//     };

//     window.addEventListener('resize', handleResize);
//     return () => {
//       window.removeEventListener('resize', handleResize);
//     };
//   }, []);

//   // Clean up WebSocket on unmount
//   useEffect(() => {
//     return () => {
//       disconnect();
//     };
//   }, []);

//   // Update the Connect MCP button state
//   const updateConnectButton = useCallback((connected) => {
//     const $button = $('.mcp-connect-btn');
//     if (connected) {
//       $button
//         .removeClass('btn-primary')
//         .addClass('btn-success')
//         .html(`
//         <i class="fa fa-check mr-1"></i> ${__('Connected')}
//       `);
//     } else {
//       $button
//         .removeClass('btn-success')
//         .addClass('btn-primary')
//         .html(`
//         <i class="fa fa-plug mr-1"></i> ${__('Connect MCP')}
//       `);
//     }
//   }, []);

//   // Log terminal events for auditing
//   const logTerminalEvent = useCallback(
//     (eventType, details = null, commandType = null) => {
//       frappe.call({
//         method: 'erpnext_mcp_server.api.terminal.log_terminal_session',
//         args: {
//           session_id: sessionId,
//           action: eventType,
//           details: details,
//           command_type: commandType,
//         },
//         callback: function (r) {
//           if (r.exc) {
//             console.error('Failed to log terminal event:', r.exc);
//           }
//         },
//       });
//     },
//     [sessionId]
//   );

//   // Create a terminal session
//   const createTerminalSession = async () => {
//     try {
//       return new Promise((resolve, reject) => {
//         frappe.call({
//           method: 'erpnext_mcp_server.api.terminal.create_terminal_session',
//           callback: function (r) {
//             if (r.message && r.message.success) {
//               setSessionId(r.message.session_id);
//               resolve(r.message.session_id);
//             } else {
//               reject(
//                 new Error(
//                   r.message?.error || 'Failed to create terminal session'
//                 )
//               );
//             }
//           },
//           error: function (err) {
//             reject(err);
//           },
//         });
//       });
//     } catch (error) {
//       console.error('Error creating terminal session:', error);
//       throw error;
//     }
//   };

//   // Connect to the MCP Server
//   const connect = async () => {
//     try {
//       // Update status
//       setStatus({ type: 'connecting', message: 'Connecting...' });

//       // Update button state
//       updateConnectButton(false);
//       $('.mcp-connect-btn').html(
//         '<i class="fa fa-spinner fa-spin mr-1"></i> ' + __('Connecting...')
//       );

//       // Create a terminal session
//       const session_id = await createTerminalSession();
//       setSessionId(session_id);

//       // Get the WebSocket URL
//       // const site_name = frappe.boot.sitename || '';
//       // const websocket_url = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//` +
//       //                      `${window.location.host}/${site_name}/api/websocket/terminal?session_id=${session_id}`;

//       // Close any existing connection
//       // if (websocketRef.current) {
//       //   websocketRef.current.close();
//       // }

//       // Create new WebSocket connection
//       // websocketRef.current = new WebSocket(websocket_url);

//       // Create the attach addon for the WebSocket
//       // const attachAddon = new AttachAddon(websocketRef.current);

//       // Set up event handlers for the WebSocket
//       // websocketRef.current.onopen = () => {
//       //   // Update UI state
//       //   setIsConnected(true);
//       //   setStatus({ type: 'connected', message: 'Connected' });
//       //   updateConnectButton(true);

//       //   // Update addons to include both FitAddon and AttachAddon
//       //   setAddons([fitAddonRef.current, attachAddon]);

//       //   // Fit the terminal and focus it
//       //   if (xtermRef.current) {
//       //     fitAddonRef.current.fit();
//       //     xtermRef.current.terminal.focus();

//       //     // Send terminal size to server
//       //     const { cols, rows } = xtermRef.current.terminal;
//       //     frappe.call({
//       //       method: 'erpnext_mcp_server.api.terminal.resize_terminal',
//       //       args: {
//       //         session_id: session_id,
//       //         cols: cols,
//       //         rows: rows
//       //       }
//       //     });
//       //   }

//       //   // Log connection
//       //   logTerminalEvent('Connect', 'Terminal connection established');
//       // };

//       // websocketRef.current.onclose = (event) => {
//       //   handleDisconnect(event);
//       // };

//       // websocketRef.current.onerror = (error) => {
//       //   console.error('WebSocket error:', error);
//       //   if (xtermRef.current) {
//       //     xtermRef.current.terminal.writeln('\r\n\x1b[31mWebSocket error occurred\x1b[0m');
//       //   }
//       //   logTerminalEvent('Error', 'WebSocket error occurred');
//       // };

//       // Get Socket.IO port from Frappe
//       const socketio_port = frappe.boot.socketio_port || 9000;

//       console.log('socketio_port', socketio_port);

//       // Close any existing connection
//       if (socketRef.current) {
//         socketRef.current.disconnect();
//       }

//       // Create new Socket.IO connection
//       // Create the URL with the correct protocol and port
//       const protocol =
//         window.location.protocol === 'https:' ? 'wss://' : 'ws://';
//       const host = window.location.hostname;
//       const socketUrl = `${protocol}${host}:${socketio_port}`;

//       console.log('Connecting to Socket.IO at:', socketUrl);

//       // Create new Socket.IO connection using Frappe's global io object
//       // socketRef.current = io.connect(null, {
//       //   port: socketio_port,
//       //   reconnection: true,
//       //   reconnectionDelay: 1000,
//       //   reconnectionAttempts: 5,
//       // });

//       socketRef.current = io(socketUrl, {
//         reconnection: true,
//         reconnectionDelay: 1000,
//         reconnectionAttempts: 5,
//         transports: ['websocket'],
//       });

//       // Set up event handlers for Socket.IO
//       socketRef.current.on('connect', () => {
//         console.log('Socket.IO connected');

//         // Update UI state
//         setIsConnected(true);
//         setStatus({ type: 'connected', message: 'Connected' });
//         updateConnectButton(true);

//         // Register this client for the terminal session
//         socketRef.current.emit('terminal:connect', {
//           session_id: session_id,
//         });

//         // Set up terminal with fit addon only
//         setAddons([fitAddonRef.current]);

//         // Ensure terminal is initialized before trying to access it
//         setTimeout(() => {
//           // Check if terminal exists and is initialized
//           if (xtermRef.current && xtermRef.current.terminal) {
//             try {
//               // Fit the terminal
//               if (fitAddonRef.current) {
//                 fitAddonRef.current.fit();
//               }

//               // Focus the terminal
//               xtermRef.current.terminal.focus();

//               // Send terminal size to server
//               const { cols, rows } = xtermRef.current.terminal;
//               socketRef.current.emit('terminal:resize', {
//                 session_id: session_id,
//                 cols: cols,
//                 rows: rows,
//               });
//             } catch (err) {
//               console.error('Error initializing terminal:', err);
//             }
//           } else {
//             console.warn('Terminal not initialized yet');
//           }
//         }, 500); // Add a small delay to ensure terminal is fully initialized

//         // Log connection
//         logTerminalEvent('Connect', 'Terminal connection established');

//         // Fit the terminal and focus it
//         if (xtermRef.current) {
//           fitAddonRef.current.fit();
//           xtermRef.current.terminal.focus();

//           // Send terminal size to server
//           const { cols, rows } = xtermRef.current.terminal;
//           socketRef.current.emit('terminal:resize', {
//             session_id: session_id,
//             cols: cols,
//             rows: rows,
//           });
//         }

//         // Log connection
//         logTerminalEvent('Connect', 'Terminal connection established');
//       });

//       socketRef.current.on('disconnect', () => {
//         console.log('Socket.IO disconnected');
//         handleDisconnect({
//           wasClean: false,
//           code: 1000,
//           reason: 'Socket.IO disconnected',
//         });
//       });

//       socketRef.current.on('error', (error) => {
//         console.error('Socket.IO error:', error);
//         if (xtermRef.current && xtermRef.current.terminal) {
//           xtermRef.current.terminal.writeln(
//             '\r\n\x1b[31mSocket.IO error occurred\x1b[0m'
//           );
//         }
//         logTerminalEvent('Error', 'Socket.IO error occurred');
//       });

//       // Handle terminal data from server
//       socketRef.current.on('terminal:output', (data) => {
//         if (xtermRef.current && xtermRef.current.terminal) {
//           // Write data to the terminal
//           const text =
//             typeof data === 'string' ? data : new TextDecoder().decode(data);
//           xtermRef.current.terminal.write(text);
//         }
//       });

//       // Set up terminal input handler
//       if (xtermRef.current && xtermRef.current.terminal) {
//         // Remove any existing listeners
//         xtermRef.current.terminal.onData(null);

//         // Add new listener
//         xtermRef.current.terminal.onData((data) => {
//           if (socketRef.current && socketRef.current.connected) {
//             socketRef.current.emit('terminal:input', {
//               session_id: session_id,
//               data: data,
//             });
//           }
//         });
//       }
//     } catch (error) {
//       console.error('Connection error:', error);
//       if (xtermRef.current && xtermRef.current.terminal) {
//         xtermRef.current.terminal.writeln(
//           `\r\n\x1b[31mError: ${error.message || 'Connection failed'}\x1b[0m`
//         );
//       }
//       setStatus({ type: 'error', message: 'Connection error' });
//       updateConnectButton(false);
//       logTerminalEvent(
//         'Error',
//         `Connection error: ${error.message || 'Unknown error'}`
//       );
//     }
//   };

//   // Disconnect from the MCP Server
//   const disconnect = () => {
//     try {
//       // Close Socket.IO connection
//       if (socketRef.current) {
//         socketRef.current.disconnect();
//         socketRef.current = null;
//       }

//       // Close the terminal session on the server
//       if (sessionId) {
//         frappe.call({
//           method: 'erpnext_mcp_server.api.terminal.close_terminal_session',
//           args: {
//             session_id: sessionId,
//           },
//           callback: function (r) {
//             if (!r.message || !r.message.success) {
//               console.error(
//                 'Failed to close terminal session:',
//                 r.message?.error || 'Unknown error'
//               );
//             }
//           },
//         });
//       }

//       // Update state
//       setIsConnected(false);
//       setStatus({ type: 'disconnected', message: 'Disconnected' });
//       setAddons([fitAddonRef.current]); // Keep only FitAddon

//       // Update button
//       updateConnectButton(false);

//       // Log disconnection
//       logTerminalEvent('Disconnect', 'Terminal disconnected');

//       // Clear session ID
//       setSessionId(null);
//     } catch (error) {
//       console.error('Error disconnecting:', error);
//     }
//   };

//   // Handle WebSocket disconnection
//   const handleDisconnect = (event) => {
//     // Only handle if currently connected
//     if (!isConnected) return;

//     setIsConnected(false);
//     setStatus({ type: 'disconnected', message: 'Disconnected' });
//     setAddons([fitAddonRef.current]); // Remove the AttachAddon

//     // Update button
//     updateConnectButton(false);

//     if (xtermRef.current) {
//       if (event.wasClean) {
//         xtermRef.current.terminal.writeln(
//           '\r\n\x1b[33mConnection closed cleanly\x1b[0m'
//         );
//       } else {
//         xtermRef.current.terminal.writeln(
//           `\r\n\x1b[31mConnection closed unexpectedly. Code: ${event.code}\x1b[0m`
//         );
//         if (event.reason) {
//           xtermRef.current.terminal.writeln(
//             `\x1b[31mReason: ${event.reason}\x1b[0m`
//           );
//         }
//       }
//     }

//     // Log disconnection details
//     logTerminalEvent(
//       'Disconnect',
//       `Connection closed: ${event.wasClean ? 'Clean' : 'Unexpected'}, Code: ${event.code}, Reason: ${event.reason || 'None'}`
//     );
//   };

//   // Handle mouse drag to resize terminal
//   const handleMouseDown = (e) => {
//     e.preventDefault();

//     const startY = e.clientY;
//     const startHeight = terminalHeight;

//     const onMouseMove = (mouseMoveEvent) => {
//       // Calculate new height
//       const deltaY = startY - mouseMoveEvent.clientY;
//       const newHeight = startHeight + deltaY;

//       // Apply constraints
//       const newTerminalHeight = Math.max(
//         MIN_TERMINAL_HEIGHT,
//         Math.min(newHeight, MAX_TERMINAL_HEIGHT)
//       );

//       setTerminalHeight(newTerminalHeight);
//     };

//     const onMouseUp = () => {
//       document.removeEventListener('mousemove', onMouseMove);
//       document.removeEventListener('mouseup', onMouseUp);

//       // Fit terminal to new size
//       if (fitAddonRef.current && xtermRef.current) {
//         setTimeout(() => {
//           fitAddonRef.current.fit();

//           // Send terminal size to server
//           if (isConnected && sessionId) {
//             const { cols, rows } = xtermRef.current.terminal;
//             frappe.call({
//               method: 'erpnext_mcp_server.api.terminal.resize_terminal',
//               args: {
//                 session_id: sessionId,
//                 cols: cols,
//                 rows: rows,
//               },
//             });
//           }
//         }, 100);
//       }
//     };

//     document.addEventListener('mousemove', onMouseMove);
//     document.addEventListener('mouseup', onMouseUp);
//   };

//   // Toggle terminal size between min and max
//   const toggleSize = () => {
//     const newHeight =
//       terminalHeight === MAX_TERMINAL_HEIGHT
//         ? MIN_TERMINAL_HEIGHT
//         : MAX_TERMINAL_HEIGHT;

//     setTerminalHeight(newHeight);

//     // Fit terminal to new size
//     if (fitAddonRef.current && xtermRef.current) {
//       setTimeout(() => {
//         fitAddonRef.current.fit();

//         // Send terminal size to server
//         if (isConnected && sessionId) {
//           const { cols, rows } = xtermRef.current.terminal;
//           frappe.call({
//             method: 'erpnext_mcp_server.api.terminal.resize_terminal',
//             args: {
//               session_id: sessionId,
//               cols: cols,
//               rows: rows,
//             },
//           });
//         }
//       }, 100);
//     }
//   };

//   return (
//     <div className="mcp-terminal-container" ref={containerRef}>
//       {/* Terminal resize handle */}
//       <div className="terminal-resize-handle" onMouseDown={handleMouseDown}>
//         <i className="fa fa-grip-lines"></i>
//       </div>

//       {/* Terminal header with controls */}
//       <div className="terminal-header">
//         <div className="terminal-status">
//           <span className={`terminal-status-indicator ${status.type}`}></span>
//           <span>{status.message}</span>
//           {sessionId && (
//             <span className="ml-2 text-muted text-xs">
//               Session: {sessionId.substring(0, 8)}...
//             </span>
//           )}
//         </div>

//         <div className="terminal-controls">
//           <button
//             className={`btn btn-sm ${isConnected ? 'btn-danger' : 'btn-primary'}`}
//             onClick={isConnected ? disconnect : connect}
//           >
//             {isConnected ? 'Disconnect' : 'Connect'}
//           </button>

//           <button
//             className="btn btn-sm btn-icon ml-2"
//             onClick={toggleSize}
//             title={
//               terminalHeight === MAX_TERMINAL_HEIGHT ? 'Minimize' : 'Maximize'
//             }
//           >
//             <i
//               className={`fa fa-${terminalHeight === MAX_TERMINAL_HEIGHT ? 'compress' : 'expand'}`}
//             ></i>
//           </button>

//           <button
//             className="btn btn-sm btn-icon ml-2"
//             onClick={() => {
//               if (xtermRef.current) {
//                 xtermRef.current.terminal.clear();
//               }
//             }}
//             title="Clear terminal"
//           >
//             <i className="fa fa-eraser"></i>
//           </button>
//         </div>
//       </div>

//       {/* Terminal container */}
//       <div
//         className="terminal-container"
//         style={{ height: `${terminalHeight}px` }}
//       >
//         <XTerm
//           ref={xtermRef}
//           className="xterm"
//           addons={addons}
//           options={{
//             cursorBlink: true,
//             fontFamily: 'monospace',
//             fontSize: 14,
//             theme: {
//               background: '#1e1e1e',
//               foreground: '#f0f0f0',
//             },
//           }}
//         />
//       </div>
//     </div>
//   );
// });

// export default App;

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
import '@xterm/xterm/css/xterm.css';
import { io } from 'socket.io-client';
import './styles/xterm.css';
import './styles/terminal.css';

function App() {
  const terminalRef = useRef(null);
  const socketRef = useRef(null);
  const termRef = useRef(null);
  const fitAddonRef = useRef(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
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

    console.log('term App.jsx', term);

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
    console.log('ENV App.jsx', process.env.NODE_ENV);
    console.log('sitename App.jsx', sitename);
    console.log('socket_port App.jsx', socketio_port);

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

    console.log('socketRef', socketRef);

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
    <div className="page-container">
      {/* Header */}
      <header className="navbar">
        <div id="mcp__terminal" className="container">
          <div className="navbar-left">
            <div className="indicator red"></div>
            <div className="indicator yellow"></div>
            <div className="indicator green"></div>
            <span className="ml-2 text-muted">{__('Web Terminal')}</span>
          </div>
          <div className="navbar-right">
            <div className="indicator-label">
              <div
                className={`indicator ${isConnected ? 'green' : 'red'}`}
              ></div>
              <span className="text-muted small">
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-section">
        <div className="terminal-wrapper">
          <div
            ref={terminalRef}
            className="terminal-body"
            style={{ minHeight: '400px', height: 'calc(100vh - 12rem)' }}
          />
        </div>
      </main>

      {/* Footer */}
      <footer className="footer">
        <div className="container">
          <p className="text-muted small text-center">
            Press Ctrl+C to clear the terminal • Ctrl+L to clear the screen
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;

import React, {
  useState,
  useEffect,
  useRef,
  forwardRef,
  useImperativeHandle,
} from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';
import './styles/xterm.css';
import './styles/terminal.css';

const App = forwardRef((props, ref) => {
  console.log('props', props);
  console.log('frappe.realtime', frappe.realtime);
  const terminalRef = useRef(null);
  // const socketRef = useRef(null);
  const termRef = useRef(null);
  const fitAddonRef = useRef(null);
  const [isConnected, setIsConnected] = useState(false);

  frappe.realtime.init();

  frappe.realtime.on('event_name', (data) => {
    console.log(data);
  });

  // Expose methods to parent component
  useImperativeHandle(ref, () => ({
    connectToServer: () => {
      return false;
    },
    disconnectFromServer: () => {
      return false;
    },
    focusTerminal: () => {
      if (termRef.current) {
        termRef.current.focus();
      }
    },
    getConnectionStatus: () => {
      return {
        isConnected: frappe.realtime.socket.connected || false,
        status: frappe.realtime.socket.connected ? 'connected' : 'disconnected',
      };
    },
  }));

  useEffect(() => {
    const term = new Terminal({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: 'Menlo, Monaco, "Courier New", monospace',
      theme: {
        background: '#1a1b26',
        foreground: '#a9b1d6',
        cursor: '#c0caf5',
        cursorAccent: '#1a1b26',
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
      term.focus();
    }

    // Connection status updates
    const handleConnect = () => {
      console.log('Connected to Frappe realtime');
      setIsConnected(true);

      // Register this terminal with the server
      frappe.realtime.emit('mcp:register', {
        session_id: frappe.session.user || 'anonymous',
        rows: term.rows,
        cols: term.cols,
      });

      term.write('\r\n\x1b[32mConnected to MCP Server\x1b[0m\r\n\r\n');
      term.focus();
    };

    const handleDisConnect = (reason) => {
      console.log('Disconnected from server: ', reason);
      setIsConnected(false);
      term.write(
        '\r\n\x1b[33mDisconnected from server: ' + reason + '\x1b[0m\r\n'
      );
    };

    // Set up event listeners
    frappe.realtime.on('connect', handleConnect);
    frappe.realtime.on('disconnect', handleDisConnect);

    // Handle terminal output
    frappe.realtime.on('mcp:output', (data) => {
      // Handle output data from server
      if (typeof data === 'string') {
        term.write(data);
      } else if (data && data.data) {
        term.write(data.data);
      }
    });

    // Terminal input handler
    term.onData((data) => {
      console.log('data', data);
      frappe.realtime.init();
      frappe.realtime.emit('mcp:input', { data });
    });

    // Terminal resize handler
    term.onResize(({ rows, cols }) => {
      frappe.realtime.emit('mcp:resize', { rows, cols });
    });

    // Window resize handler
    const handleResize = () => {
      if (fitAddonRef.current && termRef.current) {
        fitAddonRef.current.fit();
      }
    };

    window.addEventListener('resize', handleResize);

    // Clean up on unmount
    return () => {
      window.removeEventListener('resize', handleResize);

      if (termRef.current) {
        termRef.current.dispose();
      }

      // Remove event listeners
      frappe.realtime.off('connect');
      frappe.realtime.off('disconnect');
      frappe.realtime.off('mcp:output');
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
            <span className="ml-2 text-muted">{__('MCP Terminal')}</span>
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
            Press Ctrl+C to interrupt • Ctrl+L to clear the screen
          </p>
        </div>
      </footer>
    </div>
  );
});

export default App;

import { useEffect, useRef, useState } from 'react';
import { Terminal as XTerm } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';
import { initSocket } from '../socket';
import type { Socket } from 'socket.io-client';
import type { DefaultEventsMap } from '@socket.io/component-emitter';

function Terminal() {
  const terminalRef = useRef(null);
  const fitAddonRef = useRef(new FitAddon());
  const socketRef = useRef<Socket<DefaultEventsMap, DefaultEventsMap> | null>(
    null
  );
  const xtermRef = useRef<XTerm | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Initialize xterm
    if (!terminalRef.current) return;

    // Create terminal
    const terminal = new XTerm({
      theme: {
        background: '#1e1e1e',
        foreground: '#ffffff',
        cursor: '#ffffff',
      },
      fontSize: 14,
      fontFamily: 'monospace',
      cursorBlink: true,
      convertEol: true,
    });

    // Load addons
    terminal.loadAddon(fitAddonRef.current);

    // Open terminal
    terminal.open(terminalRef.current);
    xtermRef.current = terminal;

    // Connect to socket
    const socket = initSocket();
    socketRef.current = socket;

    // Handle socket connection events
    socket.on('connect', () => {
      setIsConnected(true);
      setIsLoading(false);

      // Fit terminal and get dimensions
      fitAddonRef.current.fit();
      const dimensions = {
        cols: terminal.cols,
        rows: terminal.rows,
      };

      // Initialize terminal session
      socket.emit('terminal_init', dimensions);

      // Handle terminal data received from server
      socket.on('terminal_data', (data) => {
        terminal.write(data);
      });
    });

    socket.on('disconnect', () => {
      setIsConnected(false);
      terminal.write(
        '\r\n\x1b[31mDisconnected from server. Trying to reconnect...\x1b[0m\r\n'
      );
    });

    socket.on('terminal_error', (error) => {
      console.error('Terminal error:', error);
      terminal.write(`\r\n\x1b[31mError: ${error}\x1b[0m\r\n`);
    });

    // Set up terminal input handling
    terminal.onData((data) => {
      if (isConnected && socketRef.current) {
        socketRef.current.emit('terminal_input', data);
      }
    });

    // Handle resize events
    const handleResize = () => {
      if (
        fitAddonRef.current &&
        xtermRef.current &&
        socketRef.current &&
        isConnected
      ) {
        fitAddonRef.current.fit();
        socketRef.current.emit('terminal_resize', {
          cols: xtermRef.current.cols,
          rows: xtermRef.current.rows,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    // Initial fit
    setTimeout(() => {
      if (fitAddonRef.current) {
        fitAddonRef.current.fit();
      }
    }, 100);

    // Cleanup on unmount
    return () => {
      if (socketRef.current) {
        socketRef.current.off('connect');
        socketRef.current.off('disconnect');
        socketRef.current.off('terminal_data');
        socketRef.current.off('terminal_error');
        socketRef.current.disconnect();
      }

      if (xtermRef.current) {
        xtermRef.current.dispose();
      }

      window.removeEventListener('resize', handleResize);
    };
  }, [isConnected]);

  return (
    <div className="relative">
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-800 bg-opacity-50 z-10">
          <div className="flex items-center">
            <div className="animate-spin mr-3 h-5 w-5 text-white">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <title>Spinner</title>
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
            </div>
            <span className="text-white">Initializing terminal...</span>
          </div>
        </div>
      )}
      <div
        ref={terminalRef}
        className="terminal-container"
        style={{ height: '500px', width: '100%' }}
      />
      <div className="terminal-status p-2 bg-gray-100 border-t">
        {isConnected ? (
          <span className="text-green-600 text-sm flex items-center">
            <span className="inline-block w-2 h-2 rounded-full bg-green-600 mr-2" />
            Connected to MCP Server
          </span>
        ) : (
          <span className="text-yellow-600 text-sm flex items-center">
            <span className="inline-block w-2 h-2 rounded-full bg-yellow-600 mr-2" />
            Disconnected
          </span>
        )}
      </div>
    </div>
  );
}

export default Terminal;

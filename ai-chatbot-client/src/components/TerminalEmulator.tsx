import React, { useState, useEffect, useCallback, memo, useRef } from 'react';
import { createPortal } from 'react-dom';
import { XTerm } from 'react-xtermjs';
import type { ITerminalAddon } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { AttachAddon } from '@xterm/addon-attach';
import { Button } from './ui/button';
import { Loader2 } from 'lucide-react';
import { initSocket } from '../socket';
import type { Socket } from 'socket.io-client';
import type { DefaultEventsMap } from '@socket.io/component-emitter';

type Props = {
  onClose: () => void;
};

const MemorizedXTerm = memo(XTerm);

const TerminalEmulator = ({ onClose }: Props) => {
  const MIN_TERMINAL_HEIGHT = 248;
  const MAX_TERMINAL_HEIGHT = window.innerHeight - 64 - 60; // 64 (navbar) + 60 (terminal header)
  const [terminalHeight, setTerminalHeight] = useState(MIN_TERMINAL_HEIGHT);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [addons, setAddons] = useState<ITerminalAddon[]>([]);
  const fitAddon = new FitAddon();

  const socketRef = useRef<Socket<DefaultEventsMap, DefaultEventsMap> | null>(
    null
  );

  // Initialize terminal and socket connection
  useEffect(() => {
    const socket = initSocket();
    console.log('socket', socket);

    socketRef.current = socket;

    socket.on('connect', () => {
      setIsConnected(true);
      setIsLoading(false);

      // Create addons array with fit and attach addons
      setAddons([fitAddon, new AttachAddon(socket)]);

      // Initialize terminal session
      const { cols, rows } = fitAddon.proposeDimensions();
      socket.emit('terminal_init', { cols, rows });
    });

    socket.on('disconnect', () => {
      setIsConnected(false);
    });

    socket.on('terminal_error', (error) => {
      console.error('Terminal error:', error);
    });

    // Handle terminal resize
    const handleResize = () => {
      if (isConnected && socketRef.current) {
        fitAddon.fit();
        const { cols, rows } = fitAddon.proposeDimensions();
        socketRef.current.emit('teminal_resize', { cols, rows });
      }
    };

    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => {
      socket.off('coannect');
      socket.off('disconnect');
      socket.off('terminal_error');
      socket.disconnect();
      window.removeEventListener('resize', handleResize);
    };
  }, [isConnected]);

  // Handle terminal drag size
  const handleMouseDown = useCallback(
    (e) => {
      e.preventDefault();
      const startY = e.clientY;
      const startHeight = terminalHeight;

      const handleMouseMove = (moveEvent) => {
        const newHeight = startHeight + (startY - moveEvent.clientY);
        setTerminalHeight(
          Math.min(
            Math.max(newHeight, MIN_TERMINAL_HEIGHT),
            MAX_TERMINAL_HEIGHT
          )
        );
      };

      const handleMouseUp = () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
        fitAddon.fit();
      };

      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    },
    [terminalHeight]
  );

  const toggleTerminalSize = () => {
    setTerminalHeight((prevHeight) =>
      prevHeight === MAX_TERMINAL_HEIGHT
        ? MIN_TERMINAL_HEIGHT
        : MAX_TERMINAL_HEIGHT
    );
  };
  return createPortal(
    <div className="fixed bottom-0 left-0 right-0 bg-gray-100 border-t border-gray-300 shadow-lg z-50">
      {/* Resize handle */}
      <div
        className="h-2 w-full bg-gray-200 hover:bg-gray-300 cursor-ns-resize flex items-center justify-center"
        onMouseDown={handleMouseDown}
      >
        <div className="w-8 h-0.5 bg-gray-500 rounded-full" />
      </div>

      {/* Terminal header */}
      <div className="flex justify-between items-center px-4 py-2 bg-white border-b border-gray-300">
        <div className="flex items-center text-gray-700">
          ERPNext Terminal
          {!isConnected && (
            <span className="ml-2 text-xs text-yellow-600">
              (Connecting...)
            </span>
          )}
        </div>
        <div className="flex space-x-2">
          <Button onClick={toggleTerminalSize} variant="ghost" size="sm">
            {terminalHeight === MAX_TERMINAL_HEIGHT ? (
              <span className="material-icons">expand_more</span>
            ) : (
              <span className="material-icons">expand_less</span>
            )}
          </Button>
          <Button onClick={onClose} variant="ghost" size="sm">
            <span className="material-icons">close</span>
            Close
          </Button>
        </div>
      </div>

      {/* Terminal container */}
      <div className="bg-black p-2" style={{ height: `${terminalHeight}px` }}>
        {isLoading ? (
          <div className="h-full flex items-center justify-center text-white">
            <Loader2 className="mr-2" />
            Initializing terminal...
          </div>
        ) : (
          <MemorizedXTerm
            className="h-full w-full"
            addons={addons}
            options={{
              theme: {
                background: '#1e1e1e',
                foreground: '#ffffff',
                cursor: '#ffffff',
              },
              fontSize: 14,
              fontFamily: 'monospace',
              cursorBlink: true,
            }}
          />
        )}
      </div>
    </div>,
    document.body
  );
};

export default TerminalEmulator;

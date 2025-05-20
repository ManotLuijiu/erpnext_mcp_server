import React, { useEffect, useRef } from 'react';
import { Terminal } from '@xterm/xterm';
import '@xterm/xterm/css/xterm.css';

export default function App() {
  const terminalRef = useRef(null);
  const terminalInstanceRef = useRef(null);
  const currentLineBuffer = useRef('');

  console.log('terminalRef', terminalRef);
  console.log('terminalInstanceRef', terminalInstanceRef);

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
    });

    console.log('term', term);

    term.open(terminalRef.current);
    terminalInstanceRef.current = term;

    console.log('terminalInstanceRef.current', terminalInstanceRef.current);

    // Initial greeting
    term.write(
      'MCP Terminal Connected. Type a command and press Enter.\r\n\r\n'
    );

    // Test socket.io
    frappe.realtime.on('item_connector', (data) => {
      console.log('data testing socket.io', data);
    });

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
      // Special key handling
      if (domEvent.key === 'Enter') {
        // Get the current line
        // const currentLine = getCurrentLine(term);

        // console.log('currentLine', currentLine);

        // Testing socket.io
        frappe.realtime.emit('item_connector', (data) => {
          console.log(data);
        });

        // Send command to server
        frappe.realtime.emit('mcp_terminal_input', {
          command: currentLineBuffer.current,
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
  }, []);

  return (
    <div className="h-full w-full p-4 bg-gray-900">
      <div className="text-lg mb-4 text-white">MCP Terminal</div>
      <div
        ref={terminalRef}
        className="h-5/6 w-full border border-gray-700 rounded"
      />
    </div>
  );
}

import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';

export const initMCPTerminal = async (containerId) => {
  try {
    // Wait for container to be ready
    await new Promise((resolve) => setTimeout(resolve, 100));

    const container = document.getElementById(containerId);
    if (!container) throw new Error(`Container ${containerId} not found`);

    console.log('container mcp_chatbot.bundle.js', container);

    // Initialize terminal
    const terminal = new Terminal({
      fontSize: 14,
      fontFamily: 'monospace',
      theme: {
        background: '#1e1e1e',
        foreground: '#ffffff',
      },
      cursorBlink: true,
    });

    const fitAddon = new FitAddon();
    terminal.loadAddon(fitAddon);

    // Find the terminal element within the container
    const terminalElement = container.querySelector('#terminal');
    if (!terminalElement) throw new Error('Terminal element not found');

    terminal.open(terminalElement);
    fitAddon.fit();

    // Basic terminal functionality
    terminal.writeln('Welcome to MCP Terminal!');
    terminal.writeln('Type commands and press Enter to execute');
    showPrompt(terminal);
    // terminal.write('$ ');

    // Setup realtime listeners
    setupRealtimeListeners(terminal);

    // Handle terminal input
    let currentCommand = '';
    terminal.onData((data) => {
      if (data === '\r') {
        // Enter pressed
        executeCommand(terminal, currentCommand);
        currentCommand = '';
      } else if (data === '\x7f') {
        // Backspace
        if (currentCommand.length > 0) {
          currentCommand = currentCommand.slice(0, -1);
          terminal.write('\b \b');
        }
      } else if (data.charCodeAt(0) >= 32 && data.charCodeAt(0) <= 126) {
        // Printable characters
        currentCommand += data;
        terminal.write(data);
      }
    });

    return terminal;
  } catch (error) {
    console.error('Terminal initialization failed:', error);
    throw error;
  }
};

let isPromptVisible = false;

function showPrompt(terminal) {
  console.log('terminal showPrompt', terminal);
  if (!isPromptVisible) {
    const user = frappe.session.user || 'user';
    const site = frappe.boot.sitename || 'erpnext';
    terminal.write(`\x1b[32m${user}@${site}\x1b[0m:\x1b[34m$\x1b[0m `);
    isPromptVisible = true;
  }
}

// function showPrompt(terminal) {
//   terminal.write('\r\n$ ');
// }

function setupRealtimeListeners(terminal) {
  // Listen for terminal output from server
  frappe.realtime.on('terminal_output', (message) => {
    switch (message.type) {
      case 'command':
        terminal.write(`\x1b[33m${message.data}\x1b[0m`); // Yellow for command
        break;

      case 'stdout':
        terminal.write(message.data);
        break;

      case 'stderr':
        terminal.write(`\x1b[31m${message.data}\x1b[0m`); // Red for errors
        break;

      case 'prompt':
        showPrompt(terminal);
        break;
    }
    // if (message.type === 'output') {
    //   terminal.write(message.data);
    // } else if (message.type === 'error') {
    //   terminal.write(`\x1b[31m${message.data}\x1b[0m`); // Red color for errors
    // }
    // showPrompt(terminal);
  });
}

function executeCommand(terminal, command) {
  if (!command.trim()) {
    showPrompt(terminal);
    return;
  }

  terminal.write('\r\n');

  // Send command to server
  frappe.call({
    method: 'erpnext_mcp_server.api.vue_mcp_server.execute_terminal_command',
    args: { command: command },
    callback: (response) => {
      if (!response || response.exc) {
        terminal.write('\x1b[31mError communicating with server\x1b[0m\r\n');
      }
      showPrompt(terminal);
    },
    error: (err) => {
      terminal.write(`\x1b[31mError: ${err.message}\x1b[0m\r\n`);
      showPrompt(terminal);
    },
  });
}

// Auto-initialize if container exists
document.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById('mcp-terminal-app');
  if (container) {
    initMCPTerminal('mcp-terminal-app').catch((err) => {
      console.error('Failed to initialize terminal:', err);
    });
  }
});

// Export for manual initialization
window.initMCPTerminal = initMCPTerminal;

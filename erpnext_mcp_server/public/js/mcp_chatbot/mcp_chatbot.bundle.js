import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';

export const initMCPTerminal = async (containerId) => {
  try {
    // Wait for container to be ready
    await new Promise((resolve) => setTimeout(resolve, 100));

    const container = document.getElementById(containerId);
    if (!container) throw new Error(`Container ${containerId} not found`);

    console.log('container mcp_chatbot.bundle.js', container);
    console.log('Initializing MCP Terminal...');

    // Initialize terminal
    const terminal = new Terminal({
      convertEol: true,
      disableStdin: false,
      cursorBlink: true,
      fontSize: 14,
      fontFamily:
        '"Cascadia Code", "Fira Code", "JetBrains Mono", "Courier New", monospace',
      theme: {
        // background: '#1e1e1e',
        // foreground: '#ffffff',
        background: '#0c0c0c',
        foreground: '#cccccc',
        cursor: '#ffffff',
        cursorAccent: '#000000',
        selection: '#404040',
        black: '#000000',
        red: '#cd3131',
        green: '#0dbc79',
        yellow: '#e5e510',
        blue: '#2472c8',
        magenta: '#bc3fbc',
        cyan: '#11a8cd',
        white: '#e5e5e5',
        brightBlack: '#666666',
        brightRed: '#f14c4c',
        brightGreen: '#23d18b',
        brightYellow: '#f5f543',
        brightBlue: '#3b8eea',
        brightMagenta: '#d670d6',
        brightCyan: '#29b8db',
        brightWhite: '#ffffff',
      },
      cols: 120,
      rows: 30,
      scrollback: 1000,
      tabStopWidth: 4,
    });

    const fitAddon = new FitAddon();
    terminal.loadAddon(fitAddon);

    // Find the terminal element within the container
    const terminalElement = container.querySelector('#terminal');
    if (!terminalElement) throw new Error('Terminal element not found');

    terminal.open(terminalElement);

    // Add some padding to terminal
    // terminalElement.style.padding = '20px';
    // terminalElement.style.margin = '10px';

    fitAddon.fit();

    // Show welcome message with available commands
    showWelcomeMessage(terminal);

    // Basic terminal functionality
    // terminal.writeln('Welcome to MCP Terminal!');
    // terminal.writeln('Type commands and press Enter to execute');
    // showPrompt(terminal);
    // terminal.write('$ ');

    // Setup realtime listeners
    setupRealtimeListeners(terminal);

    // Handle terminal input
    let currentCommand = '';
    let commandHistory = [];
    let historyIndex = -1;
    let isProcessing = false;

    terminal.onData((data) => {
      if (isProcessing) return;

      const code = data.charCodeAt(0);

      switch (code) {
        case 13: // Enter
          if (currentCommand.trim()) {
            commandHistory.push(currentCommand);
            if (commandHistory.length > 100) {
              commandHistory.shift();
            }
            historyIndex = -1;
            executeCommand(terminal, currentCommand.trim());
            isProcessing = true;
          } else {
            terminal.write('\r\n');
            showPrompt(terminal);
          }
          currentCommand = '';
          break;

        case 127: // Backspace
          if (currentCommand.length > 0) {
            currentCommand = currentCommand.slice(0, -1);
            terminal.write('\b \b');
          }
          break;

        case 27: // Escape sequences (arrow keys)
          // Handle in next data events
          break;

        case 3: // Ctrl+C
          terminal.write('^C\r\n');
          currentCommand = '';
          showPrompt(terminal);
          break;

        case 12: // Ctrl+L
          terminal.clear();
          showWelcomeMessage(terminal);
          showPrompt(terminal);
          break;

        case 9: // Tab - show available commands
          showAvailableCommands(terminal);
          break;

        default:
          // Handle arrow keys
          if (data === '\x1b[A' && commandHistory.length > 0) {
            // Up arrow
            if (historyIndex < commandHistory.length - 1) {
              historyIndex++;
              replaceCurrentLine(
                terminal,
                commandHistory[commandHistory.length - 1 - historyIndex]
              );
              currentCommand =
                commandHistory[commandHistory.length - 1 - historyIndex];
            }
          } else if (data === '\x1b[B' && commandHistory.length > 0) {
            // Down arrow
            if (historyIndex > 0) {
              historyIndex--;
              replaceCurrentLine(
                terminal,
                commandHistory[commandHistory.length - 1 - historyIndex]
              );
              currentCommand =
                commandHistory[commandHistory.length - 1 - historyIndex];
            } else if (historyIndex === 0) {
              historyIndex = -1;
              replaceCurrentLine(terminal, '');
              currentCommand = '';
            }
          } else if (code >= 32 && code <= 126) {
            // Printable characters
            currentCommand += data;
            terminal.write(data);
          }
      }
      // if (data === '\r') {
      //   // Enter pressed
      //   executeCommand(terminal, currentCommand);
      //   currentCommand = '';
      // } else if (data === '\x7f') {
      //   // Backspace
      //   if (currentCommand.length > 0) {
      //     currentCommand = currentCommand.slice(0, -1);
      //     terminal.write('\b \b');
      //   }
      // } else if (data.charCodeAt(0) >= 32 && data.charCodeAt(0) <= 126) {
      //   // Printable characters
      //   currentCommand += data;
      //   terminal.write(data);
      // }
    });

    // Handle processing state
    window.setProcessingState = (processing) => {
      isProcessing = processing;
    };

    return terminal;
  } catch (error) {
    console.error('Terminal initialization failed:', error);
    throw error;
  }
};

function showWelcomeMessage(terminal) {
  const welcome = `\x1b[36m
╔══════════════════════════════════════════════════════════════════════════════╗
║                           🚀 ERPNext MCP Terminal                             
║                      Model Context Protocol Interface                        ║
║                                                                              ║
║  Type 'help' for available commands or 'Tab' to see quick commands           ║
╚══════════════════════════════════════════════════════════════════════════════╝\x1b[0m

\x1b[32m✅ Terminal initialized successfully!\x1b[0m
\x1b[33m💡 Pro tip: Use Tab to see available commands, ↑/↓ for command history\x1b[0m

`;
  terminal.write(welcome);
  showPrompt(terminal);
}

function showAvailableCommands(terminal) {
  terminal.write('\r\n\x1b[36m📚 Quick Commands:\x1b[0m\r\n');
  terminal.write(
    '\x1b[90m┌─────────────────────┬─────────────────────────────────────────────────────┐\x1b[0m\r\n'
  );
  terminal.write(
    '\x1b[90m│\x1b[0m \x1b[33mCommand\x1b[0m             \x1b[90m│\x1b[0m \x1b[37mDescription\x1b[0m                                     \x1b[90m│\x1b[0m\r\n'
  );
  terminal.write(
    '\x1b[90m├─────────────────────┼─────────────────────────────────────────────────────┤\x1b[0m\r\n'
  );
  terminal.write(
    '\x1b[90m│\x1b[0m help                \x1b[90m│\x1b[0m Show detailed help and usage examples              \x1b[90m│\x1b[0m\r\n'
  );
  terminal.write(
    '\x1b[90m│\x1b[0m list_doctypes       \x1b[90m│\x1b[0m List all available document types                  \x1b[90m│\x1b[0m\r\n'
  );
  terminal.write(
    '\x1b[90m│\x1b[0m get_document        \x1b[90m│\x1b[0m Get specific document (e.g., Customer "CUST-001") \x1b[90m│\x1b[0m\r\n'
  );
  terminal.write(
    '\x1b[90m│\x1b[0m search_documents    \x1b[90m│\x1b[0m Search documents by criteria                       \x1b[90m│\x1b[0m\r\n'
  );
  terminal.write(
    '\x1b[90m│\x1b[0m execute_sql         \x1b[90m│\x1b[0m Execute SQL query (SELECT only)                    \x1b[90m│\x1b[0m\r\n'
  );
  terminal.write(
    '\x1b[90m│\x1b[0m get_system_info     \x1b[90m│\x1b[0m Show system information                            \x1b[90m│\x1b[0m\r\n'
  );
  terminal.write(
    '\x1b[90m│\x1b[0m list_files          \x1b[90m│\x1b[0m List files in directory                            \x1b[90m│\x1b[0m\r\n'
  );
  terminal.write(
    '\x1b[90m│\x1b[0m clear               \x1b[90m│\x1b[0m Clear terminal screen                              \x1b[90m│\x1b[0m\r\n'
  );
  terminal.write(
    '\x1b[90m│\x1b[0m status              \x1b[90m│\x1b[0m Show connection status                             \x1b[90m│\x1b[0m\r\n'
  );
  terminal.write(
    '\x1b[90m└─────────────────────┴─────────────────────────────────────────────────────┘\x1b[0m\r\n'
  );
  terminal.write(
    '\r\n\x1b[33m💡 Type any command above or "help" for detailed examples\x1b[0m\r\n'
  );
  showPrompt(terminal);
}

function replaceCurrentLine(terminal, newCommand) {
  // Move to beginning of line and clear it
  terminal.write('\r\x1b[K');
  showPrompt(terminal);
  terminal.write(newCommand);
}

// let isPromptVisible = false;

// function showPrompt(terminal) {
//   console.log('terminal showPrompt', terminal);
//   if (!isPromptVisible) {
//     const user = frappe.session.user || 'user';
//     const site = frappe.boot.sitename || 'erpnext';
//     terminal.write(`\x1b[32m${user}@${site}\x1b[0m:\x1b[34m$\x1b[0m `);
//     isPromptVisible = true;
//   }
// }

function showPrompt(terminal) {
  if (!terminal) return;

  const user = frappe?.session?.user || 'user';
  const site = frappe?.boot?.sitename || 'erpnext';
  const timestamp = new Date().toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
  });
  const currentPath = '/Users/manolj/frappe-bench/sites'; // You can make this dynamic

  // Enhanced prompt with colors and structure
  terminal.write(
    `\r\n\x1b[90m┌─[\x1b[32m${user}\x1b[90m@\x1b[34m${site}\x1b[90m] \x1b[35m${timestamp}\x1b[90m\x1b[0m\r\n`
  );
  terminal.write(
    `\x1b[90m└─[\x1b[36m${currentPath}\x1b[90m] \x1b[32m$\x1b[0m `
  );
}

// function showPrompt(terminal) {
//   terminal.write('\r\n$ ');
// }

function setupRealtimeListeners(terminal) {
  // Listen for terminal output from server
  frappe.realtime.on('terminal_output', (message) => {
    window.setProcessingState && window.setProcessingState(false);

    switch (message.type) {
      case 'command':
        // terminal.write(`\x1b[33m${message.data}\x1b[0m`);
        // terminal.write(`\r\n\x1b[33m${message.data}\x1b[0m `);
        terminal.write(
          `\r\n\x1b[90m▶\x1b[0m \x1b[33m${message.data}\x1b[0m\r\n`
        );
        break;

      case 'stdout':
        // terminal.write(message.data);
        // terminal.write(`\r\n${message.data}`);
        terminal.write(`\r\n${formatOutput(message.data)}\r\n`);
        break;

      case 'stderr':
        // terminal.write(`\x1b[31m${message.data}\x1b[0m`);
        // terminal.write(`\r\n\x1b[31m${message.data}\x1b[0m`);
        terminal.write(`\r\n\x1b[31m❌ ${message.data}\x1b[0m\r\n`);
        break;

      case 'success':
        terminal.write(`\r\n\x1b[32m✅ ${message.data}\x1b[0m\r\n`);
        break;

      case 'info':
        terminal.write(`\r\n\x1b[36mℹ️  ${message.data}\x1b[0m\r\n`);
        break;

      case 'warning':
        terminal.write(`\r\n\x1b[33m⚠️  ${message.data}\x1b[0m\r\n`);
        break;

      default:
        terminal.write(`\r\n${message.data}\r\n`);

      // case 'prompt':
      //   showPrompt(terminal);
      //   break;
    }
    // if (message.type === 'output') {
    //   terminal.write(message.data);
    // } else if (message.type === 'error') {
    //   terminal.write(`\x1b[31m${message.data}\x1b[0m`); // Red color for errors
    // }
    showPrompt(terminal);
  });

  // Handle connection status
  frappe.realtime.on('mcp_status', (message) => {
    switch (message.status) {
      case 'connected':
        terminal.write(`\r\n\x1b[32m🟢 MCP Server connected\x1b[0m\r\n`);
        break;
      case 'disconnected':
        terminal.write(`\r\n\x1b[31m🔴 MCP Server disconnected\x1b[0m\r\n`);
        break;
      case 'error':
        terminal.write(
          `\r\n\x1b[31m❌ Connection error: ${message.error}\x1b[0m\r\n`
        );
        break;
    }
    showPrompt(terminal);
  });
}

function formatOutput(data) {
  if (typeof data === 'string') {
    return data;
  }

  if (typeof data === 'object') {
    try {
      return JSON.stringify(data, null, 2);
    } catch (e) {
      console.error('e', e);
      return String(data);
    }
  }

  return String(data);
}

function executeCommand(terminal, command) {
  if (!command.trim()) {
    // terminal.write('\r\n');
    // showPrompt(terminal);
    return;
  }

  // Handle built-in commands
  const lowerCommand = command.toLowerCase().trim();

  if (lowerCommand === 'clear' || lowerCommand === 'cls') {
    terminal.clear();
    showWelcomeMessage(terminal);
    return;
  }

  if (lowerCommand === 'help') {
    showDetailedHelp(terminal);
    return;
  }

  if (lowerCommand === 'status') {
    showSystemStatus(terminal);
    return;
  }

  // Show command being executed
  terminal.write(`\r\n\x1b[90m▶\x1b[0m \x1b[33mExecuting: ${command}\x1b[0m`);
  // terminal.write(`\r\n\x1b[90m⏳ Processing...\x1b[0m\r\n`);

  // window.isProcessing = true;
  // terminal.write('\r\n');

  // Send command to server
  frappe.call({
    method: 'erpnext_mcp_server.api.vue_mcp_server.execute_terminal_command',
    args: { command: command },
    callback: (response) => {
      console.log('Command executed:', response);
      window.setProcessingState && window.setProcessingState(false);

      if (response && response.message) {
        // Success response
        if (response.message.success !== false) {
          terminal.write(`\x1b[32m✅ Command completed\x1b[0m\r\n`);
        }
      } else {
        terminal.write(`\x1b[33m⚠️  No response from server\x1b[0m\r\n`);
      }
      // window.isProcessing = false;
      // if (!response || response.exc) {
      //   terminal.write('\x1b[31mError communicating with server\x1b[0m\r\n');
      // }
      showPrompt(terminal);
    },
    error: (err) => {
      console.error('Command execution failed:', err);
      window.setProcessingState && window.setProcessingState(false);
      // window.isProcessing = false;
      // terminal.write(`\x1b[31mError: ${err.message}\x1b[0m\r\n`);
      terminal.write(
        `\x1b[31m❌ Error: ${err.message || 'Command execution failed'}\x1b[0m\r\n`
      );
      showPrompt(terminal);
    },
  });
}

function showDetailedHelp(terminal) {
  const help = `\r\n\x1b[36m📖 ERPNext MCP Terminal - Detailed Help\x1b[0m\r\n
\x1b[33m📄 Document Operations:\x1b[0m
  \x1b[32mlist_doctypes\x1b[0m                     - List all available document types
  \x1b[32mget_document\x1b[0m <doctype> <name>     - Get specific document
    Example: get_document Customer "CUST-00001"
    Example: get_document "Sales Invoice" "SINV-2024-00001"
  
  \x1b[32msearch_documents\x1b[0m <doctype> <query> - Search documents
    Example: search_documents Customer "John Doe"
    Example: search_documents Item "laptop"

\x1b[33m🗄️  Database Operations:\x1b[0m
  \x1b[32mexecute_sql\x1b[0m <query>              - Execute SQL query (SELECT only)
    Example: execute_sql "SELECT name, customer_name FROM \`tabCustomer\` LIMIT 10"
    Example: execute_sql "SELECT COUNT(*) FROM \`tabSales Invoice\`"

\x1b[33m⚙️  System Operations:\x1b[0m
  \x1b[32mget_system_info\x1b[0m                   - Show system information
  \x1b[32mlist_files\x1b[0m <path>                 - List files in directory
  \x1b[32mstatus\x1b[0m                            - Show connection status

\x1b[33m🖥️  Terminal Commands:\x1b[0m
  \x1b[32mhelp\x1b[0m          - Show this help        \x1b[32mclear\x1b[0m    - Clear screen
  \x1b[32mTab\x1b[0m           - Show quick commands    \x1b[32m↑/↓\x1b[0m      - Command history
  \x1b[32mCtrl+C\x1b[0m        - Cancel command         \x1b[32mCtrl+L\x1b[0m   - Clear screen

\x1b[33m💡 Pro Tips:\x1b[0m
  • Use quotes for names with spaces: get_document "Sales Invoice" "SINV-001"
  • Press Tab to see available commands quickly
  • Use arrow keys to navigate command history
  • Type 'status' to check system connection
`;

  terminal.write(help);
  showPrompt(terminal);
}

function showSystemStatus(terminal) {
  const user = frappe?.session?.user || 'Unknown';
  const site = frappe?.boot?.sitename || 'Unknown';
  const version = frappe?.boot?.versions?.frappe || 'Unknown';

  const status = `\r\n\x1b[36m📊 System Status\x1b[0m\r\n
\x1b[90m┌─────────────────────────────────────────────────────────────────┐\x1b[0m
\x1b[90m│\x1b[0m \x1b[33mConnection:\x1b[0m \x1b[32m●\x1b[0m Connected                               \x1b[90m│\x1b[0m
\x1b[90m│\x1b[0m \x1b[33mUser:\x1b[0m       ${user.padEnd(47)} \x1b[90m│\x1b[0m
\x1b[90m│\x1b[0m \x1b[33mSite:\x1b[0m       ${site.padEnd(47)} \x1b[90m│\x1b[0m
\x1b[90m│\x1b[0m \x1b[33mVersion:\x1b[0m    Frappe ${version.padEnd(39)} \x1b[90m│\x1b[0m
\x1b[90m│\x1b[0m \x1b[33mTime:\x1b[0m       ${new Date().toLocaleString().padEnd(47)} \x1b[90m│\x1b[0m
\x1b[90m└─────────────────────────────────────────────────────────────────┘\x1b[0m
`;

  terminal.write(status);
  showPrompt(terminal);
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

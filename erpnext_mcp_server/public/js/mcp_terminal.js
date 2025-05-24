/**
 * Simple MCP Terminal using xterm.js
 */
class MCPTerminal {
  constructor(containerId) {
    this.containerId = containerId;
    this.container = document.getElementById(containerId);
    this.sessionId = null;
    this.commandHistory = [];
    this.historyIndex = -1;
    this.currentCommand = '';
    this.isConnected = false;

    // Available commands for auto-completion
    this.availableCommands = [
      'list_doctypes',
      'get_document',
      'search_documents',
      'create_document',
      'update_document',
      'execute_sql',
      'get_system_info',
      'bench_command',
      'help',
      'clear',
      'exit',
    ];

    this.init();
  }

  init() {
    // Create terminal
    this.terminal = new Terminal({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: 'Monaco, Menlo, "Ubuntu Mono", monospace',
      theme: {
        background: '#1e1e1e',
        foreground: '#ffffff',
        cursor: '#ffffff',
        selection: '#3d3d3d',
      },
      cols: 120,
      rows: 30,
    });

    // Add fit addon
    this.fitAddon = new FitAddon();
    this.terminal.loadAddon(this.fitAddon);

    // Open terminal
    this.terminal.open(this.container);
    this.fitAddon.fit();

    // Setup event handlers
    this.setupEventHandlers();
    this.setupRealtimeEvents();

    // Show welcome and start session
    this.showWelcome();
    this.startSession();
  }

  setupEventHandlers() {
    // Handle terminal input
    this.terminal.onData((data) => {
      this.handleInput(data);
    });

    // Handle window resize
    window.addEventListener('resize', () => {
      this.fitAddon.fit();
    });
  }

  setupRealtimeEvents() {
    if (frappe.realtime) {
      frappe.realtime.on('mcp_session_started', (data) => {
        this.sessionId = data.session_id;
        this.isConnected = true;
        this.write('\r\n✅ MCP session started\r\n');
        this.showPrompt();
      });

      frappe.realtime.on('mcp_command_result', (data) => {
        this.handleCommandResult(data);
      });

      frappe.realtime.on('mcp_session_ended', (data) => {
        this.isConnected = false;
        this.sessionId = null;
        this.write('\r\n🔌 Session ended\r\n');
      });
    }
  }

  handleInput(data) {
    const code = data.charCodeAt(0);

    switch (code) {
      case 13: // Enter
        this.executeCommand();
        break;
      case 127: // Backspace
        this.handleBackspace();
        break;
      case 27: // Escape sequences (arrow keys)
        this.handleEscapeSequence(data);
        break;
      case 3: // Ctrl+C
        this.handleCancel();
        break;
      case 12: // Ctrl+L
        this.clear();
        break;
      case 9: // Tab
        this.handleTabCompletion();
        break;
      default:
        if (code >= 32 && code <= 126) {
          // Printable characters
          this.currentCommand += data;
          this.terminal.write(data);
        }
    }
  }

  handleEscapeSequence(data) {
    if (data === '\x1b[A') {
      // Up arrow
      this.navigateHistory(-1);
    } else if (data === '\x1b[B') {
      // Down arrow
      this.navigateHistory(1);
    }
  }

  navigateHistory(direction) {
    if (this.commandHistory.length === 0) return;

    this.historyIndex += direction;

    if (this.historyIndex < 0) {
      this.historyIndex = 0;
    } else if (this.historyIndex >= this.commandHistory.length) {
      this.historyIndex = this.commandHistory.length;
      this.replaceCurrentLine('');
      return;
    }

    const command = this.commandHistory[this.historyIndex];
    this.replaceCurrentLine(command);
  }

  replaceCurrentLine(newCommand) {
    // Clear current line
    this.terminal.write('\x1b[2K\r');
    this.showPrompt();
    this.terminal.write(newCommand);
    this.currentCommand = newCommand;
  }

  handleBackspace() {
    if (this.currentCommand.length > 0) {
      this.currentCommand = this.currentCommand.slice(0, -1);
      this.terminal.write('\b \b');
    }
  }

  handleCancel() {
    this.currentCommand = '';
    this.write('\r\n^C\r\n');
    this.showPrompt();
  }

  handleTabCompletion() {
    const matches = this.availableCommands.filter((cmd) =>
      cmd.startsWith(this.currentCommand.trim())
    );

    if (matches.length === 1) {
      const completion = matches[0].slice(this.currentCommand.trim().length);
      this.currentCommand += completion + ' ';
      this.terminal.write(completion + ' ');
    } else if (matches.length > 1) {
      this.write('\r\n' + matches.join('  ') + '\r\n');
      this.showPrompt();
      this.terminal.write(this.currentCommand);
    }
  }

  executeCommand() {
    const command = this.currentCommand.trim();
    this.write('\r\n');

    if (command) {
      this.commandHistory.push(command);
      this.historyIndex = this.commandHistory.length;
      this.processCommand(command);
    } else {
      this.showPrompt();
    }

    this.currentCommand = '';
  }

  processCommand(command) {
    if (!this.isConnected) {
      this.write('❌ No active MCP session\r\n');
      this.showPrompt();
      return;
    }

    // Handle built-in commands
    if (this.handleBuiltinCommand(command)) {
      return;
    }

    // Show processing indicator
    this.write('⏳ Processing...\r\n');

    // Parse command and arguments
    const parts = this.parseCommand(command);
    const cmd = parts.command;
    const args = parts.args;

    // Execute MCP command
    this.executeMCPCommand(cmd, args);
  }

  handleBuiltinCommand(command) {
    const cmd = command.toLowerCase().split(' ')[0];

    switch (cmd) {
      case 'clear':
        this.clear();
        return true;
      case 'help':
        this.showHelp();
        return true;
      case 'exit':
        this.endSession();
        return true;
      case 'history':
        this.showHistory();
        return true;
      default:
        return false;
    }
  }

  parseCommand(command) {
    const parts = command.split(' ');
    const cmd = parts[0];
    const args = {};

    // Parse different command formats
    if (cmd === 'get_document' && parts.length >= 3) {
      args.doctype = parts[1];
      args.name = parts.slice(2).join(' ');
    } else if (cmd === 'search_documents' && parts.length >= 3) {
      args.doctype = parts[1];
      args.query = parts.slice(2).join(' ');
    } else if (cmd === 'execute_sql' && parts.length >= 2) {
      args.query = parts.slice(1).join(' ');
    } else if (cmd === 'bench_command' && parts.length >= 2) {
      args.command = parts.slice(1).join(' ');
    } else if (cmd === 'create_document' && parts.length >= 3) {
      args.doctype = parts[1];
      try {
        args.data = JSON.parse(parts.slice(2).join(' '));
      } catch (e) {
        console.log(e);
        this.write('❌ Invalid JSON data for create_document\r\n');
        this.showPrompt();
        return null;
      }
    }

    return { command: cmd, args: args };
  }

  executeMCPCommand(command, args) {
    frappe.call({
      method: 'erpnext_mcp_server.api.terminal.execute_mcp_command',
      args: {
        session_id: this.sessionId,
        command: command,
        args: args,
      },
      callback: (response) => {
        if (!response.message) {
          this.write('❌ No response from server\r\n');
          this.showPrompt();
        }
        // Response will be handled via realtime events
      },
      error: (error) => {
        this.write(`❌ API Error: ${error.message}\r\n`);
        this.showPrompt();
      },
    });
  }

  handleCommandResult(data) {
    if (data.success) {
      if (data.data) {
        // Format and display the result
        const formattedData = this.formatOutput(data.data);
        this.write(formattedData + '\r\n');
      }
      this.write('✅ Command completed\r\n');
    } else {
      this.write(`❌ Error: ${data.error || 'Unknown error'}\r\n`);
    }

    this.showPrompt();
  }

  formatOutput(data) {
    // Try to format JSON data nicely
    try {
      const parsed = JSON.parse(data);
      if (Array.isArray(parsed)) {
        return this.formatArray(parsed);
      } else if (typeof parsed === 'object') {
        return this.formatObject(parsed);
      }
    } catch (e) {
      // Not JSON, return as-is
    }

    return data;
  }

  formatArray(arr) {
    if (arr.length === 0) return '[]';

    let result = '';
    arr.forEach((item, index) => {
      result += `${index + 1}. `;
      if (typeof item === 'object') {
        result += JSON.stringify(item, null, 2).replace(/\n/g, '\r\n    ');
      } else {
        result += item;
      }
      result += '\r\n';
    });

    return result;
  }

  formatObject(obj) {
    return JSON.stringify(obj, null, 2).replace(/\n/g, '\r\n');
  }

  startSession() {
    this.write('🔌 Starting MCP session...\r\n');

    frappe.call({
      method: 'erpnext_mcp_server.api.terminal.start_mcp_session',
      callback: (response) => {
        if (!response.message.success) {
          this.write(
            `❌ Failed to start session: ${response.message.error}\r\n`
          );
          this.showPrompt();
        }
      },
      error: (error) => {
        this.write(`❌ Session start failed: ${error.message}\r\n`);
        this.showPrompt();
      },
    });
  }

  endSession() {
    if (this.sessionId) {
      frappe.call({
        method: 'erpnext_mcp_server.api.terminal.end_mcp_session',
        args: { session_id: this.sessionId },
        callback: () => {
          this.write('\r\n👋 Goodbye!\r\n');
        },
      });
    } else {
      this.write('\r\n👋 Goodbye!\r\n');
    }
  }

  showWelcome() {
    const welcome = `
\x1b[36m╔══════════════════════════════════════╗
║         ERPNext MCP Terminal         ║
║       🚀 Low-Level Implementation    ║
╚══════════════════════════════════════╝\x1b[0m

Welcome to ERPNext MCP Terminal!

Available commands:
- \x1b[33mlist_doctypes\x1b[0m                 - List all doctypes
- \x1b[33mget_document <type> <name>\x1b[0m    - Get specific document  
- \x1b[33msearch_documents <type> <query>\x1b[0m - Search documents
- \x1b[33mexecute_sql <query>\x1b[0m           - Run SQL query
- \x1b[33mget_system_info\x1b[0m              - System information
- \x1b[33mbench_command <cmd>\x1b[0m           - Execute bench command
- \x1b[33mhelp\x1b[0m                        - Show help
- \x1b[33mclear\x1b[0m                       - Clear screen
- \x1b[33mexit\x1b[0m                        - Exit terminal

Type \x1b[33mhelp\x1b[0m for detailed usage examples.

`;
    this.write(welcome);
  }

  showPrompt() {
    const user = frappe.session.user || 'user';
    const site = frappe.boot.sitename || 'erpnext';
    const status = this.isConnected ? '\x1b[32m●\x1b[0m' : '\x1b[31m●\x1b[0m';
    this.terminal.write(
      `${status} \x1b[32m${user}@${site}\x1b[0m:\x1b[34m~\x1b[0m$ `
    );
  }

  showHelp() {
    const help = `
\x1b[36m📖 ERPNext MCP Terminal - Command Help\x1b[0m

\x1b[33mDocument Operations:\x1b[0m
  list_doctypes
    Example: list_doctypes

  get_document <doctype> <name>
    Example: get_document Customer "CUST-00001"
    Example: get_document "Sales Invoice" "SINV-2024-00001"

  search_documents <doctype> <query>
    Example: search_documents Customer "John"
    Example: search_documents Item "laptop"

  create_document <doctype> <json_data>
    Example: create_document Customer {"customer_name": "New Customer"}

\x1b[33mDatabase Operations:\x1b[0m
  execute_sql <query>
    Example: execute_sql "SELECT name, customer_name FROM \`tabCustomer\` LIMIT 10"
    Note: Only SELECT queries are allowed

\x1b[33mSystem Operations:\x1b[0m
  get_system_info
    Example: get_system_info

  bench_command <command>
    Example: bench_command status
    Example: bench_command version
    Allowed: status, version, migrate, list

\x1b[33mTerminal Commands:\x1b[0m
  help     - Show this help
  clear    - Clear terminal screen  
  history  - Show command history
  exit     - Exit terminal

\x1b[33mShortcuts:\x1b[0m
  Tab      - Auto-complete commands
  ↑/↓      - Navigate command history
  Ctrl+C   - Cancel current input
  Ctrl+L   - Clear screen

`;
    this.write(help);
    this.showPrompt();
  }

  showHistory() {
    this.write('\x1b[36m📜 Command History:\x1b[0m\r\n');
    this.commandHistory.forEach((cmd, index) => {
      this.write(`  ${index + 1}. ${cmd}\r\n`);
    });
    this.showPrompt();
  }

  clear() {
    this.terminal.clear();
    this.showWelcome();
    if (this.isConnected) {
      this.showPrompt();
    }
  }

  write(text) {
    this.terminal.write(text);
  }

  destroy() {
    this.endSession();
    if (this.terminal) {
      this.terminal.dispose();
    }
  }
}

// Make available globally
window.MCPTerminal = MCPTerminal;

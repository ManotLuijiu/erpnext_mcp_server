<template>
  <div class="mcp-terminal-app">
    <div class="terminal-container">
      <div class="terminal-header">
        <h3>🚀 ERPNext MCP Terminal</h3>
        <div class="terminal-status">
          <div class="status-dot" :class="{ connected: isConnected }"></div>
          <span>{{ connectionStatus }}</span>
          <span>|</span>
          <span>{{ userInfo }}</span>
        </div>
      </div>
      <div class="terminal-body">
        <div id="terminal" ref="terminalRef"></div>
        <div v-if="isLoading" class="loading">Initializing Terminal</div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted, computed } from 'vue';
import io from 'socket.io-client';

// frappe, Terminal, and FitAddon are assumed to be available on window

export default {
  name: 'MCPTerminalApp',
  setup() {
    // Get frappe from window object
    const frappe = window.frappe;
    const terminalRef = ref(null);
    const terminal = ref(null);
    const socket = ref(null);
    const isConnected = ref(false);
    const isLoading = ref(true);
    const sessionId = ref(null);
    const commandHistory = ref([]);
    const historyIndex = ref(-1);
    const currentCommand = ref('');

    // Available commands for auto-completion
    const availableCommands = [
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

    const connectionStatus = computed(() => {
      return isConnected.value ? 'Connected' : 'Disconnected';
    });

    const userInfo = computed(() => {
      const user = frappe?.session?.user || 'Guest';
      const site = frappe?.boot?.sitename || 'ERPNext';
      return `${user}@${site}`;
    });

    const initializeTerminal = () => {
      if (!window.Terminal) {
        console.error('xterm.js not loaded');
        return;
      }

      // Create terminal instance
      terminal.value = new window.Terminal({
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
      const fitAddon = new window.FitAddon.FitAddon();
      terminal.value.loadAddon(fitAddon);

      // Open terminal
      terminal.value.open(terminalRef.value);
      fitAddon.fit();

      // Setup event handlers
      setupTerminalHandlers(fitAddon);

      // Show welcome message
      showWelcome();

      // Start MCP session
      startSession();

      isLoading.value = false;
    };

    const setupTerminalHandlers = (fitAddon) => {
      // Handle terminal input
      terminal.value.onData((data) => {
        handleInput(data);
      });

      // Handle window resize
      window.addEventListener('resize', () => {
        fitAddon.fit();
      });
    };

    const setupSocketIO = () => {
      // Initialize Socket.IO connection for Frappe realtime
      socket.value = io();

      socket.value.on('connect', () => {
        console.log('Socket.IO connected');
      });

      socket.value.on('mcp_session_started', (data) => {
        sessionId.value = data.session_id;
        isConnected.value = true;
        writeToTerminal('\r\n✅ MCP session started\r\n');
        showPrompt();
      });

      socket.value.on('mcp_command_result', (data) => {
        handleCommandResult(data);
      });

      socket.value.on('mcp_session_ended', (data) => {
        console.log('data', data);
        isConnected.value = false;
        sessionId.value = null;
        writeToTerminal('\r\n🔌 Session ended\r\n');
      });

      socket.value.on('disconnect', () => {
        isConnected.value = false;
        console.log('Socket.IO disconnected');
      });
    };

    const handleInput = (data) => {
      const code = data.charCodeAt(0);

      switch (code) {
        case 13: // Enter
          executeCommand();
          break;
        case 127: // Backspace
          handleBackspace();
          break;
        case 27: // Escape sequences (arrow keys)
          handleEscapeSequence(data);
          break;
        case 3: // Ctrl+C
          handleCancel();
          break;
        case 12: // Ctrl+L
          clearTerminal();
          break;
        case 9: // Tab
          handleTabCompletion();
          break;
        default:
          if (code >= 32 && code <= 126) {
            currentCommand.value += data;
            terminal.value.write(data);
          }
      }
    };

    const handleEscapeSequence = (data) => {
      if (data === '\x1b[A') {
        // Up arrow
        navigateHistory(-1);
      } else if (data === '\x1b[B') {
        // Down arrow
        navigateHistory(1);
      }
    };

    const navigateHistory = (direction) => {
      if (commandHistory.value.length === 0) return;

      historyIndex.value += direction;

      if (historyIndex.value < 0) {
        historyIndex.value = 0;
      } else if (historyIndex.value >= commandHistory.value.length) {
        historyIndex.value = commandHistory.value.length;
        replaceCurrentLine('');
        return;
      }

      const command = commandHistory.value[historyIndex.value];
      replaceCurrentLine(command);
    };

    const replaceCurrentLine = (newCommand) => {
      terminal.value.write('\x1b[2K\r');
      showPrompt();
      terminal.value.write(newCommand);
      currentCommand.value = newCommand;
    };

    const handleBackspace = () => {
      if (currentCommand.value.length > 0) {
        currentCommand.value = currentCommand.value.slice(0, -1);
        terminal.value.write('\b \b');
      }
    };

    const handleCancel = () => {
      currentCommand.value = '';
      writeToTerminal('\r\n^C\r\n');
      showPrompt();
    };

    const handleTabCompletion = () => {
      const matches = availableCommands.filter((cmd) =>
        cmd.startsWith(currentCommand.value.trim())
      );

      if (matches.length === 1) {
        const completion = matches[0].slice(currentCommand.value.trim().length);
        currentCommand.value += completion + ' ';
        terminal.value.write(completion + ' ');
      } else if (matches.length > 1) {
        writeToTerminal('\r\n' + matches.join('  ') + '\r\n');
        showPrompt();
        terminal.value.write(currentCommand.value);
      }
    };

    const executeCommand = () => {
      const command = currentCommand.value.trim();
      writeToTerminal('\r\n');

      if (command) {
        commandHistory.value.push(command);
        historyIndex.value = commandHistory.value.length;
        processCommand(command);
      } else {
        showPrompt();
      }

      currentCommand.value = '';
    };

    const processCommand = (command) => {
      if (!isConnected.value) {
        writeToTerminal('❌ No active MCP session\r\n');
        showPrompt();
        return;
      }

      // Handle built-in commands
      if (handleBuiltinCommand(command)) {
        return;
      }

      // Show processing indicator
      writeToTerminal('⏳ Processing...\r\n');

      // Parse command and execute
      const parts = parseCommand(command);
      if (parts) {
        executeMCPCommand(parts.command, parts.args);
      }
    };

    const handleBuiltinCommand = (command) => {
      const cmd = command.toLowerCase().split(' ')[0];

      switch (cmd) {
        case 'clear':
          clearTerminal();
          return true;
        case 'help':
          showHelp();
          return true;
        case 'exit':
          endSession();
          return true;
        case 'history':
          showHistory();
          return true;
        default:
          return false;
      }
    };

    const parseCommand = (command) => {
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
          console.error(e);
          writeToTerminal('❌ Invalid JSON data for create_document\r\n');
          showPrompt();
          return null;
        }
      }

      return { command: cmd, args: args };
    };

    const executeMCPCommand = (command, args) => {
      frappe.call({
        method: 'erpnext_mcp_server.api.terminal.execute_mcp_command',
        args: {
          session_id: sessionId.value,
          command: command,
          args: args,
        },
        callback: (response) => {
          if (!response.message) {
            writeToTerminal('❌ No response from server\r\n');
            showPrompt();
          }
        },
        error: (error) => {
          writeToTerminal(`❌ API Error: ${error.message}\r\n`);
          showPrompt();
        },
      });
    };

    const handleCommandResult = (data) => {
      if (data.success) {
        if (data.data) {
          const formattedData = formatOutput(data.data);
          writeToTerminal(formattedData + '\r\n');
        }
        writeToTerminal('✅ Command completed\r\n');
      } else {
        writeToTerminal(`❌ Error: ${data.error || 'Unknown error'}\r\n`);
      }

      showPrompt();
    };

    const formatOutput = (data) => {
      try {
        const parsed = typeof data === 'string' ? JSON.parse(data) : data;
        if (Array.isArray(parsed)) {
          return formatArray(parsed);
        } else if (typeof parsed === 'object') {
          return formatObject(parsed);
        }
      } catch (e) {
        console.error(e);
        // Not JSON, return as-is
      }

      return typeof data === 'string' ? data : JSON.stringify(data);
    };

    const formatArray = (arr) => {
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
    };

    const formatObject = (obj) => {
      return JSON.stringify(obj, null, 2).replace(/\n/g, '\r\n');
    };

    const startSession = () => {
      writeToTerminal('🔌 Starting MCP session...\r\n');

      frappe.call({
        method: 'erpnext_mcp_server.api.terminal.start_mcp_session',
        callback: (response) => {
          if (!response.message.success) {
            writeToTerminal(
              `❌ Failed to start session: ${response.message.error}\r\n`
            );
            showPrompt();
          }
        },
        error: (error) => {
          writeToTerminal(`❌ Session start failed: ${error.message}\r\n`);
          showPrompt();
        },
      });
    };

    const endSession = () => {
      if (sessionId.value) {
        frappe.call({
          method: 'erpnext_mcp_server.api.terminal.end_mcp_session',
          args: { session_id: sessionId.value },
          callback: () => {
            writeToTerminal('\r\n👋 Goodbye!\r\n');
          },
        });
      } else {
        writeToTerminal('\r\n👋 Goodbye!\r\n');
      }
    };

    const showWelcome = () => {
      const welcome = `
\x1b[36m╔══════════════════════════════════════╗
║         ERPNext MCP Terminal         ║
║       🚀 Vue.js Implementation       ║
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
      writeToTerminal(welcome);
    };

    const showPrompt = () => {
      const user = frappe?.session?.user || 'user';
      const site = frappe?.boot?.sitename || 'erpnext';
      const status = isConnected.value
        ? '\x1b[32m●\x1b[0m'
        : '\x1b[31m●\x1b[0m';
      terminal.value.write(
        `${status} \x1b[32m${user}@${site}\x1b[0m:\x1b[34m~\x1b[0m$ `
      );
    };

    const showHelp = () => {
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
      writeToTerminal(help);
      showPrompt();
    };

    const showHistory = () => {
      writeToTerminal('\x1b[36m📜 Command History:\x1b[0m\r\n');
      commandHistory.value.forEach((cmd, index) => {
        writeToTerminal(`  ${index + 1}. ${cmd}\r\n`);
      });
      showPrompt();
    };

    const clearTerminal = () => {
      terminal.value.clear();
      showWelcome();
      if (isConnected.value) {
        showPrompt();
      }
    };

    const writeToTerminal = (text) => {
      if (terminal.value) {
        terminal.value.write(text);
      }
    };

    onMounted(() => {
      setupSocketIO();
      initializeTerminal();
    });

    onUnmounted(() => {
      endSession();
      if (terminal.value) {
        terminal.value.dispose();
      }
      if (socket.value) {
        socket.value.disconnect();
      }
    });

    return {
      terminalRef,
      isConnected,
      isLoading,
      connectionStatus,
      userInfo,
    };
  },
};
</script>

<style scoped>
.mcp-terminal-app {
  height: 100%;
  width: 100%;
}

.terminal-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #1e1e1e;
}

.terminal-header {
  background: linear-gradient(135deg, #2d2d2d 0%, #1e1e1e 100%);
  color: white;
  padding: 10px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 2px solid #444;
  flex-shrink: 0;
}

.terminal-header h3 {
  margin: 0;
  color: #4caf50;
  font-size: 18px;
}

.terminal-status {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: #bbb;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #f44336;
  transition: background-color 0.3s ease;
}

.status-dot.connected {
  background: #4caf50;
}

.terminal-body {
  flex: 1;
  padding: 10px;
  overflow: hidden;
}

#terminal {
  height: 100%;
  width: 100%;
}

.loading {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  color: #fff;
  font-size: 16px;
}

.loading::after {
  content: '...';
  animation: dots 1.5s infinite;
}

@keyframes dots {
  0%,
  20% {
    content: '.';
  }
  40% {
    content: '..';
  }
  60%,
  100% {
    content: '...';
  }
}

@media (max-width: 768px) {
  .terminal-header {
    padding: 8px 12px;
  }

  .terminal-header h3 {
    font-size: 16px;
  }

  .terminal-status {
    font-size: 10px;
  }
}
</style>

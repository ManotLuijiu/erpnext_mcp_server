<template>
  <div class="mcp-terminal-app">
    <div class="terminal-container">
      <div class="terminal-header">
        <div class="header-left">
          <h3>🚀 ERPNext MCP Terminal</h3>
          <div class="terminal-status">
            <div class="status-dot" :class="{ connected: isConnected }"></div>
            <span>{{ connectionStatus }}</span>
          </div>
        </div>
        <div class="header-right">
          <span class="user-info">{{ userInfo }}</span>
          <button
            class="btn-minimize"
            @click="toggleFullscreen"
            :title="isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'"
          >
            {{ isFullscreen ? '🗗' : '🗖' }}
          </button>
        </div>
      </div>

      <div class="terminal-body" ref="terminalContainer">
        <div id="terminal" ref="terminalRef" v-show="!isLoading"></div>

        <div v-if="isLoading" class="loading-container">
          <div class="loading-spinner"></div>
          <div class="loading-text">{{ loadingMessage }}</div>
        </div>

        <div v-if="error" class="error-container">
          <div class="error-icon">⚠️</div>
          <div class="error-message">{{ error }}</div>
          <button class="btn-retry" @click="retryConnection">Retry</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted, computed, nextTick } from 'vue';

export default {
  name: 'MCPTerminalApp',
  setup() {
    // Reactive state
    const terminalRef = ref(null);
    const terminalContainer = ref(null);
    const terminal = ref(null);
    const fitAddon = ref(null);
    const socket = ref(null);
    const isConnected = ref(false);
    const isLoading = ref(true);
    const loadingMessage = ref('Initializing Terminal...');
    const error = ref(null);
    const sessionId = ref(null);
    const isFullscreen = ref(false);

    // Command handling
    const commandHistory = ref([]);
    const historyIndex = ref(-1);
    const currentCommand = ref('');
    const isProcessingCommand = ref(false);

    // Available commands for auto-completion
    const availableCommands = [
      'list_doctypes',
      'get_document',
      'search_documents',
      'create_document',
      'update_document',
      'delete_document',
      'execute_sql',
      'get_system_info',
      'bench_command',
      'list_files',
      'read_file',
      'write_file',
      'backup_site',
      'get_logs',
      'help',
      'clear',
      'exit',
      'status',
    ];

    // Computed properties
    const connectionStatus = computed(() => {
      if (isLoading.value) return 'Initializing';
      return isConnected.value ? 'Connected' : 'Disconnected';
    });

    const userInfo = computed(() => {
      const user = window.frappe?.session?.user || 'Guest';
      const site = window.frappe?.boot?.sitename || 'ERPNext';
      return `${user}@${site}`;
    });

    // Terminal initialization
    const initializeTerminal = async () => {
      try {
        loadingMessage.value = 'Loading terminal dependencies...';

        // Load xterm.js and addons
        await loadXtermDependencies();

        loadingMessage.value = 'Creating terminal instance...';

        // Create terminal instance
        if (!window.Terminal) {
          throw new Error('xterm.js not available');
        }

        terminal.value = new window.Terminal({
          cursorBlink: true,
          fontSize: 14,
          fontFamily:
            '"Cascadia Code", "Fira Code", "JetBrains Mono", Monaco, Menlo, "Ubuntu Mono", monospace',
          theme: {
            background: '#1e1e1e',
            foreground: '#ffffff',
            cursor: '#ffffff',
            selection: '#3d3d3d',
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

        // Load fit addon
        if (window.FitAddon) {
          fitAddon.value = new window.FitAddon.FitAddon();
          terminal.value.loadAddon(fitAddon.value);
        }

        // Open terminal in DOM
        await nextTick();
        if (terminalRef.value) {
          terminal.value.open(terminalRef.value);

          // Fit terminal to container
          if (fitAddon.value) {
            setTimeout(() => {
              fitAddon.value.fit();
            }, 100);
          }
        }

        // Setup event handlers
        setupTerminalHandlers();

        loadingMessage.value = 'Connecting to ERPNext...';

        // Initialize Socket.IO connection
        await setupSocketIO();

        // Show welcome message
        showWelcome();

        // Start MCP session
        await startSession();

        isLoading.value = false;
      } catch (err) {
        console.error('Terminal initialization failed:', err);
        error.value = `Failed to initialize terminal: ${err.message}`;
        isLoading.value = false;
      }
    };

    const loadXtermDependencies = async () => {
      return new Promise((resolve, reject) => {
        // Check if already loaded
        if (window.Terminal && window.FitAddon) {
          resolve();
          return;
        }

        let scriptsLoaded = 0;
        const totalScripts = 2;

        const checkComplete = () => {
          scriptsLoaded++;
          if (scriptsLoaded === totalScripts) {
            // Add some delay to ensure everything is ready
            setTimeout(resolve, 100);
          }
        };

        // Load xterm.js CSS
        if (!document.querySelector('link[href*="xterm.css"]')) {
          const link = document.createElement('link');
          link.rel = 'stylesheet';
          link.href = '/assets/node_modules/@xterm/xterm/css/xterm.css';
          document.head.appendChild(link);
        }

        // Load xterm.js
        if (!window.Terminal) {
          const script1 = document.createElement('script');
          script1.src = '/assets/node_modules/@xterm/xterm/lib/xterm.js';
          script1.onload = checkComplete;
          script1.onerror = () => reject(new Error('Failed to load xterm.js'));
          document.head.appendChild(script1);
        } else {
          checkComplete();
        }

        // Load fit addon
        if (!window.FitAddon) {
          const script2 = document.createElement('script');
          script2.src =
            '/assets/node_modules/@xterm/addon-fit/lib/addon-fit.js';
          script2.onload = checkComplete;
          script2.onerror = () => reject(new Error('Failed to load fit addon'));
          document.head.appendChild(script2);
        } else {
          checkComplete();
        }
      });
    };

    const setupTerminalHandlers = () => {
      if (!terminal.value) return;

      // Handle terminal input
      terminal.value.onData((data) => {
        if (!isProcessingCommand.value) {
          handleInput(data);
        }
      });

      // Handle window resize
      const handleResize = () => {
        if (fitAddon.value && terminal.value) {
          setTimeout(() => {
            fitAddon.value.fit();
          }, 100);
        }
      };

      window.addEventListener('resize', handleResize);

      // Cleanup resize listener
      onUnmounted(() => {
        window.removeEventListener('resize', handleResize);
      });
    };

    const setupSocketIO = async () => {
      return new Promise((resolve, reject) => {
        try {
          // Use Frappe's socket.io connection
          if (window.frappe && window.frappe.socketio) {
            socket.value = window.frappe.socketio;
            setupSocketHandlers();
            resolve();
          } else {
            // Fallback to manual socket.io connection
            if (window.io) {
              socket.value = window.io();
              setupSocketHandlers();
              resolve();
            } else {
              reject(new Error('Socket.IO not available'));
            }
          }
        } catch (err) {
          reject(err);
        }
      });
    };

    const setupSocketHandlers = () => {
      if (!socket.value) return;

      socket.value.on('connect', () => {
        console.log('Socket connected');
        // Don't set isConnected here, wait for MCP session
      });

      socket.value.on('mcp_session_started', (data) => {
        sessionId.value = data.session_id;
        isConnected.value = true;
        writeToTerminal('\r\n✅ MCP session established\r\n');
        showPrompt();
      });

      socket.value.on('mcp_command_result', (data) => {
        handleCommandResult(data);
      });

      socket.value.on('mcp_error', (data) => {
        writeToTerminal(`\r\n❌ MCP Error: ${data.error}\r\n`);
        showPrompt();
        isProcessingCommand.value = false;
      });

      socket.value.on('mcp_session_ended', (data) => {
        console.log('data', data);
        isConnected.value = false;
        sessionId.value = null;
        writeToTerminal('\r\n🔌 MCP session ended\r\n');
        showPrompt();
      });

      socket.value.on('disconnect', () => {
        isConnected.value = false;
        console.log('Socket disconnected');
      });

      socket.value.on('reconnect', () => {
        console.log('Socket reconnected');
        // Attempt to restore session
        if (sessionId.value) {
          restoreSession();
        }
      });
    };

    // Input handling
    const handleInput = (data) => {
      const code = data.charCodeAt(0);

      switch (code) {
        case 13: // Enter
          executeCommand();
          break;
        case 127: // Backspace
          handleBackspace();
          break;
        case 27: // Escape sequences (arrow keys, etc.)
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
        case 4: // Ctrl+D (EOF)
          handleEOF();
          break;
        default:
          // Printable characters
          if (code >= 32 && code <= 126) {
            currentCommand.value += data;
            terminal.value.write(data);
          }
      }
    };

    const handleEscapeSequence = (data) => {
      if (data === '\x1b[A') {
        // Up arrow - previous command
        navigateHistory(-1);
      } else if (data === '\x1b[B') {
        // Down arrow - next command
        navigateHistory(1);
      } else if (data === '\x1b[C') {
        // Right arrow - move cursor right (not implemented)
      } else if (data === '\x1b[D') {
        // Left arrow - move cursor left (not implemented)
      }
    };

    const navigateHistory = (direction) => {
      if (commandHistory.value.length === 0) return;

      const newIndex = historyIndex.value + direction;

      if (newIndex < 0) {
        historyIndex.value = -1;
        replaceCurrentLine('');
      } else if (newIndex >= commandHistory.value.length) {
        historyIndex.value = commandHistory.value.length - 1;
      } else {
        historyIndex.value = newIndex;
        const command =
          commandHistory.value[
            commandHistory.value.length - 1 - historyIndex.value
          ];
        replaceCurrentLine(command);
      }
    };

    const replaceCurrentLine = (newCommand) => {
      // Clear current line and rewrite
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
      if (isProcessingCommand.value) {
        // Cancel current command
        cancelCurrentCommand();
      } else {
        currentCommand.value = '';
        writeToTerminal('\r\n^C\r\n');
        showPrompt();
      }
    };

    const handleEOF = () => {
      if (currentCommand.value.length === 0) {
        // Exit on empty line with Ctrl+D
        executeBuiltinCommand('exit');
      }
    };

    const handleTabCompletion = () => {
      const partial = currentCommand.value.trim().split(' ')[0];
      const matches = availableCommands.filter((cmd) =>
        cmd.toLowerCase().startsWith(partial.toLowerCase())
      );

      if (matches.length === 1) {
        const completion = matches[0].slice(partial.length);
        currentCommand.value = matches[0] + ' ';
        terminal.value.write(completion + ' ');
      } else if (matches.length > 1) {
        writeToTerminal('\r\n');
        const columns = Math.floor(120 / 20); // Approximate column width
        for (let i = 0; i < matches.length; i += columns) {
          const row = matches.slice(i, i + columns);
          writeToTerminal(row.map((cmd) => cmd.padEnd(20)).join('') + '\r\n');
        }
        showPrompt();
        terminal.value.write(currentCommand.value);
      }
    };

    // Command execution
    const executeCommand = () => {
      const command = currentCommand.value.trim();
      writeToTerminal('\r\n');

      if (command) {
        // Add to history
        if (commandHistory.value[commandHistory.value.length - 1] !== command) {
          commandHistory.value.push(command);
          // Limit history size
          if (commandHistory.value.length > 100) {
            commandHistory.value.shift();
          }
        }
        historyIndex.value = -1;

        processCommand(command);
      } else {
        showPrompt();
      }

      currentCommand.value = '';
    };

    const processCommand = (command) => {
      // Handle built-in commands first
      if (executeBuiltinCommand(command)) {
        return;
      }

      if (!isConnected.value) {
        writeToTerminal(
          '❌ No active MCP session. Please wait for connection.\r\n'
        );
        showPrompt();
        return;
      }

      // Show processing indicator
      isProcessingCommand.value = true;
      writeToTerminal('⏳ Processing command...\r\n');

      // Send command to backend
      sendMCPCommand(command);
    };

    const executeBuiltinCommand = (command) => {
      const parts = command.toLowerCase().split(' ');
      const cmd = parts[0];

      switch (cmd) {
        case 'clear':
        case 'cls':
          clearTerminal();
          return true;

        case 'help':
          showHelp();
          return true;

        case 'exit':
        case 'quit':
          handleExit();
          return true;

        case 'history':
          showHistory();
          return true;

        case 'status':
          showStatus();
          return true;

        default:
          return false;
      }
    };

    const sendMCPCommand = (command) => {
      if (!window.frappe) {
        writeToTerminal('❌ Frappe not available\r\n');
        showPrompt();
        isProcessingCommand.value = false;
        return;
      }

      window.frappe.call({
        method: 'erpnext_mcp_server.api.terminal.execute_mcp_command',
        args: {
          session_id: sessionId.value,
          command: command,
        },
        callback: (response) => {
          if (response && response.message) {
            // Response will be handled by socket event
          } else {
            writeToTerminal('❌ No response from server\r\n');
            showPrompt();
            isProcessingCommand.value = false;
          }
        },
        error: (error) => {
          writeToTerminal(`❌ API Error: ${error.message}\r\n`);
          showPrompt();
          isProcessingCommand.value = false;
        },
      });
    };

    const handleCommandResult = (data) => {
      isProcessingCommand.value = false;

      if (data.success) {
        if (data.result) {
          const formatted = formatCommandOutput(data.result);
          writeToTerminal(formatted + '\r\n');
        }
        if (data.message && data.message !== data.result) {
          writeToTerminal(`ℹ️  ${data.message}\r\n`);
        }
      } else {
        writeToTerminal(`❌ Error: ${data.error || 'Unknown error'}\r\n`);
        if (data.details) {
          writeToTerminal(`   Details: ${data.details}\r\n`);
        }
      }

      showPrompt();
    };

    const formatCommandOutput = (data) => {
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
    };

    // Session management
    const startSession = async () => {
      if (!window.frappe) {
        throw new Error('Frappe not available');
      }

      return new Promise((resolve, reject) => {
        window.frappe.call({
          method: 'erpnext_mcp_server.api.terminal.start_mcp_session',
          callback: (response) => {
            if (response && response.message && response.message.success) {
              resolve(response.message);
            } else {
              reject(
                new Error(
                  response?.message?.error || 'Failed to start MCP session'
                )
              );
            }
          },
          error: (error) => {
            reject(error);
          },
        });
      });
    };

    const restoreSession = () => {
      if (sessionId.value && window.frappe) {
        window.frappe.call({
          method: 'erpnext_mcp_server.api.terminal.restore_mcp_session',
          args: {
            session_id: sessionId.value,
          },
          callback: (response) => {
            if (response && response.message && response.message.success) {
              isConnected.value = true;
              writeToTerminal('\r\n🔄 Session restored\r\n');
              showPrompt();
            }
          },
        });
      }
    };

    const cancelCurrentCommand = () => {
      if (sessionId.value && window.frappe) {
        window.frappe.call({
          method: 'erpnext_mcp_server.api.terminal.cancel_mcp_command',
          args: {
            session_id: sessionId.value,
          },
        });
      }

      isProcessingCommand.value = false;
      writeToTerminal('\r\n^C Command cancelled\r\n');
      showPrompt();
    };

    const endSession = () => {
      if (sessionId.value && window.frappe) {
        window.frappe.call({
          method: 'erpnext_mcp_server.api.terminal.end_mcp_session',
          args: {
            session_id: sessionId.value,
          },
        });
      }

      sessionId.value = null;
      isConnected.value = false;
    };

    // UI functions
    const showWelcome = () => {
      const welcome = `\x1b[36m╔══════════════════════════════════════════════════════════╗
║                   ERPNext MCP Terminal                   ║
║              🚀 Model Context Protocol Server            ║
╚══════════════════════════════════════════════════════════╝\x1b[0m

Welcome to ERPNext MCP Terminal!

\x1b[33mDocument Operations:\x1b[0m
  list_doctypes                    - List all document types
  get_document <type> <name>       - Get specific document
  search_documents <type> <query>  - Search documents
  create_document <type> <json>    - Create new document

\x1b[33mDatabase Operations:\x1b[0m
  execute_sql <query>              - Execute SQL query (SELECT only)

\x1b[33mSystem Operations:\x1b[0m
  get_system_info                  - Get system information
  bench_command <cmd>              - Execute bench command
  get_logs                         - View system logs

\x1b[33mFile Operations:\x1b[0m
  list_files <path>                - List files in directory
  read_file <path>                 - Read file content

\x1b[33mTerminal Commands:\x1b[0m
  help     - Show detailed help     clear    - Clear screen
  history  - Command history        status   - Connection status
  exit     - Exit terminal

Type \x1b[33mhelp\x1b[0m for detailed usage examples.

`;
      writeToTerminal(welcome);
    };

    const showPrompt = () => {
      if (!terminal.value) return;

      const user = window.frappe?.session?.user || 'user';
      const site = window.frappe?.boot?.sitename || 'erpnext';
      const status = isConnected.value
        ? '\x1b[32m●\x1b[0m'
        : '\x1b[31m●\x1b[0m';
      const timestamp = new Date().toLocaleTimeString();

      terminal.value.write(
        `${status} \x1b[32m${user}@${site}\x1b[0m \x1b[90m${timestamp}\x1b[0m \x1b[34m$\x1b[0m `
      );
    };

    const showHelp = () => {
      const help = `\x1b[36m📖 ERPNext MCP Terminal - Detailed Help\x1b[0m

\x1b[33m📄 Document Operations:\x1b[0m
  list_doctypes
    Example: list_doctypes

  get_document <doctype> <name>
    Example: get_document Customer "CUST-00001"
    Example: get_document "Sales Invoice" "SINV-2024-00001"

  search_documents <doctype> <query>
    Example: search_documents Customer "John Doe"
    Example: search_documents Item "laptop" --limit 10

  create_document <doctype> <json_data>
    Example: create_document Customer {"customer_name": "New Customer", "customer_type": "Individual"}

\x1b[33m🗄️  Database Operations:\x1b[0m
  execute_sql <query>
    Example: execute_sql "SELECT name, customer_name FROM \`tabCustomer\` LIMIT 10"
    Example: execute_sql "SELECT COUNT(*) as total FROM \`tabSales Invoice\`"
    Note: Only SELECT queries are allowed for security

\x1b[33m⚙️  System Operations:\x1b[0m
  get_system_info
    Shows: Frappe version, ERPNext version, Python version, database info

  bench_command <command>
    Example: bench_command --version
    Example: bench_command migrate
    Allowed: version, migrate, status, list-apps

  get_logs [--lines 50] [--level error]
    Example: get_logs
    Example: get_logs --lines 100 --level warning

\x1b[33m📁 File Operations:\x1b[0m
  list_files <path>
    Example: list_files /home/frappe/frappe-bench/apps
    Example: list_files . --recursive

  read_file <path>
    Example: read_file sites/common_site_config.json
    Example: read_file apps/erpnext/erpnext/hooks.py --lines 20

\x1b[33m🖥️  Terminal Commands:\x1b[0m
  help          - Show this help message
  clear/cls     - Clear terminal screen
  history       - Show command history
  status        - Show connection and session status
  exit/quit     - Exit terminal

\x1b[33m⌨️  Keyboard Shortcuts:\x1b[0m
  Tab           - Auto-complete commands
  ↑/↓           - Navigate command history
  Ctrl+C        - Cancel current command/input
  Ctrl+L        - Clear screen
  Ctrl+D        - Exit (on empty line)

\x1b[33m💡 Pro Tips:\x1b[0m
  • Use quotes for names with spaces: get_document "Sales Invoice" "SINV-001"
  • JSON data can be formatted across multiple lines
  • Use --help with commands for more options
  • Session persists across reconnections

`;
      writeToTerminal(help);
      showPrompt();
    };

    const showHistory = () => {
      writeToTerminal('\x1b[36m📜 Command History:\x1b[0m\r\n');
      if (commandHistory.value.length === 0) {
        writeToTerminal('  No commands in history\r\n');
      } else {
        commandHistory.value.slice(-20).forEach((cmd, index) => {
          const num = commandHistory.value.length - 20 + index + 1;
          writeToTerminal(
            `  \x1b[90m${num.toString().padStart(3)}.\x1b[0m ${cmd}\r\n`
          );
        });
      }
      showPrompt();
    };

    const showStatus = () => {
      const status = `\x1b[36m📊 Terminal Status:\x1b[0m
  Connection: ${isConnected.value ? '\x1b[32mConnected\x1b[0m' : '\x1b[31mDisconnected\x1b[0m'}
  Session ID: ${sessionId.value || 'None'}
  User: ${window.frappe?.session?.user || 'Unknown'}
  Site: ${window.frappe?.boot?.sitename || 'Unknown'}
  Commands in history: ${commandHistory.value.length}
  Processing: ${isProcessingCommand.value ? 'Yes' : 'No'}
`;
      writeToTerminal(status);
      showPrompt();
    };

    const clearTerminal = () => {
      if (terminal.value) {
        terminal.value.clear();
        showWelcome();
        if (isConnected.value) {
          showPrompt();
        }
      }
    };

    const handleExit = () => {
      writeToTerminal('\r\n👋 Closing terminal...\r\n');
      endSession();
      setTimeout(() => {
        if (window.frappe && window.frappe.set_route) {
          window.frappe.set_route('');
        }
      }, 1000);
    };

    const writeToTerminal = (text) => {
      if (terminal.value) {
        terminal.value.write(text);
      }
    };

    const toggleFullscreen = () => {
      isFullscreen.value = !isFullscreen.value;
      const container = terminalContainer.value?.parentElement;
      if (container) {
        if (isFullscreen.value) {
          container.classList.add('fullscreen');
        } else {
          container.classList.remove('fullscreen');
        }

        // Refit terminal after fullscreen toggle
        setTimeout(() => {
          if (fitAddon.value) {
            fitAddon.value.fit();
          }
        }, 100);
      }
    };

    const retryConnection = () => {
      error.value = null;
      isLoading.value = true;
      loadingMessage.value = 'Retrying connection...';
      initializeTerminal();
    };

    // Lifecycle hooks
    onMounted(() => {
      initializeTerminal();
    });

    onUnmounted(() => {
      endSession();
      if (terminal.value) {
        terminal.value.dispose();
      }
      if (socket.value && socket.value.disconnect) {
        socket.value.disconnect();
      }
    });

    return {
      terminalRef,
      terminalContainer,
      isConnected,
      isLoading,
      loadingMessage,
      error,
      connectionStatus,
      userInfo,
      isFullscreen,
      toggleFullscreen,
      retryConnection,
    };
  },
};
</script>

<style scoped>
.mcp-terminal-app {
  height: 100%;
  width: 100%;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.terminal-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #1e1e1e;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.terminal-header {
  background: linear-gradient(135deg, #2d2d2d 0%, #1e1e1e 100%);
  color: white;
  padding: 12px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 2px solid #444;
  flex-shrink: 0;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 15px;
}

.terminal-header h3 {
  margin: 0;
  color: #4caf50;
  font-size: 18px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.terminal-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #bbb;
  background: rgba(255, 255, 255, 0.1);
  padding: 4px 8px;
  border-radius: 12px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #f44336;
  transition: background-color 0.3s ease;
  box-shadow: 0 0 4px rgba(244, 67, 54, 0.5);
}

.status-dot.connected {
  background: #4caf50;
  box-shadow: 0 0 4px rgba(76, 175, 80, 0.5);
}

.user-info {
  font-size: 12px;
  color: #ccc;
  background: rgba(255, 255, 255, 0.05);
  padding: 4px 8px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
}

.btn-minimize {
  background: none;
  border: none;
  color: #ccc;
  font-size: 14px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.btn-minimize:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.terminal-body {
  flex: 1;
  padding: 0;
  overflow: hidden;
  position: relative;
}

#terminal {
  height: 100%;
  width: 100%;
  padding: 10px;
}

/* Loading States */
.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  flex-direction: column;
  color: #8d99ae;
  background: #1e1e1e;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #333;
  border-top: 4px solid #4caf50;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 20px;
}

.loading-text {
  font-size: 16px;
  color: #bbb;
}

/* Error States */
.error-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  flex-direction: column;
  color: #e74c3c;
  text-align: center;
  padding: 20px;
  background: #1e1e1e;
}

.error-icon {
  font-size: 48px;
  margin-bottom: 20px;
}

.error-message {
  font-size: 16px;
  margin-bottom: 20px;
  max-width: 400px;
  line-height: 1.5;
}

.btn-retry {
  background: #4caf50;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.2s ease;
}

.btn-retry:hover {
  background: #45a049;
}

/* Fullscreen Mode */
.terminal-container.fullscreen {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 9999;
  border-radius: 0;
}

/* Animations */
@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

/* Responsive Design */
@media (max-width: 768px) {
  .terminal-header {
    padding: 8px 12px;
    flex-direction: column;
    gap: 10px;
  }

  .header-left,
  .header-right {
    width: 100%;
    justify-content: space-between;
  }

  .terminal-header h3 {
    font-size: 16px;
  }

  .terminal-status,
  .user-info {
    font-size: 10px;
  }

  #terminal {
    padding: 5px;
  }
}

/* Terminal Scrollbar Styling */
.terminal-body :deep(.xterm-viewport) {
  scrollbar-width: thin;
  scrollbar-color: #444 #1e1e1e;
}

.terminal-body :deep(.xterm-viewport::-webkit-scrollbar) {
  width: 6px;
}

.terminal-body :deep(.xterm-viewport::-webkit-scrollbar-track) {
  background: #1e1e1e;
}

.terminal-body :deep(.xterm-viewport::-webkit-scrollbar-thumb) {
  background: #444;
  border-radius: 3px;
}

.terminal-body :deep(.xterm-viewport::-webkit-scrollbar-thumb:hover) {
  background: #555;
}

/* Terminal Focus Styling */
.terminal-body :deep(.xterm-screen) {
  padding: 10px;
}

.terminal-body :deep(.xterm-cursor-layer) {
  animation: blink 1s infinite;
}

@keyframes blink {
  0%,
  50% {
    opacity: 1;
  }
  51%,
  100% {
    opacity: 0;
  }
}
</style>

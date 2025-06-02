import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import {
  TerminalColors as chalk,
  TerminalSpinner as ora,
  TerminalFiglet as figlet,
  TerminalProgress,
  TerminalBox,
} from '../terminal_utils';
import { library, dom } from '@fortawesome/fontawesome-svg-core';
import {
  faBars,
  faClipboard,
  faDownload,
  faKey,
  faCog,
  faServer,
  faDatabase,
  faTerminal,
} from '@fortawesome/free-solid-svg-icons';

library.add(
  faBars,
  faClipboard,
  faDownload,
  faKey,
  faCog,
  faServer,
  faDatabase,
  faTerminal
);
dom.watch();

// Terminal state management
class TerminalState {
  constructor() {
    this.isProcessing = false;
    this.currentSpinner = null;
    this.commandHistory = [];
    this.historyIndex = -1;
    this.currentCommand = '';
    this.mcpStatus = 'disconnected';
    this.sessionInfo = null;
  }

  reset() {
    this.isProcessing = false;
    this.currentSpinner = null;
    this.currentCommand = '';
  }

  addToHistory(command) {
    if (
      command.trim() &&
      this.commandHistory[this.commandHistory.length - 1] !== command
    ) {
      this.commandHistory.push(command);
      if (this.commandHistory.length > 100) {
        this.commandHistory.shift();
      }
    }
    this.historyIndex = -1;
  }
}

export const initEnhancedMCPTerminal = async (containerId) => {
  try {
    await new Promise((resolve) => setTimeout(resolve, 100));

    const container = document.getElementById(containerId);
    if (!container) throw new Error(`Container ${containerId} not found`);
    console.log('Initializing Enhanced MCP Terminal...', container);

    // Initialize terminal state
    const terminalState = new TerminalState();

    // Initialize terminal with enhanced settings
    const terminal = new Terminal({
      convertEol: true,
      disableStdin: false,
      cursorBlink: true,
      fontSize: 14,
      fontFamily:
        '"Cascadia Code", "Fira Code", "JetBrains Mono", "Courier New", monospace',
      theme: {
        background: '#0c0c0c',
        foreground: '#cccccc',
        cursor: '#00ff00',
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
      scrollback: 2000,
      tabStopWidth: 4,
      allowProposedApi: true,
    });

    const fitAddon = new FitAddon();
    terminal.loadAddon(fitAddon);

    const terminalElement = container.querySelector('#terminal');
    if (!terminalElement) throw new Error('Terminal element not found');

    terminal.open(terminalElement);
    fitAddon.fit();

    // Show enhanced welcome with MCP status
    await showEnhancedWelcome(terminal);

    // Initialize MCP server status
    await checkMCPStatus(terminal, terminalState);

    // Setup enhanced realtime listeners
    setupEnhancedRealtimeListeners(terminal, terminalState);

    // Handle terminal input with improved command processing
    terminal.onData(async (data) => {
      await handleTerminalInput(terminal, terminalState, data);
    });

    // Store terminal globally for utilities
    window.mcpTerminal = terminal;
    window.terminalState = terminalState;

    // Auto-fit on resize
    window.addEventListener('resize', () => {
      fitAddon.fit();
    });

    return terminal;
  } catch (error) {
    console.error(`Enhanced terminal initialization failed: ${error}`);
    throw error;
  }
};

async function showEnhancedWelcome(terminal) {
  const banner = figlet.banner('ERPNext MCP', {
    font: 'block',
    color: 'brightCyan',
    border: true,
    padding: 1,
  });
  const welcomeText = `
    ${banner}

    ${chalk.brightGreen('🚀 Enhanced ERPNext MCP Terminal')}
    ${chalk.gray('━'.repeat(60))}

    ${chalk.yellow('🔧 MCP Features:')}
      ${chalk.green('•')} Document operations (list, get, search)
      ${chalk.green('•')} Database queries (SELECT only for security)
      ${chalk.green('•')} System information and bench commands
      ${chalk.green('•')} File operations with safety restrictions
      ${chalk.green('•')} Real-time command processing via MCP protocol

    ${chalk.yellow('⚙️ Advanced Terminal:')}
      ${chalk.green('•')} Professional CLI styling and formatting
      ${chalk.green('•')} Loading spinners and progress indicators
      ${chalk.green('•')} Command history and auto-completion
      ${chalk.green('•')} Error handling and recovery
      ${chalk.green('•')} Session persistence and status monitoring

    ${chalk.yellow('📋 Quick Commands:')}
      ${chalk.cyan('status')}        Show MCP server connection status
      ${chalk.cyan('help')}          Comprehensive command reference
      ${chalk.cyan('list_doctypes')} Browse available document types
      ${chalk.cyan('get_system_info')} System and platform information

    ${chalk.brightMagenta('🔑 Keyboard Shortcuts:')}
      • ${chalk.cyan('↑/↓')} arrows for command history
      • ${chalk.cyan('Tab')} for available commands
      • ${chalk.cyan('Ctrl+C')} to cancel operations
      • ${chalk.cyan('Ctrl+L')} for screen clear

    ${chalk.gray('━'.repeat(60))}
    ${chalk.dim('Connecting to MCP server...')}
  `;

  terminal.write(welcomeText);
}

async function checkMCPStatus(terminal, terminalState) {
  try {
    const response = await frappe.call({
      method: 'erpnext_mcp_server.api.vue_mcp_server.get_terminal_status',
    });

    if (response.message && response.message.success) {
      terminalState.mcpStatus = response.message.status;
      terminalState.sessionInfo = response.message;

      const statusColor =
        response.message.status === 'connected'
          ? 'brightGreen'
          : 'brightYellow';
      const statusText =
        response.message.status === 'connected' ? 'CONNECTED' : 'STARTING';

      terminal.write(
        `\r\n${chalk.chain()[statusColor]().bold().apply(`🔗 MCP SERVER ${statusText}`)}\r\n`
      );

      if (response.message.status === 'disconnected') {
        terminal.write(
          `${chalk.dim('Initializing MCP server for session...')}\r\n`
        );
        await startMCPServer(terminal, terminalState);
      }
    } else {
      terminal.write(
        `\r\n${chalk.chain().red().bold().apply('❌ MCP SERVER ERROR')}\r\n`
      );
    }
  } catch (error) {
    terminal.write(
      `\r\n${chalk.chain().red().bold().apply('❌ CONNECTION ERROR:')} ${chalk.red(error.message || 'Unknown error')}\r\n`
    );
  }

  showEnhancedPrompt(terminal, terminalState);
}

async function startMCPServer(terminal, terminalState) {
  const spinner = new ora({
    text: 'Starting MCP server...',
    spinner: 'dots',
    color: 'cyan',
    terminal: terminal,
  });

  spinner.start();

  try {
    const response = await frappe.call({
      method: 'erpnext_mcp_server.api.vue_mcp_server.start_mcp_server',
    });
    if (response.message && response.message.success) {
      spinner.succeed('MCP server started successfully');
      terminalState.mcpStatus = 'connected';
    } else {
      spinner.fail('Failed to start MCP server');
    }
  } catch (error) {
    spinner.fail(`MCP server error: ${error.message}`);
  }
}

function showEnhancedPrompt(terminal, terminalState) {
  if (!terminal) return;

  const user = frappe?.session?.user || 'user';
  const site = frappe?.boot?.sitename || 'erpnext';
  const timestamp = new Date().toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });

  // Enhanced status indicators
  const statusIcon =
    terminalState.mcpStatus === 'connected'
      ? chalk.brightGreen('●')
      : chalk.brightRed('●');

  const mcpIndicator =
    terminalState.mcpStatus === 'connected'
      ? chalk.dim('[MCP:ON]')
      : chalk.dim('[MCP:OFF]');

  const userInfo = chalk.chain().cyan().bold().apply(`${user}@${site}`);
  const timeInfo = chalk.dim(`[${timestamp}]`);
  const pathInfo = chalk.brightBlue('~/frappe-bench/sites');
  const promptSymbol = chalk.chain().green().bold().apply('❯');

  terminal.write(
    `\r\n${statusIcon} ${userInfo} ${mcpIndicator} ${timeInfo}\r\n`
  );
  terminal.write(`${chalk.dim('┌─')} ${pathInfo}\r\n`);
  terminal.write(`${chalk.dim('└─')} ${promptSymbol} `);
}

async function handleTerminalInput(terminal, terminalState, data) {
  if (terminalState.isProcessing && terminalState.currentSpinner) return;

  const code = data.charCodeAt(0);

  switch (code) {
    case 13: // Enter
      if (terminalState.currentCommand.trim()) {
        terminalState.addToHistory(terminalState.currentCommand);
        await executeEnhancedCommand(
          terminal,
          terminalState,
          terminalState.currentCommand.trim()
        );
        terminalState.isProcessing = true;
      } else {
        terminal.write('\r\n');
        showEnhancedPrompt(terminal, terminalState);
      }
      terminalState.currentCommand = '';
      break;

    case 127: // Backspace
      if (terminalState.currentCommand.length > 0) {
        terminalState.currentCommand = terminalState.currentCommand.slice(
          0,
          -1
        );
        terminal.write('\b \b');
      }
      break;

    case 3: // Ctrl+C
      if (terminalState.currentSpinner) {
        terminalState.currentSpinner.fail('Operation cancelled');
        terminalState.currentSpinner = null;
        terminalState.isProcessing = false;
      }
      terminal.write(chalk.red('^C') + '\r\n');
      terminalState.currentCommand = '';
      showEnhancedPrompt(terminal, terminalState);
      break;

    case 12: // Ctrl+L
      terminal.clear();
      await showEnhancedWelcome(terminal);
      showEnhancedPrompt(terminal, terminalState);
      break;

    case 9: // Tab
      showEnhancedCommandsHelp(terminal, terminalState);
      break;

    default:
      // Handle arrow keys
      if (data === '\x1b[A' && terminalState.commandHistory.length > 0) {
        // Up arrow
        if (
          terminalState.historyIndex <
          terminalState.commandHistory.length - 1
        ) {
          terminalState.historyIndex++;
          const command =
            terminalState.commandHistory[
              terminalState.commandHistory.length -
                1 -
                terminalState.historyIndex
            ];
          replaceCurrentLine(terminal, terminalState, command);
          terminalState.currentCommand = command;
        }
      } else if (data === '\x1b[B' && terminalState.commandHistory.length > 0) {
        // Down arrow
        if (terminalState.historyIndex > 0) {
          terminalState.historyIndex--;
          const command =
            terminalState.commandHistory[
              terminalState.commandHistory.length -
                1 -
                terminalState.historyIndex
            ];
          replaceCurrentLine(terminal, terminalState, command);
          terminalState.currentCommand = command;
        } else if (terminalState.historyIndex === 0) {
          terminalState.historyIndex = -1;
          replaceCurrentLine(terminal, terminalState, '');
          terminalState.currentCommand = '';
        }
      } else if (code >= 32 && code <= 126) {
        // Printable characters
        terminalState.currentCommand += data;
        terminal.write(data);
      }
  }
}

function replaceCurrentLine(terminal, terminalState, newCommand) {
  terminal.write('\r\x1b[K');
  showEnhancedPrompt(terminal, terminalState);
  terminal.write(newCommand);
}

async function executeEnhancedCommand(terminal, terminalState, command) {
  if (!command.trim()) return;

  const lowerCommand = command.toLowerCase().trim();

  // Handle built-in commands
  if (lowerCommand === 'clear' || lowerCommand === 'cls') {
    terminal.clear();
    await showEnhancedWelcome(terminal);
    return;
  }

  if (lowerCommand === 'help') {
    showDetailedMCPHelp(terminal, terminalState);
    return;
  }

  if (lowerCommand === 'status') {
    await showMCPStatus(terminal, terminalState);
    return;
  }

  // Show command execution with professional feedback
  terminal.write(
    `\r\n${chalk.dim('▶')} ${chalk.brightYellow(`Executing: ${command}`)}\r\n`
  );

  // Create spinner for MCP command
  const spinner = new ora({
    text: `Processing MCP command: ${command}`,
    spinner: 'dots',
    color: 'cyan',
    terminal: terminal,
  });

  spinner.start();
  terminalState.currentSpinner = spinner;

  // Send command to MCP server via Frappe API
  try {
    const user = frappe.session.user;
    console.log('user', user);

    const response = await frappe.call({
      method: 'erpnext_mcp_server.api.vue_mcp_server.execute_terminal_command',
      args: { command: command, user },
    });

    if (response && response.message && response.message.success) {
      spinner.succeed('Command sent to MCP server');
    } else {
      spinner.warn('Command sent with warnings');
    }
  } catch (error) {
    console.error(`Command execution failed: ${error}`);
    spinner.fail(`Error: ${error.message || 'Command execution failed'}`);
    terminal.write(
      `\r\n${chalk.chain().red().bold().apply('❌ EXECUTION ERROR:')} ${chalk.red(error.message)}\r\n`
    );
    showEnhancedPrompt(terminal, terminalState);
  }
  terminalState.currentSpinner = null;
}

function setupEnhancedRealtimeListeners(terminal, terminalState) {
  // Enhanced terminal output listener
  frappe.realtime.on('terminal_output', (message) => {
    if (terminalState.currentSpinner) {
      terminalState.currentSpinner.stop();
      terminalState.currentSpinner = null;
    }

    terminalState.isProcessing = false;

    switch (message.type) {
      case 'command':
        terminal.write(
          `\r\n${chalk.dim('▶')} ${chalk.brightYellow(message.data)}\r\n`
        );
        break;

      case 'stdout': {
        const formattedOutput = formatMCPOutput(message.data);
        terminal.write(`\r\n${formattedOutput}\r\n`);
        break;
      }

      case 'stderr':
        terminal.write(
          `\r\n${chalk.chain().red().bold().apply('❌ ERROR:')} ${chalk.red(message.data)}\r\n`
        );
        break;

      case 'success':
        terminal.write(
          `\r\n${chalk.chain().green().bold().apply('✅ SUCCESS:')} ${chalk.brightGreen(message.data)}\r\n`
        );
        break;

      case 'info':
        terminal.write(
          `\r\n${chalk.chain().blue().bold().apply('ℹ️  INFO:')} ${chalk.cyan(message.data)}\r\n`
        );
        break;

      case 'warning':
        terminal.write(
          `\r\n${chalk.chain().yellow().bold().apply('⚠️  WARNING:')} ${chalk.yellow(message.data)}\r\n`
        );
        break;

      case 'progress':
        if (message.current !== undefined && message.total !== undefined) {
          showProgressBar(
            terminal,
            message.current,
            message.total,
            message.label
          );
          return;
        }
        break;

      default:
        terminal.write(`\r\n${message.data}\r\n`);
    }

    showEnhancedPrompt(terminal, terminalState);
  });

  // Enhanced MCP status listener
  frappe.realtime.on('mcp_status', (message) => {
    terminalState.mcpStatus = message.status;

    switch (message.status) {
      case 'connected':
        terminal.write(
          `\r\n${chalk.chain().green().bold().apply('🟢 MCP CONNECTED:')} Server online and ready\r\n`
        );
        break;
      case 'disconnected':
        terminal.write(
          `\r\n${chalk.chain().red().bold().apply('🔴 MCP DISCONNECTED:')} Server offline\r\n`
        );
        break;
      case 'error':
        terminal.write(
          `\r\n${chalk.chain().red().bold().apply('❌ MCP ERROR:')} ${chalk.red(message.error)}\r\n`
        );
        break;
      case 'reconnecting':
        terminal.write(
          `\r\n${chalk.chain().yellow().bold().apply('🔄 MCP RECONNECTING:')} Attempting to restore connection\r\n`
        );
        break;
    }

    showEnhancedPrompt(terminal, terminalState);
  });
}

function formatMCPOutput(data) {
  if (typeof data === 'string') {
    return (
      data
        // Highlight MCP-specific patterns
        .replace(/^(📋|📄|🔍|📊|🖥️|📁|🔧|⚙️|🗄️)/gm, chalk.brightCyan('$1'))
        .replace(/^(✅|❌|⚠️|ℹ️)/gm, (match) => {
          switch (match) {
            case '✅':
              return chalk.brightGreen(match);
            case '❌':
              return chalk.brightRed(match);
            case '⚠️':
              return chalk.brightYellow(match);
            case 'ℹ️':
              return chalk.brightBlue(match);
            default:
              return match;
          }
        })
        // Highlight structural elements
        .replace(/^(═+|─+)/gm, chalk.dim('$1'))
        .replace(/^(\s+•)/gm, chalk.green('$1'))
        .replace(/(\w+:)/g, chalk.yellow('$1'))
        .replace(/(".*?")/g, chalk.brightMagenta('$1'))
        .replace(/(\d+)/g, chalk.brightBlue('$1'))
        // Highlight ERPNext-specific terms
        .replace(
          /(Customer|Sales Invoice|Item|DocType)/g,
          chalk.brightCyan('$1')
        )
        .replace(
          /(SELECT|FROM|WHERE|ORDER BY|LIMIT)/g,
          chalk.brightMagenta('$1')
        )
    );
  }

  if (typeof data === 'object') {
    try {
      return chalk.dim(JSON.stringify(data, null, 2));
    } catch (error) {
      console.error(error);
      return String(data);
    }
  }

  return String(data);
}

function showEnhancedCommandsHelp(terminal, terminalState) {
  terminal.write('\r\n');

  const commands = [
    ['help', 'Show comprehensive help with examples'],
    ['status', 'Display MCP server and system status'],
    ['list_doctypes [module]', 'List document types, optionally by module'],
    ['get_document <type> <name>', 'Retrieve specific document'],
    ['search_documents <type> <query>', 'Search documents with filters'],
    ['execute_sql "<query>"', 'Execute SQL SELECT queries safely'],
    ['get_system_info', 'Show system and platform information'],
    ['bench_command <cmd>', 'Execute safe bench commands'],
    ['list_files <path> [--recursive]', 'List directory contents'],
    ['read_file <path> [--lines N]', 'Display file contents'],
    ['clear', 'Clear terminal screen'],
  ];

  const table = TerminalBox.table(commands, {
    style: 'rounded',
    headers: ['Command', 'Description'],
    colors: { header: 'brightCyan' },
  });

  terminal.write(chalk.cyan(table) + '\r\n\r\n');

  // Add MCP-specific examples
  const examples = `${chalk.yellow('🚀 MCP Command Examples:')}

${chalk.cyan('Document Operations:')}
  get_document Customer "CUST-00001"
  search_documents "Sales Invoice" "pending" --limit 5
  list_doctypes Selling

${chalk.cyan('Database Queries:')}
  execute_sql "SELECT name, customer_name FROM \`tabCustomer\` LIMIT 10"
  execute_sql "SELECT COUNT(*) as total FROM \`tabItem\`"

${chalk.cyan('System Operations:')}
  bench_command version
  get_system_info
  list_files ./apps --recursive`;

  const exampleBox = TerminalBox.create(examples, {
    style: 'single',
    color: 'brightYellow',
    padding: 1,
    title: 'MCP Examples',
  });

  terminal.write(exampleBox + '\r\n');
  showEnhancedPrompt(terminal, terminalState);
}

async function showMCPStatus(terminal, terminalState) {
  try {
    const response = await frappe.call({
      method: 'erpnext_mcp_server.api.vue_mcp_server.get_terminal_status',
    });

    if (response.message && response.message.success) {
      const status = response.message;
      const connectionStatus =
        status.status === 'connected'
          ? chalk.chain().green().bold().apply('● CONNECTED')
          : chalk.chain().red().bold().apply('● DISCONNECTED');

      const statusData = [
        ['MCP Server', connectionStatus],
        ['Session', chalk.cyan(status.session || 'N/A')],
        ['User', chalk.cyan(status.user)],
        ['Site', chalk.cyan(status.site)],
        ['Protocol', chalk.yellow('JSON-RPC over stdio')],
        ['Transport', chalk.yellow('Frappe Realtime (socket.io)')],
        ['Security', chalk.green('✓ Enabled (whitelisted operations)')],
      ];

      const statusTable = TerminalBox.table(statusData, {
        style: 'double',
        headers: ['Component', 'Status'],
        colors: { header: 'brightMagenta' },
      });

      terminal.write(
        '\r\n' + figlet.generate('STATUS', 'small', 'brightGreen') + '\r\n'
      );
      terminal.write(chalk.brightGreen(statusTable) + '\r\n');

      // Add performance metrics if available
      const perfData = [
        ['Commands Executed', terminalState.commandHistory.length.toString()],
        ['Session Duration', 'Active'],
        ['Last Activity', new Date().toLocaleTimeString()],
      ];

      const perfTable = TerminalBox.table(perfData, {
        style: 'single',
        headers: ['Metric', 'Value'],
        colors: { header: 'brightBlue' },
      });

      terminal.write('\r\n' + chalk.brightBlue('📊 Session Metrics') + '\r\n');
      terminal.write(perfTable + '\r\n');
    } else {
      terminal.write(
        `\r\n${chalk.chain().red().bold().apply('❌ STATUS ERROR:')} Unable to retrieve MCP status\r\n`
      );
    }
  } catch (error) {
    terminal.write(
      `\r\n${chalk.chain().red().bold().apply('❌ CONNECTION ERROR:')} ${chalk.red(error.message)}\r\n`
    );
  }

  showEnhancedPrompt(terminal, terminalState);
}

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
      scrollback: 2000,
      tabStopWidth: 4,
      allowProposedApi: true,
    });

    const fitAddon = new FitAddon();
    terminal.loadAddon(fitAddon);

    // Find the terminal element within the container
    const terminalElement = container.querySelector('#terminal');
    if (!terminalElement) throw new Error('Terminal element not found');

    terminal.open(terminalElement);

    // Enhanced styling with padding and effects
    // terminalElement.style.padding = '20px';
    // terminalElement.style.margin = '10px';
    // terminalElement.style.borderRadius = '8px';
    // terminalElement.style.background =
    //   'linear-gradient(135deg, #0a0e27 0%, #1e1e2e 100%)';
    // terminalElement.style.boxShadow = 'inset 0 0 20px rgba(0, 0, 0, 0.5)';

    fitAddon.fit();

    // Show welcome message with available commands
    // showWelcomeMessage(terminal);

    // Show professional welcome message with ASCII art
    await showProfessionalWelcome(terminal);

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
    let currentSpinner = null;

    terminal.onData(async (data) => {
      if (isProcessing && currentSpinner) return;

      const code = data.charCodeAt(0);

      switch (code) {
        case 13: // Enter
          if (currentCommand.trim()) {
            commandHistory.push(currentCommand);
            if (commandHistory.length > 100) {
              commandHistory.shift();
            }
            historyIndex = -1;
            // executeCommand(terminal, currentCommand.trim());
            executeCommandWithStyle(terminal, currentCommand.trim());
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
          if (currentSpinner) {
            currentSpinner.fail('Command cancelled');
            currentSpinner = null;
            isProcessing = false;
          }
          // terminal.write('^C\r\n');
          terminal.write(chalk.red('^C') + '\r\n');
          currentCommand = '';
          // showPrompt(terminal);
          showStyledPrompt(terminal);
          break;

        case 12: // Ctrl+L
          terminal.clear();
          await showProfessionalWelcome(terminal);
          showStyledPrompt(terminal);
          // showWelcomeMessage(terminal);
          // showPrompt(terminal);
          break;

        case 9: // Tab - show available commands
          // showAvailableCommands(terminal);
          showStyledAvailableCommands(terminal);
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
      if (!processing && currentSpinner) {
        currentSpinner.succeed('Command completed');
        currentSpinner = null;
      }
    };

    // Store terminal instance globally for utilities
    window.mcpTerminal = terminal;

    return terminal;
  } catch (error) {
    console.error('Terminal initialization failed:', error);
    throw error;
  }
};

async function showProfessionalWelcome(terminal) {
  // Create ASCII art banner
  const banner = figlet.banner('ERPNext MCP', {
    font: 'block',
    color: 'brightCyan',
    border: true,
    padding: 1,
  });

  // Welcome text with professional styling
  const welcomeText = `
${banner}

${chalk.brightGreen('🚀 Professional Terminal Interface')}
${chalk.gray('━'.repeat(60))}

${chalk.yellow('✨ Features:')}
  ${chalk.green('•')} Professional CLI styling with ${chalk.cyan('chalk')}-like colors
  ${chalk.green('•')} Loading spinners with ${chalk.cyan('ora')}-style animations  
  ${chalk.green('•')} ASCII art banners with ${chalk.cyan('figlet')}-style fonts
  ${chalk.green('•')} Progress bars and professional formatting
  ${chalk.green('•')} Advanced box drawing and table layouts

${chalk.yellow('⚡ Quick Start:')}
  ${chalk.cyan('Tab')}        Show available commands
  ${chalk.cyan('help')}       Detailed command reference  
  ${chalk.cyan('status')}     System information
  ${chalk.cyan('clear')}      Clear terminal screen

${chalk.brightMagenta('💡 Pro Tips:')}
  • Use ${chalk.cyan('↑/↓')} arrows for command history
  • ${chalk.cyan('Ctrl+C')} to cancel running commands
  • ${chalk.cyan('Ctrl+L')} for quick screen clear
  • Commands support ${chalk.green('--help')} flag for detailed usage

${chalk.gray('━'.repeat(60))}
${chalk.dim('Ready for professional ERPNext management...')}
`;

  terminal.write(welcomeText);
  showStyledPrompt(terminal);
}

function showStyledAvailableCommands(terminal) {
  terminal.write('\r\n');

  // Create professional command table
  const commands = [
    ['list_doctypes', 'List all document types with module info'],
    ['get_document', 'Fetch specific document with formatting'],
    ['search_documents', 'Advanced document search with filters'],
    ['execute_sql', 'Execute SQL queries (SELECT only)'],
    ['get_system_info', 'Comprehensive system information'],
    ['list_files', 'Browse directories with file details'],
    ['read_file', 'View file contents with syntax awareness'],
    ['bench_command', 'Execute safe bench operations'],
    ['help', 'Show detailed help with examples'],
    ['status', 'Display connection and system status'],
    ['clear', 'Clear terminal with welcome message'],
  ];

  const table = TerminalBox.table(commands, {
    style: 'rounded',
    headers: ['Command', 'Description'],
    colors: { header: 'brightCyan' },
  });

  terminal.write(chalk.cyan(table) + '\r\n\r\n');

  // Add usage examples box
  const examples = `${chalk.yellow('💡 Usage Examples:')}

${chalk.cyan('get_document')} Customer "CUST-00001"
${chalk.cyan('search_documents')} Item "laptop" --limit 10  
${chalk.cyan('execute_sql')} "SELECT name FROM \`tabCustomer\` LIMIT 5"
${chalk.cyan('list_files')} ./apps --recursive
${chalk.cyan('bench_command')} --version`;

  const exampleBox = TerminalBox.create(examples, {
    style: 'single',
    color: 'brightYellow',
    padding: 1,
    title: 'Examples',
  });

  terminal.write(exampleBox + '\r\n');
  showStyledPrompt(terminal);
}

function showStyledPrompt(terminal) {
  if (!terminal) return;

  const user = frappe?.session?.user || 'user';
  const site = frappe?.boot?.sitename || 'erpnext';
  const timestamp = new Date().toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });

  // Professional prompt with colors and styling
  const statusIcon = chalk.brightGreen('●');
  const userInfo = chalk.chain().cyan().bold().apply(`${user}@${site}`);
  const timeInfo = chalk.dim(`[${timestamp}]`);
  const pathInfo = chalk.brightBlue('~/frappe-bench/sites');
  const promptSymbol = chalk.chain().green().bold().apply('❯');

  terminal.write(`\r\n${statusIcon} ${userInfo} ${timeInfo}\r\n`);
  terminal.write(`${chalk.dim('┌─')} ${pathInfo}\r\n`);
  terminal.write(`${chalk.dim('└─')} ${promptSymbol} `);
}

// function showWelcomeMessage(terminal) {
//   const welcome = `\x1b[36m
// ╔══════════════════════════════════════════════════════════════════════════════╗
// ║                           🚀 ERPNext MCP Terminal
// ║                      Model Context Protocol Interface                        ║
// ║                                                                              ║
// ║  Type 'help' for available commands or 'Tab' to see quick commands           ║
// ╚══════════════════════════════════════════════════════════════════════════════╝\x1b[0m

// \x1b[32m✅ Terminal initialized successfully!\x1b[0m
// \x1b[33m💡 Pro tip: Use Tab to see available commands, ↑/↓ for command history\x1b[0m

// `;
//   terminal.write(welcome);
//   showPrompt(terminal);
// }

// function showAvailableCommands(terminal) {
//   terminal.write('\r\n\x1b[36m📚 Quick Commands:\x1b[0m\r\n');
//   terminal.write(
//     '\x1b[90m┌─────────────────────┬─────────────────────────────────────────────────────┐\x1b[0m\r\n'
//   );
//   terminal.write(
//     '\x1b[90m│\x1b[0m \x1b[33mCommand\x1b[0m             \x1b[90m│\x1b[0m \x1b[37mDescription\x1b[0m                                     \x1b[90m│\x1b[0m\r\n'
//   );
//   terminal.write(
//     '\x1b[90m├─────────────────────┼─────────────────────────────────────────────────────┤\x1b[0m\r\n'
//   );
//   terminal.write(
//     '\x1b[90m│\x1b[0m help                \x1b[90m│\x1b[0m Show detailed help and usage examples              \x1b[90m│\x1b[0m\r\n'
//   );
//   terminal.write(
//     '\x1b[90m│\x1b[0m list_doctypes       \x1b[90m│\x1b[0m List all available document types                  \x1b[90m│\x1b[0m\r\n'
//   );
//   terminal.write(
//     '\x1b[90m│\x1b[0m get_document        \x1b[90m│\x1b[0m Get specific document (e.g., Customer "CUST-001") \x1b[90m│\x1b[0m\r\n'
//   );
//   terminal.write(
//     '\x1b[90m│\x1b[0m search_documents    \x1b[90m│\x1b[0m Search documents by criteria                       \x1b[90m│\x1b[0m\r\n'
//   );
//   terminal.write(
//     '\x1b[90m│\x1b[0m execute_sql         \x1b[90m│\x1b[0m Execute SQL query (SELECT only)                    \x1b[90m│\x1b[0m\r\n'
//   );
//   terminal.write(
//     '\x1b[90m│\x1b[0m get_system_info     \x1b[90m│\x1b[0m Show system information                            \x1b[90m│\x1b[0m\r\n'
//   );
//   terminal.write(
//     '\x1b[90m│\x1b[0m list_files          \x1b[90m│\x1b[0m List files in directory                            \x1b[90m│\x1b[0m\r\n'
//   );
//   terminal.write(
//     '\x1b[90m│\x1b[0m clear               \x1b[90m│\x1b[0m Clear terminal screen                              \x1b[90m│\x1b[0m\r\n'
//   );
//   terminal.write(
//     '\x1b[90m│\x1b[0m status              \x1b[90m│\x1b[0m Show connection status                             \x1b[90m│\x1b[0m\r\n'
//   );
//   terminal.write(
//     '\x1b[90m└─────────────────────┴─────────────────────────────────────────────────────┘\x1b[0m\r\n'
//   );
//   terminal.write(
//     '\r\n\x1b[33m💡 Type any command above or "help" for detailed examples\x1b[0m\r\n'
//   );
//   showPrompt(terminal);
// }

// function replaceCurrentLine(terminal, newCommand) {
//   // Move to beginning of line and clear it
//   terminal.write('\r\x1b[K');
//   showStyledPrompt(terminal);
//   // showPrompt(terminal);
//   terminal.write(newCommand);
// }

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
    if (window.mcpCurrentSpinner) {
      window.mcpCurrentSpinner.stop();
      window.mcpCurrentSpinner = null;
    }

    window.setProcessingState && window.setProcessingState(false);

    switch (message.type) {
      case 'command':
        // terminal.write(`\x1b[33m${message.data}\x1b[0m`);
        // terminal.write(`\r\n\x1b[33m${message.data}\x1b[0m `);
        // terminal.write(
        //   `\r\n\x1b[90m▶\x1b[0m \x1b[33m${message.data}\x1b[0m\r\n`
        // );
        terminal.write(
          `\r\n${chalk.dim('▶')} ${chalk.brightYellow(message.data)}\r\n`
        );
        break;

      case 'stdout': {
        // terminal.write(message.data);
        // terminal.write(`\r\n${message.data}`);
        // terminal.write(`\r\n${formatOutput(message.data)}\r\n`);
        const formattedOutput = formatProfessionalOutput(message.data);
        terminal.write(`\r\n${formattedOutput}\r\n`);
        break;
      }

      case 'stderr':
        // terminal.write(`\x1b[31m${message.data}\x1b[0m`);
        // terminal.write(`\r\n\x1b[31m${message.data}\x1b[0m`);
        // terminal.write(`\r\n\x1b[31m❌ ${message.data}\x1b[0m\r\n`);
        terminal.write(
          `\r\n${chalk.chain().red().bold().apply('❌ ERROR:')} ${chalk.red(message.data)}\r\n`
        );
        break;

      case 'success':
        // terminal.write(`\r\n\x1b[32m✅ ${message.data}\x1b[0m\r\n`);
        terminal.write(
          `\r\n${chalk.chain().green().bold().apply('✅ SUCCESS:')} ${chalk.brightGreen(message.data)}\r\n`
        );
        break;

      case 'info':
        // terminal.write(`\r\n\x1b[36mℹ️  ${message.data}\x1b[0m\r\n`);
        terminal.write(
          `\r\n${chalk.chain().blue().bold().apply('ℹ️  INFO:')} ${chalk.cyan(message.data)}\r\n`
        );
        break;

      case 'warning':
        // terminal.write(`\r\n\x1b[33m⚠️  ${message.data}\x1b[0m\r\n`);
        terminal.write(
          `\r\n${chalk.chain().yellow().bold().apply('⚠️  WARNING:')} ${chalk.yellow(message.data)}\r\n`
        );
        break;

      case 'progress':
        if (message.current !== undefined && message.total !== undefined) {
          showProgressBar(
            terminal,
            message.current,
            message.total,
            message.label
          );
          return; // Don't show prompt for progress updates
        }
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
    // showPrompt(terminal);
    showStyledPrompt(terminal);
  });

  // Handle connection status
  frappe.realtime.on('mcp_status', (message) => {
    switch (message.status) {
      case 'connected':
        // terminal.write(`\r\n\x1b[32m🟢 MCP Server connected\x1b[0m\r\n`);
        terminal.write(
          `\r\n${chalk.chain().green().bold().apply('🟢 CONNECTED:')} MCP Server online\r\n`
        );
        break;
      case 'disconnected':
        // terminal.write(`\r\n\x1b[31m🔴 MCP Server disconnected\x1b[0m\r\n`);
        terminal.write(
          `\r\n${chalk.chain().red().bold().apply('🔴 DISCONNECTED:')} MCP Server offline\r\n`
        );
        break;
      case 'error':
        // terminal.write(
        //   `\r\n\x1b[31m❌ Connection error: ${message.error}\x1b[0m\r\n`
        // );
        terminal.write(
          `\r\n${chalk.chain().red().bold().apply('❌ CONNECTION ERROR:')} ${chalk.red(message.error)}\r\n`
        );
        break;
    }
    // showPrompt(terminal);
    showStyledPrompt(terminal);
  });
}

function formatProfessionalOutput(data) {
  if (typeof data === 'string') {
    // Add syntax highlighting for common patterns
    return data
      .replace(/^(📋|📄|🔍|📊|🖥️|📁|🔧)/gm, chalk.brightCyan('$1'))
      .replace(/^(✅|❌|⚠️|ℹ️)/gm, (match) => {
        switch (match) {
          case '✅':
            return chalk.brightGreen(match);
          case '❌':
            return chalk.brightRed(match);
          case '⚠️':
            return chalk.brightYellow(match);
          case 'ℹ️':
            return chalk.brightBlue(match);
          default:
            return match;
        }
      })
      .replace(/^(═+|─+)/gm, chalk.dim('$1'))
      .replace(/^(\x20\x20•)/gm, chalk.green('$1'))
      .replace(/(\w+:)/g, chalk.yellow('$1'))
      .replace(/(".*?")/g, chalk.brightMagenta('$1'))
      .replace(/(\d+)/g, chalk.brightBlue('$1'));
  }

  if (typeof data === 'object') {
    try {
      const jsonString = JSON.stringify(data, null, 2);
      return chalk.dim(jsonString);
    } catch (e) {
      console.err('e', e);
      return String(data);
    }
  }

  return String(data);
}

function showProgressBar(terminal, current, total, label = 'Progress') {
  const progress = new TerminalProgress(total, {
    terminal: terminal,
    width: 40,
    format: `${chalk.cyan(label)}: {bar} {percentage}% ({current}/{total})`,
    complete: '█',
    incomplete: '░',
  });

  progress.update(current);
}

// function formatOutput(data) {
//   if (typeof data === 'string') {
//     return data;
//   }

//   if (typeof data === 'object') {
//     try {
//       return JSON.stringify(data, null, 2);
//     } catch (e) {
//       console.error('e', e);
//       return String(data);
//     }
//   }

//   return String(data);
// }

function executeCommandWithStyle(terminal, command) {
  if (!command.trim()) return;

  // Handle built-in commands with enhanced styling
  const lowerCommand = command.toLowerCase().trim();

  if (lowerCommand === 'clear' || lowerCommand === 'cls') {
    terminal.clear();
    showProfessionalWelcome(terminal);
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

  // Show command execution with professional spinner
  terminal.write(
    `\r\n${chalk.dim('▶')} ${chalk.brightYellow(`Executing: ${command}`)}\r\n`
  );

  // Create and start spinner
  const spinner = new ora({
    text: 'Processing command...',
    spinner: 'dots',
    color: 'cyan',
    terminal: terminal,
  });

  spinner.start();
  window.mcpCurrentSpinner = spinner;

  // Send command to server
  const user = frappe.session.user;
  frappe.call({
    method: 'erpnext_mcp_server.api.vue_mcp_server.execute_terminal_command',
    args: { command: command, user },
    callback: (response) => {
      console.log('Command executed:', response);

      if (spinner) {
        if (
          response &&
          response.message &&
          response.message.success !== false
        ) {
          spinner.succeed('Command completed successfully');
        } else {
          spinner.warn('Command completed with warnings');
        }
      }

      window.setProcessingState && window.setProcessingState(false);
      showStyledPrompt(terminal);
    },
    error: (err) => {
      console.error('Command execution failed:', err);

      if (spinner) {
        spinner.fail(`Error: ${err.message || 'Command execution failed'}`);
      }

      window.setProcessingState && window.setProcessingState(false);
      showStyledPrompt(terminal);
    },
  });
}

// function executeCommand(terminal, command) {
//   if (!command.trim()) {
//     // terminal.write('\r\n');
//     // showPrompt(terminal);
//     return;
//   }

//   // Handle built-in commands
//   const lowerCommand = command.toLowerCase().trim();

//   if (lowerCommand === 'clear' || lowerCommand === 'cls') {
//     terminal.clear();
//     showWelcomeMessage(terminal);
//     return;
//   }

//   if (lowerCommand === 'help') {
//     showDetailedHelp(terminal);
//     return;
//   }

//   if (lowerCommand === 'status') {
//     showSystemStatus(terminal);
//     return;
//   }

//   // Show command being executed
//   terminal.write(`\r\n\x1b[90m▶\x1b[0m \x1b[33mExecuting: ${command}\x1b[0m`);
//   // terminal.write(`\r\n\x1b[90m⏳ Processing...\x1b[0m\r\n`);

//   // window.isProcessing = true;
//   // terminal.write('\r\n');

//   // Send command to server
//   frappe.call({
//     method: 'erpnext_mcp_server.api.vue_mcp_server.execute_terminal_command',
//     args: { command: command },
//     callback: (response) => {
//       console.log('Command executed:', response);
//       window.setProcessingState && window.setProcessingState(false);

//       if (response && response.message) {
//         // Success response
//         if (response.message.success !== false) {
//           terminal.write(`\x1b[32m✅ Command completed\x1b[0m\r\n`);
//         }
//       } else {
//         terminal.write(`\x1b[33m⚠️  No response from server\x1b[0m\r\n`);
//       }
//       // window.isProcessing = false;
//       // if (!response || response.exc) {
//       //   terminal.write('\x1b[31mError communicating with server\x1b[0m\r\n');
//       // }
//       showPrompt(terminal);
//     },
//     error: (err) => {
//       console.error('Command execution failed:', err);
//       window.setProcessingState && window.setProcessingState(false);
//       // window.isProcessing = false;
//       // terminal.write(`\x1b[31mError: ${err.message}\x1b[0m\r\n`);
//       terminal.write(
//         `\x1b[31m❌ Error: ${err.message || 'Command execution failed'}\x1b[0m\r\n`
//       );
//       showPrompt(terminal);
//     },
//   });
// }

function showDetailedHelp(terminal) {
  const helpContent = `
${figlet.generate('HELP', 'small', 'brightYellow')}

${chalk.brightCyan('📖 ERPNext MCP Terminal - Comprehensive Guide')}
${chalk.gray('━'.repeat(70))}

${chalk.brightYellow('📄 Document Operations:')}
  ${chalk.green('list_doctypes')}
    ${chalk.dim('→')} Lists all available document types organized by module
    ${chalk.cyan('Example:')} list_doctypes
    
  ${chalk.green('get_document')} ${chalk.dim('<doctype> <name>')}
    ${chalk.dim('→')} Retrieves and formats a specific document
    ${chalk.cyan('Examples:')} 
      get_document Customer "CUST-00001"
      get_document "Sales Invoice" "SINV-2024-00001"
    
  ${chalk.green('search_documents')} ${chalk.dim('<doctype> <query> [--limit N]')}
    ${chalk.dim('→')} Searches documents with advanced filtering
    ${chalk.cyan('Examples:')}
      search_documents Customer "John Doe"
      search_documents Item "laptop" --limit 10

${chalk.brightYellow('🗄️  Database Operations:')}
  ${chalk.green('execute_sql')} ${chalk.dim('<query>')}
    ${chalk.dim('→')} Executes SELECT queries with safety checks
    ${chalk.cyan('Examples:')}
      execute_sql "SELECT name, customer_name FROM \`tabCustomer\` LIMIT 10"
      execute_sql "SELECT COUNT(*) as total FROM \`tabSales Invoice\`"
    ${chalk.red('Note:')} Only SELECT queries allowed for security

${chalk.brightYellow('⚙️  System Operations:')}
  ${chalk.green('get_system_info')}
    ${chalk.dim('→')} Displays comprehensive system information
    ${chalk.dim('    Includes:')} Frappe/ERPNext versions, database info, platform details
    
  ${chalk.green('bench_command')} ${chalk.dim('<command>')}
    ${chalk.dim('→')} Executes safe bench commands
    ${chalk.cyan('Allowed:')} version, status, list-apps, doctor, config
    ${chalk.cyan('Example:')} bench_command --version

${chalk.brightYellow('📁 File Operations:')}
  ${chalk.green('list_files')} ${chalk.dim('<path> [--recursive]')}
    ${chalk.dim('→')} Lists directory contents with file details
    ${chalk.cyan('Examples:')}
      list_files ./apps
      list_files /home/frappe/frappe-bench --recursive
      
  ${chalk.green('read_file')} ${chalk.dim('<path> [--lines N]')}
    ${chalk.dim('→')} Displays file contents with optional line limiting
    ${chalk.cyan('Examples:')}
      read_file sites/common_site_config.json
      read_file apps/erpnext/erpnext/hooks.py --lines 20

${chalk.brightYellow('🖥️  Terminal Commands:')}
  ${chalk.green('help')}      Show this comprehensive help
  ${chalk.green('clear')}     Clear screen with welcome message  
  ${chalk.green('status')}    Display connection and system status
  ${chalk.green('Tab')}       Quick command reference table

${chalk.brightYellow('⌨️  Keyboard Shortcuts:')}
  ${chalk.cyan('↑/↓')}         Navigate command history
  ${chalk.cyan('Tab')}         Show available commands
  ${chalk.cyan('Ctrl+C')}      Cancel current command
  ${chalk.cyan('Ctrl+L')}      Clear screen
  ${chalk.cyan('Ctrl+D')}      Exit (on empty line)

${chalk.brightMagenta('💡 Advanced Features:')}
  • ${chalk.green('Professional styling')} with color-coded output
  • ${chalk.green('Loading spinners')} for long-running operations
  • ${chalk.green('Progress bars')} for batch operations
  • ${chalk.green('Error highlighting')} and categorization
  • ${chalk.green('Table formatting')} for structured data
  • ${chalk.green('Session persistence')} across re-connections

${chalk.gray('━'.repeat(70))}
${chalk.dim('Type any command above or press Tab for quick reference')}
`;

  terminal.write(helpContent);
  showStyledPrompt(terminal);
}

// function showDetailedHelp(terminal) {
//   const help = `\r\n\x1b[36m📖 ERPNext MCP Terminal - Detailed Help\x1b[0m\r\n
// \x1b[33m📄 Document Operations:\x1b[0m
//   \x1b[32mlist_doctypes\x1b[0m                     - List all available document types
//   \x1b[32mget_document\x1b[0m <doctype> <name>     - Get specific document
//     Example: get_document Customer "CUST-00001"
//     Example: get_document "Sales Invoice" "SINV-2024-00001"

//   \x1b[32msearch_documents\x1b[0m <doctype> <query> - Search documents
//     Example: search_documents Customer "John Doe"
//     Example: search_documents Item "laptop"

// \x1b[33m🗄️  Database Operations:\x1b[0m
//   \x1b[32mexecute_sql\x1b[0m <query>              - Execute SQL query (SELECT only)
//     Example: execute_sql "SELECT name, customer_name FROM \`tabCustomer\` LIMIT 10"
//     Example: execute_sql "SELECT COUNT(*) FROM \`tabSales Invoice\`"

// \x1b[33m⚙️  System Operations:\x1b[0m
//   \x1b[32mget_system_info\x1b[0m                   - Show system information
//   \x1b[32mlist_files\x1b[0m <path>                 - List files in directory
//   \x1b[32mstatus\x1b[0m                            - Show connection status

// \x1b[33m🖥️  Terminal Commands:\x1b[0m
//   \x1b[32mhelp\x1b[0m          - Show this help        \x1b[32mclear\x1b[0m    - Clear screen
//   \x1b[32mTab\x1b[0m           - Show quick commands    \x1b[32m↑/↓\x1b[0m      - Command history
//   \x1b[32mCtrl+C\x1b[0m        - Cancel command         \x1b[32mCtrl+L\x1b[0m   - Clear screen

// \x1b[33m💡 Pro Tips:\x1b[0m
//   • Use quotes for names with spaces: get_document "Sales Invoice" "SINV-001"
//   • Press Tab to see available commands quickly
//   • Use arrow keys to navigate command history
//   • Type 'status' to check system connection
// `;

//   terminal.write(help);
//   showPrompt(terminal);
// }

// function showSystemStatus(terminal) {
//   const user = frappe?.session?.user || 'Unknown';
//   const site = frappe?.boot?.sitename || 'Unknown';
//   const version = frappe?.boot?.versions?.frappe || 'Unknown';

//   const status = `\r\n\x1b[36m📊 System Status\x1b[0m\r\n
// \x1b[90m┌─────────────────────────────────────────────────────────────────┐\x1b[0m
// \x1b[90m│\x1b[0m \x1b[33mConnection:\x1b[0m \x1b[32m●\x1b[0m Connected                               \x1b[90m│\x1b[0m
// \x1b[90m│\x1b[0m \x1b[33mUser:\x1b[0m       ${user.padEnd(47)} \x1b[90m│\x1b[0m
// \x1b[90m│\x1b[0m \x1b[33mSite:\x1b[0m       ${site.padEnd(47)} \x1b[90m│\x1b[0m
// \x1b[90m│\x1b[0m \x1b[33mVersion:\x1b[0m    Frappe ${version.padEnd(39)} \x1b[90m│\x1b[0m
// \x1b[90m│\x1b[0m \x1b[33mTime:\x1b[0m       ${new Date().toLocaleString().padEnd(47)} \x1b[90m│\x1b[0m
// \x1b[90m└─────────────────────────────────────────────────────────────────┘\x1b[0m
// `;

//   terminal.write(status);
//   showPrompt(terminal);
// }

function showSystemStatus(terminal) {
  const user = frappe?.session?.user || 'Unknown';
  const site = frappe?.boot?.sitename || 'Unknown';
  const version = frappe?.boot?.versions?.frappe || 'Unknown';
  const currentTime = new Date().toLocaleString();

  // Create professional status display
  const statusData = [
    ['Connection', chalk.chain().green().bold().apply('● Connected')],
    ['User', chalk.cyan(user)],
    ['Site', chalk.cyan(site)],
    ['Frappe Version', chalk.yellow(version)],
    ['Session Time', chalk.dim(currentTime)],
    ['Terminal Features', chalk.green('Professional Mode ✨')],
  ];

  const statusTable = TerminalBox.table(statusData, {
    style: 'double',
    headers: ['Property', 'Value'],
    colors: { header: 'brightMagenta' },
  });

  terminal.write(
    '\r\n' + figlet.generate('STATUS', 'small', 'brightGreen') + '\r\n'
  );
  terminal.write(chalk.brightGreen(statusTable) + '\r\n');

  showStyledPrompt(terminal);
}

// Auto-initialize if container exists
document.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById('mcp-terminal-app');
  if (container) {
    initEnhancedMCPTerminal('mcp-terminal-app').catch((err) => {
      console.error(`Failed to initialize enhanced MCP terminal: ${err}`);
    });
  }
  // if (container) {
  //   initMCPTerminal('mcp-terminal-app').catch((err) => {
  //     console.error('Failed to initialize terminal:', err);
  //   });
  // }
});

// Export for manual initialization
// window.initMCPTerminal = initMCPTerminal;
window.initEnhancedMCPTerminal = initEnhancedMCPTerminal;

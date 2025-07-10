import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import {
  TerminalColors as chalk,
  TerminalSpinner as ora,
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

// Static ASCII Art
const ASCII_BANNER = `
  _____ ____  ____  _   _           _     __  __  ____ ____  
 | ____|  _ \\|  _ \\| \\ | | _____  _| |_  |  \\/  |/ ___|  _ \\ 
 |  _| | |_) | |_) |  \\| |/ _ \\ \\/ / __| | |\\/| | |   | |_) |
 | |___|  _ <|  __/| |\\  |  __/>  <| |_  | |  | | |___|  __/ 
 |_____|_| \\_\\_|   |_| \\_|\\___/_/\\_\\\\__| |_|  |_|\\____|_|    
                                                             
`;

// biome-ignore lint/correctness/noUnusedVariables: <explanation>
const STATIC_ASCII = {
  MAIN_BANNER: `
███████╗██████╗ ██████╗ ███╗   ██╗███████╗██╗  ██╗████████╗    ███╗   ███╗ ██████╗██████╗ 
██╔════╝██╔══██╗██╔══██╗████╗  ██║██╔════╝╚██╗██╔╝╚══██╔══╝    ████╗ ████║██╔════╝██╔══██╗
█████╗  ██████╔╝██████╔╝██╔██╗ ██║█████╗   ╚███╔╝    ██║       ██╔████╔██║██║     ██████╔╝
██╔══╝  ██╔══██╗██╔═══╝ ██║╚██╗██║██╔══╝   ██╔██╗    ██║       ██║╚██╔╝██║██║     ██╔═══╝ 
███████╗██║  ██║██║     ██║ ╚████║███████╗██╔╝ ██╗   ██║       ██║ ╚═╝ ██║╚██████╗██║     
╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝   ╚═╝       ╚═╝     ╚═╝ ╚═════╝╚═╝        
                                                             `,

  STATUS_HEADER: `
 ███████╗████████╗ █████╗ ████████╗██╗   ██╗███████╗
 ██╔════╝╚══██╔══╝██╔══██╗╚══██╔══╝██║   ██║██╔════╝
 ███████╗   ██║   ███████║   ██║   ██║   ██║███████╗
 ╚════██║   ██║   ██╔══██║   ██║   ██║   ██║╚════██║
 ███████║   ██║   ██║  ██║   ██║   ╚██████╔╝███████║
 ╚══════╝   ╚═╝   ╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚══════╝`,

  STATUS_HEADER_STANDARD: `
  ____ _____  _  _____ _   _ ____  
 / ___|_   _|/ \|_   _| | | / ___| 
 \___ \ | | / _ \ | | | | | \___ \ 
  ___) || |/ ___ \| | | |_| |___) |
 |____/ |_/_/   \_\_|  \___/|____/ 
 `,

  HELP_HEADER: `
 ██╗  ██╗███████╗██╗     ██████╗ 
 ██║  ██║██╔════╝██║     ██╔══██╗
 ███████║█████╗  ██║     ██████╔╝
 ██╔══██║██╔══╝  ██║     ██╔═══╝ 
 ██║  ██║███████╗███████╗██║     
 ╚═╝  ╚═╝╚══════╝╚══════╝╚═╝     `,

  HELP_HEADER_STANDARD: `
  _   _ _____ _     ____  
 | | | | ____| |   |  _ \ 
 | |_| |  _| | |   | |_) |
 |  _  | |___| |___|  __/ 
 |_| |_|_____|_____|_|    
 `,
};

const HEADER_LINE = '~'.repeat(80);
const FOOTER_LINE = '~'.repeat(80);

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
    this.currentUser = frappe?.session?.user || 'visitor';
    this.currentSite = frappe?.boot?.sitename || 'erpnext';
  }

  reset() {
    this.isProcessing = false;
    this.currentSpinner = null;
    this.currentCommand = '';
  }

  addToHistory(command) {
    console.log('command', command);
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

  updateUserInfo() {
    console.log('user', frappe?.session?.user);
    console.log('sitename', frappe?.boot?.sitename);
    this.currentUser = frappe?.session?.user || 'visitor';
    this.currentSite = frappe?.boot?.sitename || 'erpnext';
  }
}

// Enhanced Terminal Colors
const terminalColors = {
  primary: '#00ff41', // Matrix green
  secondary: '#ffd700', // Gold
  accent: '#00bfff', // Deep sky blue
  error: '#ff4444', // Red
  warning: '#ffaa00', // Orange
  info: '#44aaff', // Light blue
  success: '#44ff44', // Bright green
  dim: '#666666', // Gray
  background: '#0c0c0c', // Almost black
  foreground: '#c0c0c0', // Light gray
};

export const initEnhancedMCPTerminal = async (containerId) => {
  try {
    await new Promise((resolve) => setTimeout(resolve, 100));

    const container = document.getElementById(containerId);
    if (!container) throw new Error(`Container ${containerId} not found`);

    console.log('Initializing Enhanced MCP Terminal...', container);

    // Initialize terminal state
    const terminalState = new TerminalState();
    terminalState.updateUserInfo();

    console.log('terminalState', terminalState);

    // Initialize terminal theme
    const terminal = new Terminal({
      convertEol: true,
      disableStdin: false,
      cursorBlink: true,
      fontSize: 14,
      fontFamily:
        '"Cascadia Code", "Fira Code", "JetBrains Mono", "Courier New", monospace',
      theme: {
        background: terminalColors.background,
        foreground: terminalColors.foreground,
        cursor: terminalColors.primary,
        cursorAccent: terminalColors.background,
        selection: '#404040',
        black: '#000000',
        red: terminalColors.error,
        green: terminalColors.primary,
        yellow: terminalColors.secondary,
        blue: terminalColors.accent,
        magenta: '#bc3fbc',
        cyan: terminalColors.info,
        white: '#e5e5e5',
        brightBlack: terminalColors.dim,
        brightRed: '#ff6666',
        brightGreen: terminalColors.success,
        brightYellow: '#ffdd44',
        brightBlue: terminalColors.accent,
        brightMagenta: '#dd88dd',
        brightCyan: '#66ddff',
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

    // Show enhanced welcome with static ASCII
    await showMooCodingWelcome(terminal, terminalState);

    // Initialize MCP server status
    await checkMCPStatus(terminal, terminalState);

    // Setup enhanced realtime listeners
    setupEnhancedRealtimeListeners(terminal, terminalState);

    // Handle terminal input
    terminal.onData(async (data) => {
      await handleTerminalInput(terminal, terminalState, data);
    });

    // Store terminal globally
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

async function showMooCodingWelcome(terminal, terminalState) {
  // Clear and show header
  terminal.clear();
  terminal.write('\r\n');

  // Header with copyright
  const header = `${chalk.dim('MooCoding (MC). All rights reserved.')}

${chalk.chain().green().bold().apply(ASCII_BANNER)}

${chalk.chain().yellow().apply(HEADER_LINE)}
${chalk.chain().green().apply('Welcome to my interactive web terminal.')}
${chalk.chain().green().apply(`For a list of available commands, type '`)}${chalk.chain().cyan().bold().apply('help')}${chalk.chain().green().apply(`'.`)}
${chalk.chain().dim().apply(`${terminalState.currentUser}@${terminalState.currentSite}:~$ ls`)}
${chalk.chain().white().apply('Command not found. For a list of commands, type ')}${chalk.chain().cyan().bold().apply(`'help'`)}${chalk.chain().white().apply('.')}
${chalk.chain().dim().apply(`${terminalState.currentUser}@${terminalState.currentSite}:~$ help`)}

${chalk.chain().cyan().bold().apply('whois')}        ${chalk.chain().white().apply('Who is MooCoding?')}
${chalk.chain().cyan().bold().apply('whoami')}       ${chalk.chain().white().apply('Who are you?')}
${chalk.chain().cyan().bold().apply('video')}        ${chalk.chain().white().apply('View YouTube videos')}
${chalk.chain().cyan().bold().apply('social')}       ${chalk.chain().white().apply('Display social networks')}
${chalk.chain().cyan().bold().apply('projects')}     ${chalk.chain().white().apply('View coding projects')}
${chalk.chain().cyan().bold().apply('history')}      ${chalk.chain().white().apply('View command history')}
${chalk.chain().cyan().bold().apply('help')}         ${chalk.chain().white().apply('You obviously already know what this does')}
${chalk.chain().cyan().bold().apply('email')}        ${chalk.chain().white().apply('Email me')}
${chalk.chain().cyan().bold().apply('clear')}        ${chalk.chain().white().apply('Clear terminal')}
${chalk.chain().cyan().bold().apply('banner')}       ${chalk.chain().white().apply('Display the header')}

${chalk.chain().yellow().apply('🚀 ERPNext MCP Commands:')}
${chalk.chain().cyan().bold().apply('list_doctypes')}    ${chalk.chain().white().apply('List all ERPNext document types')}
${chalk.chain().cyan().bold().apply('get_document')}     ${chalk.chain().white().apply('Retrieve specific document')}
${chalk.chain().cyan().bold().apply('search_docs')}      ${chalk.chain().white().apply('Search documents with filters')}
${chalk.chain().cyan().bold().apply('execute_sql')}      ${chalk.chain().white().apply('Execute SQL queries (SELECT only)')}
${chalk.chain().cyan().bold().apply('system_info')}      ${chalk.chain().white().apply('Show ERPNext system information')}
${chalk.chain().cyan().bold().apply('mcp_status')}       ${chalk.chain().white().apply('Show MCP server connection status')}

${chalk.chain().yellow().apply(FOOTER_LINE)}
`;

  terminal.write(header);
  showMooCodingPrompt(terminal, terminalState);
}

function showMooCodingPrompt(terminal, terminalState) {
  if (!terminal) return;

  const promptLine = `${chalk.chain().dim().apply(`${terminalState.currentUser}@${terminalState.currentSite}:~$`)} `;
  terminal.write(`\r\n${promptLine}`);
}

async function handleTerminalInput(terminal, terminalState, data) {
  if (terminalState.isProcessing && terminalState.currentSpinner) return;

  const code = data.charCodeAt(0);

  switch (code) {
    case 13: // Enter
      if (terminalState.currentCommand.trim()) {
        terminalState.addToHistory(terminalState.currentCommand);
        await executeMooCodingCommand(
          terminal,
          terminalState,
          terminalState.currentCommand.trim()
        );
      } else {
        terminal.write('\r\n');
        showMooCodingPrompt(terminal, terminalState);
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
      showMooCodingPrompt(terminal, terminalState);
      break;

    case 12: // Ctrl+L (clear)
      await showMooCodingWelcome(terminal, terminalState);
      break;

    case 9: // Tab
      showAvailableCommands(terminal, terminalState);
      break;

    default:
      // Handle arrow keys for history
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
  showMooCodingPrompt(terminal, terminalState);
  terminal.write(newCommand);
}

async function executeMooCodingCommand(terminal, terminalState, command) {
  if (!command.trim()) return;

  const lowerCommand = command.toLowerCase().trim();

  // Handle built-in commands
  switch (lowerCommand) {
    case 'clear':
    case 'cls':
      terminal.write('\r\n');
      await showMooCodingWelcome(terminal, terminalState);
      return;

    case 'help':
      await showMooCodingWelcome(terminal, terminalState);
      return;

    case 'banner':
      terminal.write(
        `\r\n${chalk.chain().green().bold().apply(ASCII_BANNER)}\r\n`
      );
      showMooCodingPrompt(terminal, terminalState);
      return;

    case 'whois':
      showWhoIs(terminal, terminalState);
      return;

    case 'whoami':
      showWhoAmI(terminal, terminalState);
      return;

    case 'video':
      showVideo(terminal, terminalState);
      return;

    case 'social':
      showSocial(terminal, terminalState);
      return;

    case 'secret':
      showSecret(terminal, terminalState);
      return;

    case 'projects':
      showProjects(terminal, terminalState);
      return;

    case 'history':
      showHistory(terminal, terminalState);
      return;

    case 'email':
      showEmail(terminal, terminalState);
      return;

    case 'mcp_status':
      await showMCPStatus(terminal, terminalState);
      return;

    case 'system_info':
      await executeMCPCommand(terminal, terminalState, 'get_system_info', {});
      return;

    case 'list_doctypes':
      await executeMCPCommand(terminal, terminalState, 'list_doctypes', {});
      return;

    default:
      // Check if it's an MCP command
      if (isMCPCommand(lowerCommand)) {
        await handleMCPCommand(terminal, terminalState, command);
      } else {
        // Command not found
        terminal.write(
          `\r\n${chalk.chain().white().apply('Command not found. For a list of commands, type ')}${chalk.chain().cyan().bold().apply(`'help'`)}${chalk.chain().white().apply('.')}\r\n`
        );
        showMooCodingPrompt(terminal, terminalState);
      }
  }
}

function isMCPCommand(command) {
  const mcpCommands = [
    'get_document',
    'search_docs',
    'search_documents',
    'execute_sql',
    'list_files',
    'read_file',
    'bench_command',
  ];
  return mcpCommands.some((cmd) => command.startsWith(cmd));
}

async function handleMCPCommand(terminal, terminalState, command) {
  // Parse command and arguments
  const parts = command.split(' ');
  const cmdName = parts[0];
  const args = parts.slice(1);

  // Convert to MCP tool format
  let toolArgs = {};

  if (cmdName === 'get_document' && args.length >= 2) {
    toolArgs = { doctype: args[0], name: args[1] };
  } else if (cmdName === 'search_docs' || cmdName === 'search_documents') {
    if (args.length >= 2) {
      toolArgs = { doctype: args[0], query: args[1] };
    }
  } else if (cmdName === 'execute_sql' && args.length >= 1) {
    toolArgs = { query: args.join(' ') };
  }

  await executeMCPCommand(terminal, terminalState, cmdName, toolArgs);
}

async function executeMCPCommand(terminal, terminalState, toolName, args) {
  terminal.write(
    `\r\n${chalk.chain().yellow().apply(`▶ Executing MCP command: ${toolName}`)}\r\n`
  );

  const spinner = new ora({
    text: `Processing MCP command: ${toolName}`,
    spinner: 'dots',
    color: 'green',
    terminal: terminal,
  });

  spinner.start();
  terminalState.currentSpinner = spinner;

  try {
    const response = await frappe.call({
      method: 'erpnext_mcp_server.api.vue_mcp_server.execute_terminal_command',
      args: {
        command: `${toolName} ${JSON.stringify(args)}`,
        user: terminalState.currentUser,
      },
    });

    if (response && response.message && response.message.success) {
      spinner.succeed('MCP command completed');
    } else {
      spinner.warn('MCP command completed with warnings');
    }
  } catch (error) {
    console.error(`MCP command execution failed: ${error}`);
    spinner.fail(`Error: ${error.message || 'MCP command execution failed'}`);
    terminal.write(
      `\r\n${chalk.chain().red().bold().apply('❌ MCP ERROR:')} ${chalk.red(error.message)}\r\n`
    );
    showMooCodingPrompt(terminal, terminalState);
  }

  terminalState.currentSpinner = null;
}

// Command implementations
function showWhoIs(terminal, terminalState) {
  const whoIsText = `\r\n${chalk.chain().green().apply(__('Who is MooCoding?'))}
${chalk.chain().dim().apply('─'.repeat(20))}
${chalk.chain().white().apply(__('Accountant, Software Engineer & Content Creator'))}
${chalk.chain().white().apply(__('YouTube: MooCoding'))}
${chalk.chain().white().apply(__('Building awesome things with code!'))}
`;
  terminal.write(whoIsText);
  showMooCodingPrompt(terminal, terminalState);
}

function showWhoAmI(terminal, terminalState) {
  const whoAmIText = `\r\n${chalk.chain().green().apply('Who are you?')}
${chalk.chain().dim().apply('─'.repeat(15))}
${chalk.chain().white().apply(`User: ${terminalState.currentUser}`)}
${chalk.chain().white().apply(`Site: ${terminalState.currentSite}`)}
${chalk.chain().white().apply('Role: ERPNext Administrator')}
${chalk.chain().white().apply('Access Level: MCP Terminal User')}
`;
  terminal.write(whoAmIText);
  showMooCodingPrompt(terminal, terminalState);
}

function showVideo(terminal, terminalState) {
  const videoText = `\r\n${chalk.chain().green().apply('📺 YouTube Videos')}
${chalk.chain().dim().apply('─'.repeat(20))}
${chalk.chain().cyan().apply('🎬 How to Build a Terminal Website')}
${chalk.chain().cyan().apply('🎬 JavaScript Projects for Beginners')}
${chalk.chain().cyan().apply('🎬 Web Development Roadmap 2024')}
${chalk.chain().white().apply('Visit: youtube.com/@MooCoding')}
`;
  terminal.write(videoText);
  showMooCodingPrompt(terminal, terminalState);
}

function showSocial(terminal, terminalState) {
  const socialText = `\r\n${chalk.chain().green().apply('🌐 Social Networks')}
${chalk.chain().dim().apply('─'.repeat(20))}
${chalk.chain().cyan().apply('🐦 Twitter: @MooCoding')}
${chalk.chain().cyan().apply('🎮 GitHub: github.com/ManotLuijiu')}
`;
  terminal.write(socialText);
  showMooCodingPrompt(terminal, terminalState);
}

function showSecret(terminal, terminalState) {
  const secretText = `\r\n${chalk.chain().yellow().apply('🔐 Secret Found!')}
${chalk.chain().dim().apply('─'.repeat(15))}
${chalk.chain().green().apply('The password is: ')}${chalk.chain().red().bold().apply('coffee')}
${chalk.chain().white().apply("(But don't tell anyone! 🤫)")}
`;
  terminal.write(secretText);
  showMooCodingPrompt(terminal, terminalState);
}

function showProjects(terminal, terminalState) {
  const projectsText = `\r\n${chalk.chain().green().apply('💻 Coding Projects')}
${chalk.chain().dim().apply('─'.repeat(20))}
${chalk.chain().cyan().apply('🔧 ERPNext MCP Server')}
${chalk.chain().white().apply('Check out my GitHub for more!')}
`;
  terminal.write(projectsText);
  showMooCodingPrompt(terminal, terminalState);
}

function showHistory(terminal, terminalState) {
  terminal.write(
    `\r\n${chalk.chain().green().apply('📜 Command History')}\r\n`
  );
  terminal.write(chalk.chain().dim().apply('─'.repeat(20)) + '\r\n');

  if (terminalState.commandHistory.length === 0) {
    terminal.write(
      chalk.chain().white().apply('No commands in history yet.') + '\r\n'
    );
  } else {
    terminalState.commandHistory.forEach((cmd, index) => {
      terminal.write(
        `${chalk
          .chain()
          .dim()
          .apply(`${index + 1}.`)} ${chalk.chain().cyan().apply(cmd)}\r\n`
      );
    });
  }

  showMooCodingPrompt(terminal, terminalState);
}

function showEmail(terminal, terminalState) {
  const emailText = `\r\n${chalk.chain().red().apply('📧 Email Policy')}
${chalk.chain().dim().apply('─'.repeat(15))}
${chalk.chain().white().apply('Please email me directly at')}
${chalk.chain().white().apply('moocoding@gmail.com')}
${chalk.chain().yellow().apply('Thanks you! 😊')}
`;
  terminal.write(emailText);
  showMooCodingPrompt(terminal, terminalState);
}

function showAvailableCommands(terminal, terminalState) {
  terminal.write(
    `\r\n${chalk.chain().yellow().apply('📚 Quick Command Reference')}\r\n`
  );
  terminal.write(chalk.chain().dim().apply('─'.repeat(30)) + '\r\n');

  const commands = [
    ['help', 'Show all available commands'],
    ['whois', 'Learn about Forrest'],
    ['whoami', 'Your user information'],
    ['projects', 'View coding projects'],
    ['social', 'Social media links'],
    ['mcp_status', 'MCP server status'],
    ['list_doctypes', 'ERPNext document types'],
    ['clear', 'Clear terminal screen'],
  ];

  commands.forEach(([cmd, desc]) => {
    terminal.write(
      `${chalk.chain().cyan().bold().apply(cmd.padEnd(15))} ${chalk.chain().white().apply(desc)}\r\n`
    );
  });

  terminal.write(
    `\r\n${chalk.chain().dim().apply('Press Tab anytime to see this list')}\r\n`
  );
  showMooCodingPrompt(terminal, terminalState);
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
        response.message.status === 'connected' ? 'green' : 'yellow';
      const statusText =
        response.message.status === 'connected' ? 'CONNECTED' : 'STARTING';

      terminal.write(
        `\r\n${chalk.chain()[statusColor]().bold().apply(`MCP SERVER ${statusText}`)}\r\n`
      );
    }
  } catch (error) {
    console.error(error);
    terminal.write(
      `\r\n${chalk.chain().red().bold().apply('❌ MCP CONNECTION ERROR')}\r\n`
    );
  }
}

async function showMCPStatus(terminal, terminalState) {
  try {
    const response = await frappe.call({
      method: 'erpnext_mcp_server.api.vue_mcp_server.get_terminal_status',
    });

    console.log('response showMCPStatus', response);

    if (response.message && response.message.success) {
      const status = response.message;
      const connectionStatus =
        status.status === 'connected'
          ? chalk.chain().green().bold().apply('● CONNECTED')
          : chalk.chain().red().bold().apply('● DISCONNECTED');

      terminal.write(
        `\r\n${chalk.chain().green().apply('🖥️ MCP Server Status')}\r\n`
      );
      terminal.write(chalk.chain().dim().apply('─'.repeat(25)) + '\r\n');
      terminal.write(`Connection: ${connectionStatus}\r\n`);
      terminal.write(
        `Session: ${chalk
          .chain()
          .cyan()
          .apply(status.session || 'N/A')}\r\n`
      );
      terminal.write(`User: ${chalk.chain().cyan().apply(status.user)}\r\n`);
      terminal.write(`Site: ${chalk.chain().cyan().apply(status.site)}\r\n`);
      terminal.write(
        `Protocol: ${chalk.chain().yellow().apply('JSON-RPC over stdio')}\r\n`
      );
    }
  } catch (error) {
    console.error(error);
    terminal.write(
      `\r\n${chalk.chain().red().bold().apply('❌ STATUS ERROR')}\r\n`
    );
  }

  showMooCodingPrompt(terminal, terminalState);
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
          `\r\n${chalk.chain().yellow().apply(`▶ ${message.data}`)}\r\n`
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
          `\r\n${chalk.chain().green().bold().apply('✅ SUCCESS:')} ${chalk.chain().green().apply(message.data)}\r\n`
        );
        break;

      case 'info':
        terminal.write(
          `\r\n${chalk.chain().blue().bold().apply('ℹ️  INFO:')} ${chalk.chain().cyan().apply(message.data)}\r\n`
        );
        break;

      case 'warning':
        terminal.write(
          `\r\n${chalk.chain().yellow().bold().apply('⚠️  WARNING:')} ${chalk.chain().yellow().apply(message.data)}\r\n`
        );
        break;

      default:
        terminal.write(`\r\n${message.data}\r\n`);
    }

    showMooCodingPrompt(terminal, terminalState);
  });

  // MCP status updates
  frappe.realtime.on('mcp_status', (message) => {
    terminalState.mcpStatus = message.status;

    switch (message.status) {
      case 'connected':
        terminal.write(
          `\r\n${chalk.chain().green().bold().apply('🟢 MCP CONNECTED')}\r\n`
        );
        break;
      case 'disconnected':
        terminal.write(
          `\r\n${chalk.chain().red().bold().apply('🔴 MCP DISCONNECTED')}\r\n`
        );
        break;
      case 'error':
        terminal.write(
          `\r\n${chalk.chain().red().bold().apply('❌ MCP ERROR:')} ${chalk.red(message.error)}\r\n`
        );
        break;
    }

    showMooCodingPrompt(terminal, terminalState);
  });
}

function formatMCPOutput(data) {
  if (typeof data === 'string') {
    return data
      .replace(
        /^(📋|📄|🔍|📊|🖥️|📁|🔧|⚙️|🗄️)/gm,
        chalk.chain().cyan().bold().apply('$1')
      )
      .replace(/^(✅|❌|⚠️|ℹ️)/gm, (match) => {
        switch (match) {
          case '✅':
            return chalk.chain().green().bold().apply(match);
          case '❌':
            return chalk.chain().red().bold().apply(match);
          case '⚠️':
            return chalk.chain().yellow().bold().apply(match);
          case 'ℹ️':
            return chalk.chain().blue().bold().apply(match);
          default:
            return match;
        }
      })
      .replace(/^(═+|─+)/gm, chalk.dim('$1'))
      .replace(/^(\s+•)/gm, chalk.green('$1'))
      .replace(/(\w+:)/g, chalk.yellow('$1'))
      .replace(/(".*?")/g, chalk.chain().magenta().bold().apply('$1'))
      .replace(/(\d+)/g, chalk.chain().blue().bold().apply('$1'))
      .replace(
        /(Customer|Sales Invoice|Item|DocType)/g,
        chalk.chain().cyan().bold().apply('$1')
      )
      .replace(
        /(SELECT|FROM|WHERE|ORDER BY|LIMIT)/g,
        chalk.chain().magenta().bold().apply('$1')
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

// Auto-initialize if container exists
document.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById('mcp-terminal-app');
  if (container) {
    initEnhancedMCPTerminal('mcp-terminal-app').catch((err) => {
      console.error(`Failed to initialize enhanced MCP terminal: ${err}`);
    });
  }
});

// Export for manual initialization
window.initEnhancedMCPTerminal = initEnhancedMCPTerminal;

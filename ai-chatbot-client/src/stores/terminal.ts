import type { WebContainer, WebContainerProcess } from '@webcontainer/api';
import { atom, type WritableAtom } from 'nanostores';
import type { Terminal } from '@xterm/xterm';
import { newBoltShellProcess, newShellProcess } from '../lib/shell';

export type ITerminal = Terminal;

// Simple colored text utility
export const coloredText = {
  red: (text: string) => `\x1b[31m${text}\x1b[0m`,
  green: (text: string) => `\x1b[32m${text}\x1b[0m`,
  yellow: (text: string) => `\x1b[33m${text}\x1b[0m`,
  blue: (text: string) => `\x1b[34m${text}\x1b[0m`,
  magenta: (text: string) => `\x1b[35m${text}\x1b[0m`,
  cyan: (text: string) => `\x1b[36m${text}\x1b[0m`,
};

// Declare import.meta.hot to fix TypeScript errors
declare global {
  interface ImportMeta {
    hot?: {
      data: Record<string, any>;
    };
  }
}

// Maximum number of terminals allowed
export const MAX_TERMINALS = 3;

// Terminal actions for state management
export const terminalActions = {
  setTerminalRunning: (
    terminalId: string,
    isRunning: boolean,
    command?: string
  ) => {
    // Action to set terminal running state
    console.log(
      `Terminal ${terminalId} running: ${isRunning}${command ? ` (${command})` : ''}`
    );
  },
  setTerminalInteractive: (terminalId: string, isInteractive: boolean) => {
    // Action to set terminal interactive state
    console.log(`Terminal ${terminalId} interactive: ${isInteractive}`);
  },
};

// Terminal metadata interface
export interface TerminalSession {
  id: string;
  terminal: ITerminal | null;
  process: WebContainerProcess | null;
  type: 'bolt' | 'standard';
  active: boolean;
}

export class TerminalStore {
  private webcontainer: Promise<WebContainer>;
  private boltTerminal = newBoltShellProcess();

  // Terminal session management
  terminalSessions: WritableAtom<TerminalSession[]> =
    import.meta.hot?.data?.terminalSessions ??
    atom([
      {
        id: 'bolt',
        terminal: null,
        process: null,
        type: 'bolt',
        active: true,
      },
    ]);

  // Terminal visibility and UI state
  showTerminal: WritableAtom<boolean> =
    import.meta.hot?.data?.showTerminal ?? atom(true);
  terminalHeight: WritableAtom<string> =
    import.meta.hot?.data?.terminalHeight ?? atom('250px');
  activeTerminalId: WritableAtom<string> =
    import.meta.hot?.data?.activeTerminalId ?? atom('bolt');
  terminalCount: WritableAtom<number> =
    import.meta.hot?.data?.terminalCount ?? atom(1);

  constructor(webcontainerPromise: Promise<WebContainer>) {
    this.webcontainer = webcontainerPromise;

    if (import.meta.hot) {
      import.meta.hot.data = import.meta.hot.data || {};
      import.meta.hot.data.terminalSessions = this.terminalSessions;
      import.meta.hot.data.showTerminal = this.showTerminal;
      import.meta.hot.data.terminalHeight = this.terminalHeight;
      import.meta.hot.data.activeTerminalId = this.activeTerminalId;
      import.meta.hot.data.terminalCount = this.terminalCount;
    }
  }

  // Access the bolt terminal instance
  get getBoltTerminal() {
    return this.boltTerminal;
  }

  // Toggle terminal visibility
  toggleTerminal(value?: boolean) {
    this.showTerminal.set(
      value !== undefined ? value : !this.showTerminal.get()
    );
  }

  // Set terminal panel height
  setTerminalHeight(height: string) {
    this.terminalHeight.set(height);
  }

  // Set the active terminal
  setActiveTerminal(id: string) {
    const sessions = this.terminalSessions.get();
    const sessionExists = sessions.some((session) => session.id === id);

    if (sessionExists) {
      this.activeTerminalId.set(id);

      // Update active state for all sessions
      const updatedSessions = sessions.map((session) => ({
        ...session,
        active: session.id === id,
      }));

      this.terminalSessions.set(updatedSessions);
    }
  }

  // Initialize the bolt terminal
  async initBoltTerminal(terminal: ITerminal) {
    try {
      if (!terminal.cols || !terminal.rows) {
        console.warn(
          'Terminal dimensions are not available yet, using defaults'
        );
      }

      console.log(
        `Initializing bolt terminal with dimensions: ${terminal.cols || 80}x${terminal.rows || 24}`
      );

      const wc = await this.webcontainer;
      await this.boltTerminal.init(wc, terminal);

      // Update the terminal reference in sessions
      const sessions = this.terminalSessions.get();
      const updatedSessions = sessions.map((session) => {
        if (session.id === 'bolt') {
          return { ...session, terminal };
        }
        return session;
      });

      this.terminalSessions.set(updatedSessions);
    } catch (error: any) {
      console.error('Error initializing bolt shell:', error);
      terminal.write(
        coloredText.red(
          `\r\nError initializing bolt shell: ${error.message}\r\n`
        )
      );
      return;
    }
  }

  // Attach a standard terminal
  async attachTerminal(terminal: ITerminal, terminalId: string) {
    try {
      const wc = await this.webcontainer;
      const shellProcess = await newShellProcess(wc, terminal);

      // Update the terminal reference in sessions
      const sessions = this.terminalSessions.get();
      const sessionIndex = sessions.findIndex((s) => s.id === terminalId);

      if (sessionIndex >= 0) {
        const updatedSessions = [...sessions];
        updatedSessions[sessionIndex] = {
          ...updatedSessions[sessionIndex],
          terminal,
          process: shellProcess,
        };

        this.terminalSessions.set(updatedSessions);
      }

      return shellProcess;
    } catch (error: any) {
      terminal.write(
        coloredText.red('Failed to spawn shell\n\n') + error.message
      );
      return null;
    }
  }

  // Handle terminal resize event
  onTerminalResize(cols: number, rows: number, terminalId?: string) {
    console.log(
      `Terminal resize: ${cols}x${rows}${terminalId ? ` for ${terminalId}` : ''}`
    );

    const sessions = this.terminalSessions.get();

    if (terminalId) {
      // Resize specific terminal
      const sessionIndex = sessions.findIndex((s) => s.id === terminalId);
      if (sessionIndex >= 0) {
        const session = sessions[sessionIndex];
        if (session.type === 'bolt') {
          // Resize bolt terminal
          this.boltTerminal.resize?.(cols, rows);
        } else if (session.process) {
          // Resize standard terminal
          session.process.resize({ cols, rows });
        }
      }
    } else {
      // Resize all terminals if no specific ID provided

      // Resize the Bolt terminal
      this.boltTerminal.resize?.(cols, rows);

      // Resize all other terminal processes
      for (const session of sessions) {
        if (session.process && session.type === 'standard') {
          session.process.resize({ cols, rows });
        }
      }
    }
  }

  // Create a new terminal session
  createNewTerminal() {
    const currentCount = this.terminalCount.get();

    if (currentCount >= MAX_TERMINALS) {
      console.warn(`Maximum number of terminals (${MAX_TERMINALS}) reached`);
      return false;
    }

    const newCount = currentCount + 1;
    const newTerminalId = `terminal_${Date.now()}`;

    // Add the new terminal session
    const sessions = this.terminalSessions.get();
    const newSession: TerminalSession = {
      id: newTerminalId,
      terminal: null,
      process: null,
      type: 'standard',
      active: false,
    };

    this.terminalSessions.set([...sessions, newSession]);
    this.terminalCount.set(newCount);

    // Set the new terminal as active
    this.setActiveTerminal(newTerminalId);

    return true;
  }

  // Close a terminal session
  closeTerminal(terminalId: string) {
    if (terminalId === 'bolt') {
      console.warn('Cannot close the main bolt terminal');
      return false;
    }

    const sessions = this.terminalSessions.get();
    const sessionIndex = sessions.findIndex((s) => s.id === terminalId);

    if (sessionIndex >= 0) {
      // Clean up resources for the terminal being closed
      const session = sessions[sessionIndex];
      if (session.process) {
        try {
          // Send SIGTERM to the process
          session.process.kill();
        } catch (error) {
          console.error('Error killing terminal process:', error);
        }
      }

      // Remove the session
      const updatedSessions = sessions.filter((s) => s.id !== terminalId);
      this.terminalSessions.set(updatedSessions);

      // Update terminal count
      this.terminalCount.set(this.terminalCount.get() - 1);

      // If the closed terminal was active, activate bolt terminal
      if (session.active) {
        this.setActiveTerminal('bolt');
      }

      return true;
    }

    return false;
  }
}

// Create and export a default terminal store instance
let terminalStoreInstance: TerminalStore | null = null;

export function createTerminalStore(
  webcontainerPromise: Promise<WebContainer>
): TerminalStore {
  terminalStoreInstance = new TerminalStore(webcontainerPromise);
  return terminalStoreInstance;
}

export function getTerminalStore(): TerminalStore | null {
  return terminalStoreInstance;
}

// Default export for the terminal store module
const terminalStoreExports = {
  createTerminalStore,
  getTerminalStore,
  terminalActions,
};

export default terminalStoreExports;

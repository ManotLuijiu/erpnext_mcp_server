import type { WebContainer, WebContainerProcess } from '@webcontainer/api';
import type { Terminal } from '@xterm/xterm';
import { atom } from 'nanostores';

// Helper function to create a promise with externally accessible resolve/reject
function withResolvers<T>() {
  let resolve: (value: T | PromiseLike<T>) => void;
  let reject: (reason?: any) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve: resolve!, reject: reject! };
}

export async function newShellProcess(
  webcontainer: WebContainer,
  terminal: Terminal
) {
  const args: string[] = [];

  // we spawn a JSH process with a fallback cols and rows in case the process is not attached yet to a visible terminal
  const process = await webcontainer.spawn('/bin/jsh', ['--osc', ...args], {
    terminal: {
      cols: terminal.cols ?? 80,
      rows: terminal.rows ?? 15,
    },
  });

  const input = process.input.getWriter();
  const output = process.output;

  const jshReady = withResolvers<void>();

  let isInteractive = false;
  output.pipeTo(
    new WritableStream({
      write(data) {
        if (!isInteractive) {
          const [, osc] = data.match(/\x1b\]654;([^\x07]+)\x07/) || [];

          if (osc === 'interactive') {
            // wait until we see the interactive OSC
            isInteractive = true;

            jshReady.resolve();
          }
        }

        terminal.write(data);
      },
    })
  );

  terminal.onData((data) => {
    // console.log('terminal onData', { data, isInteractive });

    if (isInteractive) {
      input.write(data);
    }
  });

  await jshReady.promise;

  return process;
}

export type ExecutionResult = { output: string; exitCode: number } | undefined;

export class BoltShell {
  private _terminal: Terminal | null = null;
  private _process: WebContainerProcess | null = null;
  private _webcontainer: WebContainer | null = null;
  executionState = atom<
    | {
        sessionId: string;
        active: boolean;
        executionPrms?: Promise<any>;
        abort?: () => void;
      }
    | undefined
  >();
  private outputStream: ReadableStreamDefaultReader<string> | undefined;
  private shellInputStream: WritableStreamDefaultWriter<string> | undefined;

  constructor() {}

  get terminal(): Terminal | null {
    return this._terminal;
  }

  get process(): WebContainerProcess | null {
    return this._process;
  }

  async init(webcontainer: WebContainer, terminal: Terminal) {
    if (this._process) {
      console.warn('BoltShell already initialized.');
      return;
    }
    this._webcontainer = webcontainer;
    this._terminal = terminal;

    console.log('BoltShell: Spawning shell process...');
    try {
      // Ensure we have valid dimensions, use defaults if not available
      const cols = this._terminal.cols || 80;
      const rows = this._terminal.rows || 24;

      console.log(`BoltShell: Using terminal dimensions ${cols}x${rows}`);

      this._process = await this._webcontainer.spawn('/bin/jsh', ['--osc'], {
        terminal: {
          cols,
          rows,
        },
      });

      console.log('BoltShell: Piping output/input...');
      // Pipe process output to terminal
      this._process.output.pipeTo(
        new WritableStream({
          write: (data) => {
            this._terminal?.write(data);
          },
        })
      );

      // Pipe terminal input to process
      const input = this._process.input.getWriter();
      this._terminal.onData((data) => {
        input.write(data);
      });

      console.log('BoltShell: Initialization complete.');

      // Wait for the initial prompt or process exit
      await Promise.race([
        this._process.exit,
        this.waitTillOscCode('prompt'), // Wait for the prompt OSC code
      ]);

      console.log('BoltShell: Initial prompt received or process exited.');
    } catch (error) {
      console.error('BoltShell: Failed to initialize process', error);
      this._terminal?.write(`\r\nError spawning shell: ${error}\r\n`);
      this._process = null; // Ensure process is null on failure
    }
  }

  async newBoltShellProcess(webcontainer: WebContainer, terminal: Terminal) {
    const args: string[] = [];
    const process = await webcontainer.spawn('/bin/jsh', ['--osc', ...args], {
      terminal: {
        cols: terminal.cols ?? 80,
        rows: terminal.rows ?? 15,
      },
    });

    const input = process.input.getWriter();
    this.shellInputStream = input;

    // Tee the output so we can have three independent readers
    const [streamA, streamB] = process.output.tee();
    const [streamC, streamD] = streamB.tee();

    const jshReady = withResolvers<void>();
    let isInteractive = false;
    streamA.pipeTo(
      new WritableStream({
        write(data) {
          if (!isInteractive) {
            const [, osc] = data.match(/\x1b\]654;([^\x07]+)\x07/) || [];

            if (osc === 'interactive') {
              isInteractive = true;
              jshReady.resolve();
            }
          }

          terminal.write(data);
        },
      })
    );

    terminal.onData((data) => {
      if (isInteractive) {
        input.write(data);
      }
    });

    await jshReady.promise;

    // Return all streams for use in init
    return {
      process,
      terminalStream: streamA,
      commandStream: streamC,
      expoUrlStream: streamD,
    };
  }

  // Dedicated background watcher for Expo URL
  private async _watchExpoUrlInBackground(stream: ReadableStream<string>) {
    const reader = stream.getReader();
    let buffer = '';
    const expoUrlRegex = /(exp:\/\/[^\s]+)/;

    while (true) {
      const { value, done } = await reader.read();

      if (done) {
        break;
      }

      buffer += value || '';

      if (buffer.length > 2048) {
        buffer = buffer.slice(-2048);
      }
    }
  }

  get getTerminal() {
    return this._terminal;
  }

  get getProcess() {
    return this._process;
  }

  async executeCommand(
    sessionId: string,
    command: string,
    abort?: () => void
  ): Promise<ExecutionResult> {
    if (!this._process || !this._terminal) {
      return undefined;
    }

    const state = this.executionState.get();

    if (state?.active && state.abort) {
      state.abort();
    }

    /*
     * interrupt the current execution
     *  this.shellInputStream?.write('\x03');
     */
    this._terminal.input('\x03');
    await this.waitTillOscCode('prompt');

    if (state && state.executionPrms) {
      await state.executionPrms;
    }

    //start a new execution
    this._terminal.input(command.trim() + '\n');

    //wait for the execution to finish
    const executionPromise = this.waitTillOscCode('prompt');
    this.executionState.set({
      sessionId,
      active: true,
      executionPrms: executionPromise,
      abort,
    });

    const resp = await executionPromise;
    this.executionState.set({ sessionId, active: false });

    if (resp) {
      try {
        resp.output = cleanTerminalOutput(resp.output);
      } catch (error) {
        console.log('failed to format terminal output', error);
      }
    }

    return resp;
  }

  onQRCodeDetected?: (qrCode: string) => void;

  async waitTillOscCode(waitCode: string) {
    let fullOutput = '';
    let exitCode: number = 0;
    let buffer = ''; // <-- Add a buffer to accumulate output

    if (!this.outputStream) {
      return { output: fullOutput, exitCode };
    }

    const tappedStream = this.outputStream;

    while (true) {
      const { value, done } = await tappedStream.read();

      if (done) {
        break;
      }

      const text = value || '';
      fullOutput += text;
      buffer += text; // <-- Accumulate in buffer

      // Extract Expo URL from buffer and set store

      // Check if command completion signal with exit code
      const [, osc, , , code] =
        text.match(/\x1b\]654;([^\x07=]+)=?((-?\d+):(\d+))?\x07/) || [];

      if (osc === 'exit') {
        exitCode = parseInt(code, 10);
      }

      if (osc === waitCode) {
        break;
      }
    }

    return { output: fullOutput, exitCode };
  }

  // Public method to resize the underlying shell process
  resize(cols: number, rows: number) {
    this._process?.resize({ cols, rows });
  }
}

/**
 * Cleans and formats terminal output while preserving structure and paths
 * Handles ANSI, OSC, and various terminal control sequences
 */
export function cleanTerminalOutput(input: string): string {
  // Step 1: Remove OSC sequences (including those with parameters)
  const removeOsc = input
    .replace(/\x1b\](\d+;[^\x07\x1b]*|\d+[^\x07\x1b]*)\x07/g, '')
    .replace(/\](\d+;[^\n]*|\d+[^\n]*)/g, '');

  // Step 2: Remove ANSI escape sequences and color codes more thoroughly
  const removeAnsi = removeOsc
    // Remove all escape sequences with parameters
    .replace(/\u001b\[[\?]?[0-9;]*[a-zA-Z]/g, '')
    .replace(/\x1b\[[\?]?[0-9;]*[a-zA-Z]/g, '')
    // Remove color codes
    .replace(/\u001b\[[0-9;]*m/g, '')
    .replace(/\x1b\[[0-9;]*m/g, '')
    // Clean up any remaining escape characters
    .replace(/\u001b/g, '')
    .replace(/\x1b/g, '');

  // Step 3: Clean up carriage returns and newlines
  const cleanNewlines = removeAnsi
    .replace(/\r\n/g, '\n')
    .replace(/\r/g, '\n')
    .replace(/\n{3,}/g, '\n\n');

  // Step 4: Add newlines at key breakpoints while preserving paths
  const formatOutput = cleanNewlines
    // Preserve prompt line
    .replace(/^([~\/][^\n❯]+)❯/m, '$1\n❯')
    // Add newline before command output indicators
    .replace(/(?<!^|\n)>/g, '\n>')
    // Add newline before error keywords without breaking paths
    .replace(
      /(?<!^|\n|\w)(error|failed|warning|Error|Failed|Warning):/g,
      '\n$1:'
    )
    // Add newline before 'at' in stack traces without breaking paths
    .replace(/(?<!^|\n|\/)(at\s+(?!async|sync))/g, '\nat ')
    // Ensure 'at async' stays on same line
    .replace(/\bat\s+async/g, 'at async')
    // Add newline before npm error indicators
    .replace(/(?<!^|\n)(npm ERR!)/g, '\n$1');

  // Step 5: Clean up whitespace while preserving intentional spacing
  const cleanSpaces = formatOutput
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
    .join('\n');

  // Step 6: Final cleanup
  return cleanSpaces
    .replace(/\n{3,}/g, '\n\n') // Replace multiple newlines with double newlines
    .replace(/:\s+/g, ': ') // Normalize spacing after colons
    .replace(/\s{2,}/g, ' ') // Remove multiple spaces
    .replace(/^\s+|\s+$/g, '') // Trim start and end
    .replace(/\u0000/g, ''); // Remove null characters
}

export function newBoltShellProcess(): BoltShell {
  return new BoltShell();
}

// PersistentShell class for WebContainerManager
export class PersistentShell {
  private shell: BoltShell;
  private initialized: boolean = false;
  private terminalRef: any = null;

  constructor() {
    this.shell = new BoltShell();
  }

  isInitialized(): boolean {
    return this.initialized;
  }

  async init(webcontainer: WebContainer, terminalRef: any): Promise<void> {
    if (terminalRef) {
      this.terminalRef = terminalRef;
    }

    if (this.initialized) return;

    try {
      // Make sure we have a valid terminal before proceeding
      if (!terminalRef?.current?.terminal) {
        console.error('PersistentShell: Terminal reference is not available');
        throw new Error('Terminal reference is not available');
      }

      console.log('PersistentShell: Initializing with terminal', {
        cols: terminalRef.current.terminal.cols || 80,
        rows: terminalRef.current.terminal.rows || 24,
      });

      await this.shell.init(webcontainer, terminalRef.current.terminal);
      this.initialized = true;
    } catch (error) {
      console.error('Failed to initialize persistent shell:', error);
      throw error;
    }
  }

  async restore(terminalRef: any): Promise<void> {
    this.terminalRef = terminalRef;
    // No need to re-initialize if already initialized
  }

  getDimensions() {
    return { cols: 80, rows: 24 };
  }

  async executeCommand(
    command: string,
    args: string[] = [],
    terminalId: string = 'main'
  ): Promise<{ exitCode: number }> {
    if (!this.initialized) {
      console.warn('Attempting to execute command on uninitialized shell');
      return { exitCode: 1 };
    }

    try {
      const result = await this.shell.executeCommand(terminalId, command);
      return { exitCode: result?.exitCode || 0 };
    } catch (error) {
      console.error('Error executing command:', error);
      return { exitCode: 1 };
    }
  }

  dispose(preserveState: boolean = true): void {
    // Clean up resources but optionally preserve state
    this.initialized = false;
    if (!preserveState) {
      this.terminalRef = null;
    }
  }
}

export function createPersistentShell(): PersistentShell {
  return new PersistentShell();
}

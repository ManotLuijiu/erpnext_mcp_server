'use client';

import {
  useEffect,
  useRef,
  useState,
  forwardRef,
  useImperativeHandle,
} from 'react';
import { Terminal as XTerm } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { WebLinksAddon } from '@xterm/addon-web-links';
import { useWebContainer } from '@/hooks/useWebContainer';
import { cn } from '@/lib/utils';
// import { MAX_TERMINALS } from '@/stores/terminal';

// Import styles
import '@xterm/xterm/css/xterm.css';

export interface TerminalRef {
  terminal: XTerm | null;
  writeToTerminal: (text: string) => void;
  clearTerminal: () => void;
  focus: () => void;
  getDimensions: () => { cols: number; rows: number };
  resize: () => void;
}

interface TerminalProps {
  id: string;
  active?: boolean;
  className?: string;
  onCommand?: (command: string) => void;
  onResize?: (cols: number, rows: number) => void;
  mode?: 'default' | 'minimized' | 'fullscreen';
  initialOptions?: {
    fontSize?: number;
    fontFamily?: string;
    theme?: {
      background?: string;
      foreground?: string;
      [key: string]: string | undefined;
    };
  };
}

export const Terminal = forwardRef<TerminalRef, TerminalProps>(
  (
    {
      id,
      active = false,
      className,
      onCommand,
      onResize,
      // mode = 'default',
      initialOptions,
    },
    ref
  ) => {
    const terminalRef = useRef<HTMLDivElement>(null);
    const [terminal, setTerminal] = useState<XTerm | null>(null);
    const fitAddonRef = useRef<FitAddon | null>(null);
    // const [isTerminalReady, setIsTerminalReady] = useState(false);
    const [terminalSize, setTerminalSize] = useState({ cols: 80, rows: 24 });
    // const [command, setCommand] = useState('');
    // const { runTerminalCommand } = useWebContainer(
    //   ref as React.MutableRefObject<TerminalRef | null>
    // );
    const { runTerminalCommand } = useWebContainer();

    // Initialize addons and terminal
    useEffect(() => {
      if (!terminalRef.current) return;

      // Only create a new terminal if one doesn't already exist
      if (!terminal) {
        console.log(`Initializing terminal ${id}`);

        // Initialize addons
        const fitAddon = new FitAddon();
        const webLinksAddon = new WebLinksAddon();
        fitAddonRef.current = fitAddon;

        // Create terminal with options
        const term = new XTerm({
          cursorBlink: true,
          fontSize: initialOptions?.fontSize || 14,
          fontFamily: initialOptions?.fontFamily || 'Menlo, monospace',
          theme: {
            background: '#151718',
            foreground: '#f8f8f8',
            cursor: '#a0a0a0',
            selectionBackground: '#3b4452',
            ...(initialOptions?.theme || {}),
          },
          scrollback: 5000,
          convertEol: true,
          allowTransparency: true,
        });

        // Load addons
        term.loadAddon(fitAddon);
        term.loadAddon(webLinksAddon);

        // Open terminal in the container
        term.open(terminalRef.current);

        // Write an initial welcome message
        term.write(
          '\r\n\x1b[1;34mTerminal initialized. Ready for commands.\x1b[0m\r\n'
        );
        term.write('❯ ');

        // Fit the terminal to its container size
        try {
          setTimeout(() => {
            fitAddon.fit();
            const { cols, rows } = term;
            console.log(`Terminal dimensions: ${cols}x${rows}`);
            setTerminalSize({ cols, rows });
            onResize?.(cols, rows);
          }, 100);
        } catch (e) {
          console.error('Error fitting terminal:', e);
        }

        // Handle command input
        let currentCommand = '';
        let commandHistory: string[] = [];
        let historyIndex = -1;

        term.onData((data) => {
          if (data === '\r') {
            // Enter key
            if (currentCommand.trim()) {
              onCommand?.(currentCommand);
              runTerminalCommand?.(currentCommand, id);
              commandHistory.push(currentCommand);
              historyIndex = commandHistory.length;
            }
            currentCommand = '';
          } else if (data === '\u007F') {
            // Backspace key
            if (currentCommand.length > 0) {
              currentCommand = currentCommand.slice(0, -1);
              term.write('\b \b'); // Move back, write space, move back again
            }
          } else if (data === '\u001b[A') {
            // Up arrow
            if (historyIndex > 0) {
              historyIndex--;
              // Clear current line
              while (currentCommand.length > 0) {
                term.write('\b \b');
                currentCommand = currentCommand.slice(0, -1);
              }
              currentCommand = commandHistory[historyIndex];
              term.write(currentCommand);
            }
          } else if (data === '\u001b[B') {
            // Down arrow
            // Clear current line
            while (currentCommand.length > 0) {
              term.write('\b \b');
              currentCommand = currentCommand.slice(0, -1);
            }
            if (historyIndex < commandHistory.length - 1) {
              historyIndex++;
              currentCommand = commandHistory[historyIndex];
              term.write(currentCommand);
            } else {
              historyIndex = commandHistory.length;
            }
          } else if (data >= ' ' || data === '\t') {
            // Printable characters
            currentCommand += data;
            term.write(data);
          }

          // setCommand(currentCommand);
        });

        setTerminal(term);
        // setIsTerminalReady(true);

        // Let parents know this terminal is ready
        setTimeout(() => {
          if (ref && 'current' in ref) {
            // Trigger the update of the ref, which will notify parent components
            // that rely on ref.current.terminal
          }
        }, 100);

        return () => {
          term.dispose();
        };
      }
    }, [id, onCommand, onResize, runTerminalCommand, terminal, initialOptions]);

    // Handle terminal resize
    useEffect(() => {
      const handleResize = () => {
        if (terminal && fitAddonRef.current) {
          try {
            fitAddonRef.current.fit();
            const { cols, rows } = terminal;
            if (cols !== terminalSize.cols || rows !== terminalSize.rows) {
              setTerminalSize({ cols, rows });
              onResize?.(cols, rows);
            }
          } catch (e) {
            console.error('Error on terminal resize:', e);
          }
        }
      };

      window.addEventListener('resize', handleResize);
      return () => window.removeEventListener('resize', handleResize);
    }, [terminal, terminalSize, onResize]);

    // Focus the terminal when it becomes active
    useEffect(() => {
      if (active && terminal) {
        terminal.focus();
      }
    }, [active, terminal]);

    // Expose terminal methods via ref
    useImperativeHandle(
      ref,
      () => ({
        terminal,
        writeToTerminal: (text: string) => {
          terminal?.write(text);
        },
        clearTerminal: () => {
          terminal?.clear();
        },
        focus: () => {
          terminal?.focus();
        },
        getDimensions: () => ({
          cols: terminal?.cols || 80,
          rows: terminal?.rows || 24,
        }),
        resize: () => {
          if (terminal && fitAddonRef.current) {
            fitAddonRef.current.fit();
            const { cols, rows } = terminal;
            onResize?.(cols, rows);
          }
        },
      }),
      [terminal, onResize]
    );

    return (
      <div
        className={cn(
          'relative h-full w-full overflow-hidden',
          active ? 'block' : 'hidden',
          className
        )}
      >
        <div
          ref={terminalRef}
          className="h-full w-full bg-[#151718]"
          style={{ padding: '4px' }}
        />
      </div>
    );
  }
);

Terminal.displayName = 'Terminal';

export default Terminal;

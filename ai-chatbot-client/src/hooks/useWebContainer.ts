'use client';

import {
  useState,
  useEffect,
  type RefObject,
  useRef,
  useCallback,
} from 'react';
import { WebContainer, type WebContainerProcess } from '@webcontainer/api';
import { type TerminalRef } from '@/components/Terminal';
import { webContainerManager } from '@/lib/WebContainerManager';
import { terminalActions } from '@/stores/terminal';

// Helper to safely get shell dimensions
const getPersistentShellDimensions = (shell: any) => {
  try {
    if (!shell || !shell.isInitialized()) {
      console.warn(
        'Shell not initialized when getting dimensions, using default.'
      );
      return { cols: 80, rows: 24 };
    }
    return shell.getDimensions();
  } catch (e) {
    console.warn(
      'Could not get persistent shell dimensions, using default.',
      e
    );
    return { cols: 80, rows: 24 };
  }
};

console.log('getPersistentShellDimensions', getPersistentShellDimensions);

export const useWebContainer = (
  terminalRef?: RefObject<TerminalRef | null>
) => {
  const [webContainerInstance, setWebContainerInstance] =
    useState<WebContainer | null>(null);
  const [webContainerURL, setWebContainerURL] = useState<string | null>(null);
  const [previews, setPreviews] = useState<{ port: number; url: string }[]>([]);
  const [isInitializingWebContainer, setIsInitializingWebContainer] =
    useState(true);
  const [isInstallingDeps, setIsInstallingDeps] = useState(false);
  const [isStartingDevServer, setIsStartingDevServer] = useState(false);
  const [initializationError, setInitializationError] = useState<string | null>(
    null
  );
  const [devServerProcess, setDevServerProcess] =
    useState<WebContainerProcess | null>(null);

  const initAttemptedRef = useRef(false);
  const activeServersRef = useRef<Set<number>>(new Set());
  const persistentShell = webContainerManager.getPersistentShell();

  // Pipe process output directly to the xterm instance via the Terminal component's ref
  const pipeProcessOutputToTerminal = useCallback(
    (process: WebContainerProcess) => {
      process.output
        .pipeTo(
          new WritableStream({
            write: (data) => {
              terminalRef?.current?.writeToTerminal(data);
            },
            close: () => console.log('Output stream closed for process'),
            abort: (reason) =>
              console.error('Output stream aborted for process:', reason),
          })
        )
        .catch((error) =>
          console.error('Error piping output for terminal:', error)
        );
    },
    [terminalRef]
  );

  // Run command entered by the user or AI (delegates to PersistentShell)
  const runTerminalCommand = useCallback(
    async (command: string, terminalId: string) => {
      if (!webContainerInstance || !persistentShell.isInitialized()) {
        const errorMsg = !webContainerInstance
          ? 'Web container not available'
          : 'Shell not initialized';
        terminalRef?.current?.writeToTerminal(
          `\r\n\u001b[31m${errorMsg}\u001b[0m\r\n`
        );
        // Update store state
        terminalActions.setTerminalRunning(terminalId, false);
        terminalActions.setTerminalInteractive(terminalId, true);
        return { exitCode: 1 };
      }
      if (!command.trim()) {
        // Write a new prompt if user just hits enter
        terminalRef?.current?.writeToTerminal('\r\n❯ ');
        return { exitCode: 0 };
      }

      // PersistentShell.executeCommand now handles state updates via OSC codes/its own logic
      return persistentShell.executeCommand(command, [], terminalId);
    },
    [webContainerInstance, persistentShell, terminalRef]
  );

  // Run npm install in the 'main' (Bolt) terminal
  const runNpmInstall = useCallback(async () => {
    const terminalId = 'main';
    if (!webContainerInstance || isInstallingDeps) {
      // Removed shell check here, spawn directly
      console.warn('Skipping npm install: WC not ready or already installing.');
      return false;
    }

    setIsInstallingDeps(true);
    setInitializationError(null);
    terminalActions.setTerminalRunning(terminalId, true, 'npm install'); // Update store state
    terminalActions.setTerminalInteractive(terminalId, false);
    terminalRef?.current?.writeToTerminal(
      '\r\n\u001b[1;34m$ npm install\u001b[0m\r\n'
    ); // Echo command

    try {
      // Get dimensions from the terminal component ref if available
      // Get dimensions with correct method signature (no terminalId parameter)
      const dims = terminalRef?.current?.getDimensions() || {
        cols: 80,
        rows: 24,
      };

      const process = await webContainerInstance.spawn('npm', ['install'], {
        output: true, // Capture output
        terminal: dims,
      });

      // Pipe the process output directly to the terminal UI
      pipeProcessOutputToTerminal(process);

      const exitCode = await process.exit;

      if (exitCode !== 0) {
        const errorMsg = `Failed to install dependencies (exit code ${exitCode}). Check terminal.`;
        setInitializationError(errorMsg);
        terminalRef?.current?.writeToTerminal(
          `\r\n\u001b[31m${errorMsg}\u001b[0m\r\n`
        );
        terminalActions.setTerminalRunning(terminalId, false); // Update store state
        terminalActions.setTerminalInteractive(terminalId, true);
        terminalRef?.current?.writeToTerminal(`\r\n❯ `); // Add prompt
        return false;
      }
      terminalRef?.current?.writeToTerminal(
        `\r\n\u001b[32mDependencies installed successfully.\u001b[0m\r\n`
      );
      // Don't set interactive yet, wait for dev server
      return true;
    } catch (error: any) {
      console.error('npm install error:', error);
      const errorMsg = `Failed to install dependencies: ${error.message}`;
      setInitializationError(errorMsg);
      terminalRef?.current?.writeToTerminal(
        `\r\n\u001b[31mError running npm install: ${error.message}\u001b[0m\r\n`
      );
      terminalActions.setTerminalRunning(terminalId, false); // Update store state
      terminalActions.setTerminalInteractive(terminalId, true);
      terminalRef?.current?.writeToTerminal(`\r\n❯ `); // Add prompt
      return false;
    } finally {
      setIsInstallingDeps(false);
      // State is managed based on exit code or next step (dev server)
    }
  }, [
    webContainerInstance,
    isInstallingDeps,
    terminalRef,
    pipeProcessOutputToTerminal,
  ]);

  // Start the dev server in the 'main' (Bolt) terminal
  const startDevServer = useCallback(async () => {
    const terminalId = 'main';
    if (!webContainerInstance || isStartingDevServer || devServerProcess) {
      // Removed shell check
      console.warn(
        'Skipping dev server start: WC not ready, already starting/running.'
      );
      return;
    }

    setIsStartingDevServer(true);
    setWebContainerURL(null);
    setInitializationError(null);
    terminalActions.setTerminalRunning(terminalId, true, 'npm run dev'); // Update store state
    terminalActions.setTerminalInteractive(terminalId, false);
    terminalRef?.current?.writeToTerminal(
      `\r\n\u001b[1;34m$ npm run dev\u001b[0m\r\n`
    ); // Echo command

    try {
      // Get dimensions from the terminal component ref if available
      // Get dimensions with correct method signature (no terminalId parameter)
      const dims = terminalRef?.current?.getDimensions() || {
        cols: 80,
        rows: 24,
      };

      const process = await webContainerInstance.spawn('npm', ['run', 'dev'], {
        terminal: dims,
        output: true,
      });
      setDevServerProcess(process);

      // Pipe the process output directly to the terminal UI
      pipeProcessOutputToTerminal(process);

      let serverReadyCalled = false;
      const serverReadyListener = (port: number, url: string) => {
        if (!serverReadyCalled) {
          serverReadyCalled = true;
          console.log(`Server ready on port ${port}: ${url}`);
          activeServersRef.current.add(port);
          setWebContainerURL(url);
          setPreviews((prev) => {
            const exists = prev.some((p) => p.port === port);
            if (exists)
              return prev.map((p) => (p.port === port ? { port, url } : p));
            return [...prev, { port, url }].sort((a, b) => a.port - b.port);
          });
          if (terminalRef?.current) {
            terminalRef.current.writeToTerminal(
              `\r\n\u001b[32mDev server ready at: ${url}\u001b[0m\r\n`
            );
          }

          // Server is ready, mark as not starting and allow interaction
          setIsStartingDevServer(false);
          terminalActions.setTerminalRunning(terminalId, false); // Update store state
          terminalActions.setTerminalInteractive(terminalId, true);
          if (terminalRef?.current) {
            terminalRef.current.writeToTerminal(`\r\n❯ `); // Show prompt
          }
        }
      };

      const disposeServerReady = webContainerInstance.on(
        'server-ready',
        serverReadyListener
      );

      process.exit
        .then((exitCode) => {
          console.log(`Dev server process exited with code ${exitCode}`);
          disposeServerReady();
          setDevServerProcess(null);
          if (!serverReadyCalled) {
            // Only update state if server-ready wasn't called
            setIsStartingDevServer(false);
            terminalActions.setTerminalRunning(terminalId, false); // Update store state
            terminalActions.setTerminalInteractive(terminalId, true);
          }
          if (terminalRef?.current) {
            terminalRef.current.writeToTerminal(
              `\r\n\u001b[33mDev server process exited (code ${exitCode})\u001b[0m\r\n`
            );
          }
          if (exitCode !== 0 && exitCode !== null) {
            setInitializationError(
              `Development server exited with error code ${exitCode}. Check terminal.`
            );
          }
          if (terminalRef?.current) {
            terminalRef.current.writeToTerminal(`\r\n❯ `); // Show prompt after exit
          }
        })
        .catch((error) => {
          console.error('Error handling dev server exit:', error);
          disposeServerReady();
          setIsStartingDevServer(false);
          setDevServerProcess(null);
          terminalActions.setTerminalRunning(terminalId, false); // Update store state
          terminalActions.setTerminalInteractive(terminalId, true);
          if (terminalRef?.current) {
            terminalRef.current.writeToTerminal(`\r\n❯ `);
          }
        });
    } catch (error: any) {
      console.error('Failed to start dev server:', error);
      setIsStartingDevServer(false);
      setDevServerProcess(null);
      const errorMsg = `Error starting development server: ${error.message}`;
      setInitializationError(errorMsg);
      if (terminalRef?.current) {
        terminalRef.current.writeToTerminal(
          `\r\n\u001b[31m${errorMsg}\u001b[0m\r\n`
        );
      }
      terminalActions.setTerminalRunning(terminalId, false); // Update store state
      terminalActions.setTerminalInteractive(terminalId, true);
      if (terminalRef?.current) {
        terminalRef.current.writeToTerminal(`\r\n❯ `);
      }
    }
  }, [
    webContainerInstance,
    isStartingDevServer,
    devServerProcess,
    terminalRef,
    pipeProcessOutputToTerminal,
  ]);

  // Stop the dev server process (keep as is, but ensure state updates)
  // Initialize shell when both WebContainer and terminal ref are available
  useEffect(() => {
    const initShell = async () => {
      // Only proceed if both WebContainer and terminal ref are available
      if (!webContainerInstance || !terminalRef?.current) return;

      try {
        console.log('Terminal ref is now available - initializing shell');
        await webContainerManager.initializeShell(terminalRef.current);

        // Let the user know the terminal is ready
        if (terminalRef.current) {
          terminalRef.current.writeToTerminal(
            '\r\n\u001b[32mTerminal ready\u001b[0m\r\n'
          );
          terminalRef.current.writeToTerminal('\r\n❯ ');
        }
      } catch (error) {
        console.error('Failed to initialize shell:', error);
        if (terminalRef.current) {
          terminalRef.current.writeToTerminal(
            `\r\n\u001b[31mFailed to initialize terminal: ${error instanceof Error ? error.message : String(error)}\u001b[0m\r\n`
          );
        }
      }
    };

    initShell();
  }, [webContainerInstance, terminalRef]);

  const stopDevServer = useCallback(async () => {
    const terminalId = 'main';
    if (devServerProcess) {
      console.log('Stopping dev server process...');
      terminalRef?.current?.writeToTerminal(
        '\r\n\u001b[33mStopping dev server...\u001b[0m\r\n'
      );
      terminalActions.setTerminalInteractive(terminalId, false); // Update store state
      terminalActions.setTerminalRunning(
        terminalId,
        true,
        'Stopping server...'
      );

      try {
        await devServerProcess.kill();
        setDevServerProcess(null);
        setIsStartingDevServer(false);
        terminalRef?.current?.writeToTerminal(
          '\r\n\u001b[32mDev server stopped.\u001b[0m\r\n'
        );
        console.log('Dev server process stopped.');
      } catch (error) {
        console.error('Error stopping dev server process:', error);
        terminalRef?.current?.writeToTerminal(
          `\r\n\u001b[31mError stopping dev server: ${error instanceof Error ? error.message : String(error)}\u001b[0m\r\n`
        );
      } finally {
        setDevServerProcess(null); // Ensure it's null even on error
        setIsStartingDevServer(false);
        terminalActions.setTerminalRunning(terminalId, false); // Update store state
        terminalActions.setTerminalInteractive(terminalId, true);
        terminalRef?.current?.writeToTerminal(`\r\n❯ `);
      }
    }
  }, [devServerProcess, terminalRef]);

  // Initialize WebContainer
  useEffect(() => {
    if (initAttemptedRef.current) return;
    initAttemptedRef.current = true;

    setIsInitializingWebContainer(true);
    setInitializationError(null);

    webContainerManager
      .getWebContainer()
      .then((wc) => {
        setWebContainerInstance(wc);
        setIsInitializingWebContainer(false);
        if (terminalRef?.current) {
          terminalRef.current.writeToTerminal(
            '\r\n\u001b[32mWebContainer booted successfully\u001b[0m\r\n'
          );
        }
        // We'll initialize the shell in a separate useEffect when terminalRef is available

        const disposeError = wc.on('error', (error) => {
          console.error('WebContainer error:', error);
          const errorMessage =
            error instanceof Error ? error.message : String(error);
          setInitializationError(`WebContainer error: ${errorMessage}`);
          terminalRef?.current?.writeToTerminal(
            `\r\n\u001b[31mWebContainer Error: ${errorMessage}\u001b[0m\r\n`
          );
          if (isInitializingWebContainer) setIsInitializingWebContainer(false);
          if (isInstallingDeps) setIsInstallingDeps(false);
          if (isStartingDevServer) {
            setIsStartingDevServer(false);
            setDevServerProcess(null);
            terminalActions.setTerminalRunning('main', false);
            terminalActions.setTerminalInteractive('main', true);
          }
        });

        return () => {
          disposeError();
        };
      })
      .catch((error) => {
        console.error('WebContainer initialization failed:', error);
        const errorMsg = `Failed to initialize WebContainer: ${error instanceof Error ? error.message : String(error)}`;
        setInitializationError(errorMsg);
        setIsInitializingWebContainer(false);
        if (terminalRef?.current) {
          terminalRef.current.writeToTerminal(
            `\r\n\u001b[31mWebContainer Boot Error: ${errorMsg}\u001b[0m\r\n`
          );
        }
      });

    // Cleanup remains the same
    return () => {
      webContainerManager.tearDown().catch(console.error);
    };
  }, [terminalRef]); // Add terminalRef dependency

  return {
    webContainerInstance,
    webContainerURL,
    previews,
    isInitializingWebContainer,
    isInstallingDeps,
    isStartingDevServer,
    initializationError,
    runTerminalCommand, // Expose the unified command runner
    runNpmInstall,
    startDevServer,
    stopDevServer,
    devServerProcess,
  };
};

/**
 * WebContainerManager.ts
 *
 * This file manages a global WebContainer instance and ensures
 * only one instance exists at a time, even during React re-renders.
 */

import { WebContainer } from '@webcontainer/api';
import { WORK_DIR_NAME } from './prompt';
import { PersistentShell, createPersistentShell } from './shell';
import terminalStore, { terminalActions } from '@/stores/terminal';
import { TerminalRef } from '@/components/Terminal';

class WebContainerManager {
  private static instance: WebContainerManager | null = null;
  private webContainer: WebContainer | null = null;
  private isBooting: boolean = false;
  private bootPromise: Promise<WebContainer> | null = null;
  private persistentShell: PersistentShell = createPersistentShell();
  private shellInitialized: boolean = false;

  private constructor() {}

  public static getInstance(): WebContainerManager {
    if (!WebContainerManager.instance) {
      WebContainerManager.instance = new WebContainerManager();
    }
    return WebContainerManager.instance;
  }

  /**
   * Get the persistent shell instance
   */
  public getPersistentShell(): PersistentShell {
    return this.persistentShell;
  }

  /**
   * Initialize or restore the persistent shell with a terminal instance.
   * This should be called when the WebContainer is ready.
   */
  public async initializeShell(
    terminalRef?: TerminalRef | null
  ): Promise<void> {
    try {
      if (!this.webContainer) {
        console.log(
          'initializeShell: WebContainer not ready, booting first...'
        );
        await this.getWebContainer(); // Ensure WebContainer is booted
      }

      if (!this.webContainer) {
        throw new Error(
          'WebContainer not available after boot attempt for shell init'
        );
      }

      // Enhanced terminal reference validation
      if (terminalRef) {
        // Check if the terminal reference is valid and has necessary methods
        const hasMethods =
          typeof terminalRef.writeToTerminal === 'function' &&
          typeof terminalRef.getDimensions === 'function' &&
          typeof terminalRef.resize === 'function';

        // Check if the terminal is properly sized by getting dimensions
        let dimensions = { cols: 0, rows: 0 };
        try {
          dimensions = terminalRef.getDimensions();
        } catch (e) {
          console.warn('Failed to get terminal dimensions:', e);
        }

        console.log('WebContainerManager: Terminal ref validation:', {
          hasRef: true,
          hasMethods,
          methods: Object.keys(terminalRef),
          dimensions,
          isValidTerminal:
            hasMethods && dimensions.cols > 0 && dimensions.rows > 0,
        });

        // If dimensions are invalid, attempt to force a resize
        if (dimensions.cols === 0 || dimensions.rows === 0) {
          console.log(
            'WebContainerManager: Terminal has invalid dimensions, attempting to resize...'
          );
          try {
            terminalRef.resize();
            // Wait a moment and check again
            await new Promise((resolve) => setTimeout(resolve, 100));
            dimensions = terminalRef.getDimensions();
            console.log(
              'WebContainerManager: After resize, dimensions:',
              dimensions
            );
          } catch (e) {
            console.warn('Failed to resize terminal:', e);
          }

          // If still zero, use reasonable defaults
          if (dimensions.cols <= 0 || dimensions.rows <= 0) {
            console.log(
              'WebContainerManager: Using default dimensions 80x24 after resize failed'
            );
            dimensions = { cols: 80, rows: 24 }; // Use reasonable defaults
          }
        }

        // Write a test message to the terminal to verify it's working
        try {
          terminalRef.writeToTerminal(
            '\r\n\x1b[36mWebContainerManager: Connecting to shell...\x1b[0m\r\n'
          );
        } catch (e) {
          console.error('Failed to write test message to terminal:', e);
        }
      } else {
        console.log('WebContainerManager: No terminal reference provided');
      }

      // Check if shell needs initialization or just restoration
      if (!this.persistentShell.isInitialized()) {
        if (!terminalRef) {
          console.log(
            'WebContainerManager: No terminal ref available, deferring shell initialization...'
          );
          return; // Wait until we have a terminal ref
        }

        console.log('WebContainerManager: Initializing shell with terminal...');
        // Allow multiple attempts for initialization in case of transient issues
        let attempts = 0;
        const maxAttempts = 3;

        while (attempts < maxAttempts) {
          try {
            // Force a small delay before initialization to ensure terminal is fully ready
            await new Promise((resolve) => setTimeout(resolve, 100));

            // Get latest dimensions as they might have changed
            let dimensions = { cols: 80, rows: 24 }; // Default fallback
            try {
              dimensions = terminalRef.getDimensions();
              if (dimensions.cols <= 0 || dimensions.rows <= 0) {
                dimensions = { cols: 80, rows: 24 }; // Use reasonable defaults
              }
              console.log(
                'WebContainerManager: Using dimensions for shell init:',
                dimensions
              );
            } catch (e) {
              console.warn(
                'Failed to get dimensions for shell init, using defaults:',
                e
              );
            }

            // Write a status message
            terminalRef.writeToTerminal(
              '\r\n\x1b[36mWebContainerManager: Initializing shell...\x1b[0m\r\n'
            );

            await this.persistentShell.init(this.webContainer, terminalRef);
            this.shellInitialized = true;
            console.log('WebContainerManager: Shell initialized successfully.');
            terminalRef.writeToTerminal(
              '\r\n\x1b[32mShell initialized successfully!\x1b[0m\r\n'
            );
            break; // Success, exit the retry loop
          } catch (error) {
            attempts++;
            const errorMsg =
              error instanceof Error ? error.message : String(error);
            console.warn(
              `WebContainerManager: Shell initialization attempt ${attempts}/${maxAttempts} failed:`,
              errorMsg
            );
            terminalRef.writeToTerminal(
              `\r\n\x1b[31mShell initialization attempt ${attempts}/${maxAttempts} failed: ${errorMsg}\x1b[0m\r\n`
            );

            if (attempts >= maxAttempts) {
              terminalRef.writeToTerminal(
                '\r\n\x1b[31mFailed to initialize shell after multiple attempts\x1b[0m\r\n'
              );
              throw error; // Re-throw after max attempts
            }

            // Wait before retrying
            terminalRef.writeToTerminal(
              `\r\n\x1b[33mRetrying in 1 second...\x1b[0m\r\n`
            );
            await new Promise((resolve) => setTimeout(resolve, 1000));
          }
        }
      } else if (terminalRef) {
        console.log(
          'WebContainerManager: Restoring shell with new terminal ref...'
        );
        terminalRef.writeToTerminal(
          '\r\n\x1b[36mWebContainerManager: Restoring existing shell...\x1b[0m\r\n'
        );

        try {
          await this.persistentShell.restore(terminalRef);
          console.log('WebContainerManager: Shell restored successfully.');
          terminalRef.writeToTerminal(
            '\r\n\x1b[32mShell restored successfully!\x1b[0m\r\n'
          );
        } catch (error) {
          const errorMsg =
            error instanceof Error ? error.message : String(error);
          console.error(
            'WebContainerManager: Failed to restore shell:',
            errorMsg
          );
          terminalRef.writeToTerminal(
            `\r\n\x1b[31mFailed to restore shell: ${errorMsg}\x1b[0m\r\n`
          );
        }
      }
    } catch (error) {
      console.error('Failed to initialize/restore shell:', error);
      this.shellInitialized = false;
    }
  }

  public async getWebContainer(): Promise<WebContainer> {
    if (this.webContainer) return this.webContainer;
    if (this.isBooting && this.bootPromise) return this.bootPromise;

    this.isBooting = true;

    this.bootPromise = new Promise<WebContainer>(async (resolve, reject) => {
      try {
        const container = await WebContainer.boot({
          coep: 'credentialless',
          workdirName: WORK_DIR_NAME,
          forwardPreviewErrors: true,
        });
        this.webContainer = container;

        // Initialize shell *after* container is booted
        // The terminal will be provided later when Terminal component calls initializeShell
        await this.initializeShell();

        this.isBooting = false;
        resolve(container);
      } catch (error: any) {
        this.isBooting = false;
        this.bootPromise = null;
        console.error('WebContainerManager: Boot failed', error);
        reject(error);
      }
    });

    return this.bootPromise;
  }

  public async tearDown(): Promise<void> {
    this.persistentShell.dispose(false);
    this.shellInitialized = false;

    if (this.webContainer) {
      console.log('WebContainerManager: Tearing down instance');
      try {
        await this.webContainer.teardown(); // Use await for teardown
        console.log('WebContainerManager: Teardown complete');
      } catch (error) {
        console.error('WebContainerManager: Teardown error', error);
      }
      this.webContainer = null;
      this.bootPromise = null;
      this.isBooting = false;
      this.persistentShell = createPersistentShell(); // Recreate for next boot
    }
  }
}

// Export a singleton instance
export const webContainerManager = WebContainerManager.getInstance();

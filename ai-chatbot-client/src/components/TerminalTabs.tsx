'use client';

import React, { useRef, useEffect, useState, createRef } from 'react';
import { useWebContainer } from '@/hooks/useWebContainer';
import Terminal, { TerminalRef } from '@/components/Terminal';
import { cn } from '@/lib/utils';
import { MAX_TERMINALS } from '@/stores/terminal';
import { X, Plus, Maximize2, Minimize2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import {
  ResizablePanel,
  ResizablePanelGroup,
  ResizableHandle,
} from '@/components/ui/resizable';

interface TerminalTabsProps {
  className?: string;
  onResize?: (height: string) => void;
  height?: string;
  defaultHeight?: string;
  onClose?: () => void;
  onMinimize?: () => void;
  onMaximize?: () => void;
  mode?: 'default' | 'minimized' | 'fullscreen';
}

const TerminalTabs: React.FC<TerminalTabsProps> = ({
  className,
  onResize,
  height,
  defaultHeight = '250px',
  onClose,
  onMinimize,
  onMaximize,
  mode = 'default',
}) => {
  const [activeTab, setActiveTab] = useState('main');
  const [isResizing, setIsResizing] = useState(false);
  const [terminals, setTerminals] = useState<{ id: string; label: string }[]>([
    { id: 'main', label: 'Bolt' },
  ]);

  // Create refs for each terminal
  const terminalRefs = useRef<Record<string, React.RefObject<TerminalRef>>>({});

  // Initialize the WebContainer with the main terminal reference
  const {
    webContainerInstance,
    runNpmInstall,
    startDevServer,
    isInitializingWebContainer,
    isInstallingDeps,
    isStartingDevServer,
    webContainerURL,
    runTerminalCommand,
  } = useWebContainer(
    terminalRefs.current['main'] as React.MutableRefObject<TerminalRef | null>
  );

  // Initialize refs for each terminal tab
  useEffect(() => {
    terminals.forEach((terminal) => {
      if (!terminalRefs.current[terminal.id]) {
        terminalRefs.current[terminal.id] = createRef<TerminalRef>();
      }
    });
  }, [terminals]);

  // Handle terminal resize
  const handleTerminalResize = (
    cols: number,
    rows: number,
    id: string = 'main'
  ) => {
    console.log(`Terminal ${id} resized to ${cols}x${rows}`);
  };

  // Add a new terminal tab
  const addTerminal = () => {
    if (terminals.length >= MAX_TERMINALS) {
      console.warn(`Maximum number of terminals (${MAX_TERMINALS}) reached`);
      return;
    }

    const newId = `terminal-${Date.now()}`;
    const newTerminals = [
      ...terminals,
      { id: newId, label: `Terminal ${terminals.length}` },
    ];
    setTerminals(newTerminals);
    setActiveTab(newId);
  };

  // Close a terminal tab
  const closeTerminal = (id: string, event?: React.MouseEvent) => {
    event?.stopPropagation();
    if (terminals.length <= 1) return; // Keep at least one terminal

    const newTerminals = terminals.filter((t) => t.id !== id);
    setTerminals(newTerminals);

    // If closing the active tab, set the first available as active
    if (activeTab === id) {
      setActiveTab(newTerminals[0].id);
    }
  };

  // Handle panel resizing
  const handlePanelResize = (sizes: number[]) => {
    if (!isResizing) return;
    const containerHeight =
      document.getElementById('terminal-container')?.clientHeight || 300;
    const newHeight = `${Math.round((containerHeight * sizes[0]) / 100)}px`;
    onResize?.(newHeight);
  };

  // Clear the active terminal
  const clearTerminal = () => {
    terminalRefs.current[activeTab]?.current?.clearTerminal();
  };

  return (
    <div
      id="terminal-container"
      className={cn('border-t border-[#2a2a2c] bg-[#161618]', className)}
      style={{ height: height || defaultHeight }}
    >
      <Tabs
        value={activeTab}
        onValueChange={setActiveTab}
        className="h-full flex flex-col"
      >
        {/* Terminal tabs header */}
        <div className="flex items-center justify-between px-2 border-b border-[#2a2a2c]">
          <TabsList className="bg-transparent h-9 border-b-0">
            {terminals.map((terminal) => (
              <TabsTrigger
                key={terminal.id}
                value={terminal.id}
                className="relative data-[state=active]:bg-[#1a1a1c] data-[state=active]:shadow-none data-[state=active]:border-transparent px-3 py-1.5 h-8 text-xs"
              >
                {terminal.label}
                {terminals.length > 1 && (
                  <button
                    onClick={(e) => closeTerminal(terminal.id, e)}
                    className="ml-2 text-[#6e6e6e] hover:text-white"
                  >
                    <X size={14} />
                  </button>
                )}
              </TabsTrigger>
            ))}
            {terminals.length < MAX_TERMINALS && (
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-[#6e6e6e] hover:text-white"
                onClick={addTerminal}
              >
                <Plus size={14} />
              </Button>
            )}
          </TabsList>
          <div className="flex items-center">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-[#6e6e6e] hover:text-white"
              onClick={clearTerminal}
            >
              <X size={14} />
            </Button>
            {mode === 'default' && (
              <>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-[#6e6e6e] hover:text-white"
                  onClick={onMinimize}
                >
                  <Minimize2 size={14} />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-[#6e6e6e] hover:text-white"
                  onClick={onMaximize}
                >
                  <Maximize2 size={14} />
                </Button>
              </>
            )}
          </div>
        </div>

        {/* Terminal content */}
        <div className="flex-1 overflow-hidden">
          {terminals.map((terminal) => (
            <TabsContent
              key={terminal.id}
              value={terminal.id}
              className="h-full data-[state=active]:flex-1 data-[state=active]:flex mt-0 border-0"
            >
              <Terminal
                id={terminal.id}
                ref={terminalRefs.current[terminal.id]}
                active={activeTab === terminal.id}
                onResize={(cols, rows) =>
                  handleTerminalResize(cols, rows, terminal.id)
                }
                className="h-full"
                mode={mode}
                initialOptions={{
                  fontSize: 14,
                  theme: {
                    background: '#151718',
                    foreground: '#f8f8f8',
                  },
                }}
              />
            </TabsContent>
          ))}
        </div>
      </Tabs>
    </div>
  );
};

export default TerminalTabs;

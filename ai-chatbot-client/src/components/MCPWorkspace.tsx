import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useFrappeGetCall, useFrappeFileUpload } from 'frappe-react-sdk';
import {
  ResizablePanel,
  ResizablePanelGroup,
  ResizableHandle,
} from '@/components/ui/resizable';
import {
  CodePreviewTab,
  CodePreviewTabList,
  CodePreviewTabTrigger,
  CodePreviewTabContent,
} from '@/components/ui/code-preview-tab';
import { Button } from '@/components/ui/button';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Terminal as XTerm } from '@xterm/xterm';

// Import custom components or create stub placeholders
// Replace with your actual components or simplified versions
const ChatPanel = ({
  messages = [],
  input = '',
  setInput = () => {},
  sendMessageToAI = () => {},
  isProcessing = false,
  streamingComplete = true,
  activeFile = null,
  completedFiles = [],
  activeCommand = null,
  completedCommands = [],
  isLoading = false,
}) => (
  <div className="border-r border-gray-800 h-full bg-gray-900 text-gray-100 flex flex-col">
    <div className="p-4 border-b border-gray-800">
      <h2 className="text-lg font-semibold">MCP Terminal Chat</h2>
    </div>
    <div className="flex-1 overflow-auto p-4">
      {messages.map((message, index) => (
        <div
          key={index}
          className={`mb-4 ${message.role === 'user' ? 'text-blue-400' : 'text-gray-300'}`}
        >
          <div className="font-semibold mb-1">
            {message.role === 'user' ? 'You' : 'MCP'}
          </div>
          <div className="pl-2">{message.content}</div>
        </div>
      ))}
      {isProcessing && !streamingComplete && (
        <div className="text-gray-400 pl-2">Processing...</div>
      )}
    </div>
    <div className="p-4 border-t border-gray-800">
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message..."
          className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-gray-100"
          disabled={isProcessing}
        />
        <Button
          onClick={() => sendMessageToAI(input)}
          disabled={isProcessing || !input.trim()}
        >
          Send
        </Button>
      </div>
    </div>
  </div>
);

const EditorPanel = ({
  files = {},
  selectedFile = null,
  setSelectedFile = () => {},
  onUpdateFile = () => {},
  isStreaming = false,
  isLoading = false,
}) => {
  const filesList = Object.entries(files).map(([path, file]) => ({
    name: path,
    type: 'file',
  }));

  const selectedFileContent = selectedFile
    ? files[selectedFile]?.content || ''
    : '';

  return (
    <div className="h-full flex">
      <div className="w-48 border-r border-gray-800 overflow-auto bg-gray-900 text-gray-100">
        {filesList.map((file) => (
          <div
            key={file.name}
            className={`px-3 py-2 cursor-pointer hover:bg-gray-800 ${selectedFile === file.name ? 'bg-gray-800' : ''}`}
            onClick={() => setSelectedFile(file.name)}
          >
            {file.name.split('/').pop()}
          </div>
        ))}
      </div>
      <div className="flex-1 overflow-auto bg-gray-950 text-gray-100 p-4">
        {selectedFile ? (
          <textarea
            value={selectedFileContent}
            onChange={(e) => onUpdateFile(selectedFile, e.target.value)}
            className="w-full h-full bg-transparent outline-none font-mono resize-none"
            disabled={isStreaming}
          />
        ) : (
          <div className="flex items-center justify-center h-full text-gray-500">
            {isLoading ? 'Loading files...' : 'Select a file to edit'}
          </div>
        )}
      </div>
    </div>
  );
};

// Simple terminal tabs component
const TerminalTabs = ({
  activeTab = 0,
  setActiveTab = () => {},
  children = null,
}) => (
  <div className="h-full flex flex-col bg-gray-900 text-gray-100">
    <div className="flex border-b border-gray-800">
      <div
        className={`px-3 py-2 cursor-pointer ${activeTab === 0 ? 'bg-gray-800' : ''}`}
        onClick={() => setActiveTab(0)}
      >
        Terminal 1
      </div>
      <div
        className={`px-3 py-2 cursor-pointer ${activeTab === 1 ? 'bg-gray-800' : ''}`}
        onClick={() => setActiveTab(1)}
      >
        Terminal 2
      </div>
      <div className="flex-1"></div>
      <div className="px-3 py-2 cursor-pointer">+</div>
    </div>
    <div className="flex-1 overflow-hidden">{children}</div>
  </div>
);

// Terminal component
const Terminal = ({ onReady, onResize }) => {
  const terminalRef = useRef(null);

  useEffect(() => {
    if (!terminalRef.current) return;

    const term = new XTerm({
      cursorBlink: true,
      theme: {
        background: '#1a1a1a',
        foreground: '#f0f0f0',
      },
    });

    term.open(terminalRef.current);

    if (onReady) {
      onReady(term);
    }

    term.onResize(({ cols, rows }) => {
      if (onResize) {
        onResize(cols, rows);
      }
    });

    return () => {
      term.dispose();
    };
  }, [onReady, onResize]);

  return <div ref={terminalRef} className="h-full"></div>;
};

// Main MCP Workspace component
const MCPWorkspace = () => {
  const [activeTab, setActiveTab] = useState('Editor');
  const [showTerminal, setShowTerminal] = useState(true);
  const [terminalTab, setTerminalTab] = useState(0);
  const [selectedFile, setSelectedFile] = useState(null);
  const [files, setFiles] = useState({});
  const [isLoadingFiles, setIsLoadingFiles] = useState(false);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingFiles, setProcessingFiles] = useState(false);
  const [streamingComplete, setStreamingComplete] = useState(true);
  const [activeFile, setActiveFile] = useState(null);
  const [completedFiles, setCompletedFiles] = useState([]);

  // Terminal refs
  const terminalOneRef = useRef(null);
  const terminalTwoRef = useRef(null);

  // Load project files from Frappe backend
  const { data: fileListData, isLoading } = useFrappeGetCall(
    'erpnext_mcp_server.mcp.bridge.get_project_files'
  );

  // File upload hook for handling file content
  const { upload } = useFrappeFileUpload();

  // Load files when fileListData changes
  useEffect(() => {
    if (fileListData && fileListData.message) {
      setIsLoadingFiles(true);

      const loadFiles = async () => {
        const newFiles = {};
        for (const file of fileListData.message) {
          try {
            const response = await fetch(
              `/api/method/erpnext_mcp_server.mcp.bridge.get_file_content?path=${encodeURIComponent(file.path)}`
            );
            const data = await response.json();
            if (data.message) {
              newFiles[file.path] = {
                name: file.path,
                content: data.message,
                type: 'file',
              };
            }
          } catch (error) {
            console.error(`Failed to load file ${file.path}:`, error);
          }
        }

        setFiles(newFiles);
        if (Object.keys(newFiles).length > 0) {
          setSelectedFile(Object.keys(newFiles)[0]);
        }
        setIsLoadingFiles(false);
      };

      loadFiles();
    }
  }, [fileListData]);

  // Handle file updates
  const handleUpdateFile = async (path, content) => {
    try {
      // Update local state
      const newFiles = { ...files };
      newFiles[path] = {
        ...newFiles[path],
        content,
      };
      setFiles(newFiles);

      // Save to server
      await frappe.call({
        method: 'erpnext_mcp_server.mcp.bridge.save_file_content',
        args: {
          path,
          content,
        },
      });
    } catch (error) {
      console.error(`Failed to save file ${path}:`, error);
      frappe.throw(`Failed to save file: ${error.message}`);
    }
  };

  // Handle sending messages to MCP Server
  const sendMessageToAI = async (message) => {
    if (!message.trim() || isProcessing) return;

    // Add user message to chat
    const newMessages = [...messages, { role: 'user', content: message }];
    setMessages(newMessages);
    setInput('');

    // Begin processing
    setIsProcessing(true);
    setProcessingFiles(true);
    setStreamingComplete(false);

    try {
      // Send to MCP Server
      const response = await frappe.call({
        method: 'erpnext_mcp_server.mcp.bridge.process_mcp_command',
        args: {
          command: message,
        },
      });

      if (response.message) {
        // Add response to chat
        setMessages([
          ...newMessages,
          { role: 'assistant', content: response.message.result },
        ]);

        // If files were modified
        if (
          response.message.modified_files &&
          response.message.modified_files.length > 0
        ) {
          // Reload all files
          const modifiedFiles = response.message.modified_files;
          setActiveFile(modifiedFiles[0]);
          setCompletedFiles([]);

          // Load modified files one by one
          for (const filePath of modifiedFiles) {
            try {
              const fileResponse = await fetch(
                `/api/method/erpnext_mcp_server.mcp.bridge.get_file_content?path=${encodeURIComponent(filePath)}`
              );
              const fileData = await fileResponse.json();

              if (fileData.message) {
                // Update files state
                setFiles((prevFiles) => ({
                  ...prevFiles,
                  [filePath]: {
                    name: filePath,
                    content: fileData.message,
                    type: 'file',
                  },
                }));

                // Update active file tracking
                setActiveFile(filePath);
                setCompletedFiles((prev) => [...prev, filePath]);
                setSelectedFile(filePath);
              }
            } catch (error) {
              console.error(`Failed to load modified file ${filePath}:`, error);
            }
          }
        }
      }
    } catch (error) {
      console.error('Failed to process command:', error);
      // Add error message to chat
      setMessages([
        ...newMessages,
        { role: 'assistant', content: `Error: ${error.message}` },
      ]);
    } finally {
      setIsProcessing(false);
      setProcessingFiles(false);
      setStreamingComplete(true);
    }
  };

  // Terminal handlers
  const handleTerminalOneReady = useCallback((term) => {
    terminalOneRef.current = term;
    term.writeln('MCP Terminal 1');
    term.writeln('Type commands to interact with the MCP Server');
    term.writeln('');
    term.write('$ ');

    // Set up input handling
    let command = '';
    term.onData((data) => {
      if (data === '\r') {
        // Enter key
        term.writeln('');
        if (command.trim()) {
          // Send command to server
          frappe.call({
            method: 'erpnext_mcp_server.mcp.bridge.run_terminal_command',
            args: { command },
            callback: (r) => {
              if (r.message) {
                term.writeln(r.message);
              }
              term.write('$ ');
            },
          });
        } else {
          term.write('$ ');
        }
        command = '';
      } else if (data === '\x7f') {
        // Backspace
        if (command.length > 0) {
          command = command.slice(0, -1);
          term.write('\b \b'); // Erase the character
        }
      } else {
        command += data;
        term.write(data);
      }
    });
  }, []);

  const handleTerminalTwoReady = useCallback((term) => {
    terminalTwoRef.current = term;
    term.writeln('MCP Terminal 2');
    term.writeln('Type commands to interact with the MCP Server');
    term.writeln('');
    term.write('$ ');

    // Set up input handling (similar to terminal one)
    let command = '';
    term.onData((data) => {
      if (data === '\r') {
        // Enter key
        term.writeln('');
        if (command.trim()) {
          // Send command to server
          frappe.call({
            method: 'erpnext_mcp_server.mcp.bridge.run_terminal_command',
            args: { command },
            callback: (r) => {
              if (r.message) {
                term.writeln(r.message);
              }
              term.write('$ ');
            },
          });
        } else {
          term.write('$ ');
        }
        command = '';
      } else if (data === '\x7f') {
        // Backspace
        if (command.length > 0) {
          command = command.slice(0, -1);
          term.write('\b \b'); // Erase the character
        }
      } else {
        command += data;
        term.write(data);
      }
    });
  }, []);

  const handleTerminalResize = useCallback((cols, rows) => {
    // Send resize event to server if needed
    frappe.call({
      method: 'erpnext_mcp_server.mcp.bridge.resize_terminal',
      args: { cols, rows },
      callback: (r) => {
        console.log('Terminal resized');
      },
    });
  }, []);

  // Toggle terminal visibility
  const toggleTerminal = useCallback(() => {
    setShowTerminal((prev) => !prev);
  }, []);

  // Handle tab changes
  const handleTabChange = (tab) => {
    // Don't allow switching tabs during processing
    if (tab === 'Preview' && processingFiles && !streamingComplete) {
      return;
    }
    setActiveTab(tab);
  };

  return (
    <div className="flex h-screen bg-gray-950 text-sm relative overflow-hidden">
      <div className="flex-shrink-0 w-96 max-w-[24rem] min-w-[20rem] overflow-x-hidden">
        <ChatPanel
          messages={messages}
          input={input}
          setInput={setInput}
          sendMessageToAI={sendMessageToAI}
          isProcessing={isProcessing}
          streamingComplete={streamingComplete}
          activeFile={activeFile}
          completedFiles={completedFiles}
          isLoading={isLoadingFiles || isLoading}
        />
      </div>

      <div className="flex-1 flex flex-col min-w-0">
        <div className="h-12 border-b border-gray-800 flex items-center px-4">
          <CodePreviewTab
            value={activeTab}
            onValueChange={(value) => handleTabChange(value)}
          >
            <CodePreviewTabList>
              {['Editor', 'Preview'].map((tab) => (
                <CodePreviewTabTrigger
                  key={tab}
                  value={tab}
                  disabled={
                    tab === 'Preview' && processingFiles && !streamingComplete
                  }
                  className={cn(
                    tab === 'Preview' && processingFiles && !streamingComplete
                      ? 'cursor-not-allowed'
                      : ''
                  )}
                >
                  {tab}
                  {tab === 'Preview' && isProcessing && (
                    <Loader2 className="w-3 h-3 animate-spin ml-1.5 inline" />
                  )}
                </CodePreviewTabTrigger>
              ))}
            </CodePreviewTabList>
          </CodePreviewTab>

          <div className="ml-auto">
            <Button variant="outline" size="sm" onClick={toggleTerminal}>
              {showTerminal ? 'Hide Terminal' : 'Show Terminal'}
            </Button>
          </div>
        </div>

        <div className="flex-1 overflow-hidden">
          {activeTab === 'Editor' ? (
            <ResizablePanelGroup direction="vertical" className="h-full">
              <ResizablePanel defaultSize={75} minSize={30}>
                <EditorPanel
                  files={files}
                  selectedFile={selectedFile}
                  setSelectedFile={setSelectedFile}
                  onUpdateFile={handleUpdateFile}
                  isStreaming={processingFiles && !streamingComplete}
                  isLoading={isLoadingFiles || isLoading}
                />
              </ResizablePanel>

              {showTerminal && (
                <>
                  <ResizableHandle className="h-[1px] bg-gray-800" />
                  <ResizablePanel defaultSize={25} minSize={15}>
                    <TerminalTabs
                      activeTab={terminalTab}
                      setActiveTab={setTerminalTab}
                    >
                      {terminalTab === 0 ? (
                        <Terminal
                          onReady={handleTerminalOneReady}
                          onResize={handleTerminalResize}
                        />
                      ) : (
                        <Terminal
                          onReady={handleTerminalTwoReady}
                          onResize={handleTerminalResize}
                        />
                      )}
                    </TerminalTabs>
                  </ResizablePanel>
                </>
              )}
            </ResizablePanelGroup>
          ) : (
            <div className="h-full bg-gray-950 flex items-center justify-center text-gray-400">
              <div className="text-center">
                <p>Preview not available in this view</p>
                <p className="text-sm mt-2">
                  This is just a placeholder in the ERPNext integration
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MCPWorkspace;

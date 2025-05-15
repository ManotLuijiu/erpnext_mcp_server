'use client';

import { useState, useRef, useCallback } from 'react';
import { WebContainer } from '@webcontainer/api';
import { FileEntry } from '@/types';
import {
  OPENROUTER_API_URL,
  DEFAULT_MODEL,
  MAX_TERMINAL_EXECUTION_TIME,
} from '@/lib/constants';
import { getSystemPrompt } from '@/lib/prompt';
import he from 'he';

// Define constants for tags to ensure consistency
const BOLT_ACTION_TAG_OPEN = '<boltAction';
const BOLT_ACTION_TAG_CLOSE = '</boltAction>';
const BOLT_ARTIFACT_TAG_OPEN = '<boltArtifact';
const BOLT_ARTIFACT_TAG_CLOSE = '</boltArtifact>';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

// Define GeneratedFile interface locally since it's not exported from @/types
interface GeneratedFile {
  path: string;
  content: string;
}

// For real-time file extraction during streaming
interface FileExtractionState {
  currentFilePath: string | null;
  partialContent: string;
  completedFiles: Set<string>;
  lastScanLength: number;
  // New properties for better tag tracking
  insideAction: boolean;
  actionType: string | null;
  actionFilePath: string | null;
  currentActionStartIndex: number;
}

export const useAIChat = (
  files: Record<string, FileEntry>,
  setFiles: (files: Record<string, FileEntry>) => void,
  webContainerInstance: WebContainer | null,
  selectedFile: string | null,
  setSelectedFile: (file: string | null) => void,
  runTerminalCommand?: (
    command: string,
    terminalId: string
  ) => Promise<{ exitCode: number }>
) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [openRouterError, setOpenRouterError] = useState<string | null>(null);
  const [streamingComplete, setStreamingComplete] = useState(true);
  const [processingFiles, setProcessingFiles] = useState(false);
  const partialResponseRef = useRef<string>('');
  const fileExtractionStateRef = useRef<FileExtractionState>({
    currentFilePath: null,
    partialContent: '',
    completedFiles: new Set<string>(),
    lastScanLength: 0,
    insideAction: false,
    actionType: null,
    actionFilePath: null,
    currentActionStartIndex: -1,
  });

  // Track streaming data and usage
  const [streamingData, setStreamingData] = useState<any>(null);

  // Expose the current active file and completed files
  const [activeFile, setActiveFile] = useState<string | null>(null);
  const [completedFiles, setCompletedFiles] = useState<Set<string>>(new Set());

  // Add state to track commands being executed
  const [activeCommand, setActiveCommand] = useState<string | null>(null);
  const [completedCommands, setCompletedCommands] = useState<Set<string>>(
    new Set()
  );

  // Process streamed content in real-time to detect and write files
  const processStreamedContent = async (chunk: string) => {
    if (!webContainerInstance) return;

    try {
      // Clean chunk - unescape common escape sequences
      const cleanedChunk = chunk
        .replace(/\\"/g, '"')
        .replace(/\\n/g, '\n')
        .replace(/\\\\/g, '\\')
        .replace(/\\t/g, '\t');

      // Update the accumulated content
      partialResponseRef.current += cleanedChunk;
      const currentContent = partialResponseRef.current;

      // Process the accumulated content for file actions
      await parseContentForFiles(currentContent);
    } catch (error) {
      // Log but don't crash on errors during streaming
      console.error('Error processing streamed content:', error);
    }
  };

  // Extract attribute value from a tag
  const extractAttribute = (tag: string, name: string): string | null => {
    const regex = new RegExp(`${name}="([^"]*)"`, 'i');
    const match = tag.match(regex);
    return match ? he.decode(match[1]) : null;
  };

  // Parse and process content to extract files
  const parseContentForFiles = async (content: string) => {
    if (!webContainerInstance) return;

    const state = fileExtractionStateRef.current;

    // If we're inside an action, handle that first
    if (
      state.insideAction &&
      state.actionType === 'file' &&
      state.actionFilePath
    ) {
      const closeTagIndex = content.indexOf(
        BOLT_ACTION_TAG_CLOSE,
        state.currentActionStartIndex
      );

      if (closeTagIndex !== -1) {
        // We found the closing tag, extract the complete content
        const fileContent = content.substring(
          state.currentActionStartIndex,
          closeTagIndex
        );

        // Write the file with complete content
        await writeFileToWebContainer(webContainerInstance, {
          path: state.actionFilePath,
          content: fileContent,
        } as GeneratedFile);

        // Mark as completed and reset
        state.completedFiles.add(state.actionFilePath);
        setCompletedFiles(new Set(state.completedFiles));

        // Reset action state
        state.insideAction = false;
        state.actionType = null;
        if (state.currentFilePath === state.actionFilePath) {
          state.currentFilePath = null;
          setActiveFile(null);
        }
        state.actionFilePath = null;
        state.currentActionStartIndex = -1;

        // Continue scanning from after this file
        state.lastScanLength = closeTagIndex + BOLT_ACTION_TAG_CLOSE.length;
      } else {
        // Still waiting for closing tag, update with partial content
        const partialContent = content.substring(state.currentActionStartIndex);

        // Only update if content has changed
        if (
          partialContent.length > 0 &&
          partialContent !== state.partialContent
        ) {
          // Update file with partial content
          await writeFileToWebContainer(webContainerInstance, {
            path: state.actionFilePath,
            content: partialContent,
          } as GeneratedFile);

          state.partialContent = partialContent;
        }

        // Don't advance lastScanLength yet since we're still waiting for the closing tag
        return;
      }
    }

    // Look for file actions in the content
    let searchPos = state.lastScanLength;
    while (searchPos < content.length) {
      // Look for opening action tag
      const openTagIndex = content.indexOf(BOLT_ACTION_TAG_OPEN, searchPos);
      if (openTagIndex === -1) break; // No more tags

      // Find the end of the opening tag
      const tagEndIndex = content.indexOf('>', openTagIndex);
      if (tagEndIndex === -1) {
        // Incomplete tag, wait for more content
        break;
      }

      // Extract the full tag
      const fullTag = content.substring(openTagIndex, tagEndIndex + 1);

      // Check if it's a file action
      const actionType = extractAttribute(fullTag, 'type');
      if (actionType === 'file') {
        const filePath = extractAttribute(fullTag, 'filePath');

        if (filePath) {
          // Skip if file is already completed
          if (state.completedFiles.has(filePath)) {
            // Look for the closing tag
            const skipCloseIndex = content.indexOf(
              BOLT_ACTION_TAG_CLOSE,
              tagEndIndex
            );
            if (skipCloseIndex !== -1) {
              // Skip to after this action
              searchPos = skipCloseIndex + BOLT_ACTION_TAG_CLOSE.length;
            } else {
              // No closing tag yet, continue from after opening tag
              searchPos = tagEndIndex + 1;
            }
            continue;
          }

          // Look for closing tag
          const closeTagIndex = content.indexOf(
            BOLT_ACTION_TAG_CLOSE,
            tagEndIndex
          );

          if (closeTagIndex !== -1) {
            // Complete file found
            const fileContent = content.substring(
              tagEndIndex + 1,
              closeTagIndex
            );

            // Write the file
            await writeFileToWebContainer(webContainerInstance, {
              path: filePath,
              content: fileContent,
            } as GeneratedFile);

            // Mark as completed
            state.completedFiles.add(filePath);
            setCompletedFiles(new Set(state.completedFiles));

            // Continue searching after this file
            searchPos = closeTagIndex + BOLT_ACTION_TAG_CLOSE.length;
          } else {
            // Start of file found but no end yet

            // Set up for tracking this file
            state.insideAction = true;
            state.actionType = 'file';
            state.actionFilePath = filePath;
            state.currentActionStartIndex = tagEndIndex + 1;

            if (!state.currentFilePath) {
              // Set as current file if we don't have one yet
              state.currentFilePath = filePath;
              setActiveFile(filePath);

              // Create empty placeholder
              await createEmptyFile(webContainerInstance, filePath);

              // Switch to this file in the editor
              setSelectedFile(filePath);
            }

            // Wait for more content
            break;
          }
        } else {
          // Invalid file action without path, skip
          searchPos = tagEndIndex + 1;
        }
      } else {
        // Not a file action, skip to after this tag
        searchPos = tagEndIndex + 1;
      }
    }

    // Update scan position
    state.lastScanLength = searchPos;
  };

  // Handle special chunks like code annotations, thoughts, and progress updates
  const processSpecialContent = (data: any) => {
    if (!data) return;

    try {
      // Process different types of structured data
      if (data.type === 'progress') {
        console.log('Progress update:', data.label, data.status, data.message);
        // Store progress updates in streamingData
        setStreamingData((prev: any) => {
          const progressUpdates = prev?.progressUpdates || [];

          // Check if we already have this progress item (based on order)
          const existingIndex = progressUpdates.findIndex(
            (p: any) => p.order === data.order
          );

          if (existingIndex >= 0) {
            // Update existing progress item
            const updatedProgress = [...progressUpdates];
            updatedProgress[existingIndex] = data;
            return {
              ...prev,
              progressUpdates: updatedProgress,
            };
          } else {
            // Add new progress item
            return {
              ...prev,
              progressUpdates: [...progressUpdates, data],
            };
          }
        });
      } else if (data.type === 'usage') {
        console.log('Usage data:', data.value);
        setStreamingData((prev: any) => ({
          ...prev,
          usage: data.value,
        }));
      } else if (data.type === 'codeContext') {
        console.log('Code context files:', data.files);
        // Could show which files are being used for context
      } else if (data.type === 'chatSummary') {
        console.log('Chat summary:', data.summary);
        // Could show the summary somewhere in the UI
      }
    } catch (error) {
      console.error('Error processing special content:', error);
    }
  };

  // Helper to create an empty file
  const createEmptyFile = async (webContainer: WebContainer, path: string) => {
    try {
      // Create parent directory if needed
      const dirPath = path.substring(0, path.lastIndexOf('/'));
      if (dirPath) {
        try {
          await webContainer.fs.mkdir(dirPath, { recursive: true });
        } catch (dirError) {
          // Ignore if directory already exists
          console.log(
            `Directory already exists or could not be created: ${dirPath}`
          );
        }
      }

      // Create an empty file if it doesn't exist
      await webContainer.fs.writeFile(path, '');

      // Update app state - use direct object assignment instead of setter function
      const newFile: FileEntry = {
        name: path,
        content: '',
        type: 'file',
      };

      // Create a new files object with the new file added
      const updatedFiles = { ...files };
      updatedFiles[path] = newFile;
      setFiles(updatedFiles);
    } catch (error) {
      console.error(`Failed to create empty file ${path}:`, error);
    }
  };

  // Write a file to WebContainer and update local state
  const writeFileToWebContainer = async (
    webContainer: WebContainer,
    file: GeneratedFile
  ) => {
    try {
      // Create parent directory if needed
      const dirPath = file.path.substring(0, file.path.lastIndexOf('/'));
      if (dirPath) {
        try {
          await webContainer.fs.mkdir(dirPath, { recursive: true });
        } catch (dirError) {
          // Ignore if directory already exists
          console.log(`Directory exists or could not be created: ${dirPath}`);
        }
      }

      // Write the file
      await webContainer.fs.writeFile(file.path, file.content);

      // Update app state - use direct object assignment instead of setter function
      const newFile: FileEntry = {
        name: file.path,
        content: file.content,
        type: 'file',
      };

      // Create a new files object with the new file added
      const updatedFiles = { ...files };
      updatedFiles[file.path] = newFile;
      setFiles(updatedFiles);
    } catch (error) {
      console.error(`Failed to write file ${file.path}:`, error);
    }
  };

  // Process shell commands found in streamed content
  const processShellCommands = async (content: string) => {
    if (!webContainerInstance || !runTerminalCommand) return;

    const shellCmdRegex =
      /<boltAction\s+type="shell">([\s\S]*?)<\/boltAction>/g;
    let shellMatch;
    let commandsFound = false;
    let commands: string[] = [];

    // First, extract all commands
    while ((shellMatch = shellCmdRegex.exec(content)) !== null) {
      commandsFound = true;
      const command = he.decode(shellMatch[1].trim());

      if (command) {
        commands.push(command);
      }
    }

    if (commands.length === 0) return false;

    // Filter out npm run dev commands - we don't want to run these as they cause conflicts
    const filteredCommands = commands.filter((cmd) => {
      const isDevServer =
        cmd.trim() === 'npm run dev' ||
        cmd.trim() === 'npm start' ||
        cmd.includes('next dev');

      // If it's a dev server command, mark it as completed without running it
      if (isDevServer) {
        setCompletedCommands((prev) => {
          const newSet = new Set(prev);
          newSet.add(cmd);
          return newSet;
        });
      }

      // Keep only non-dev-server commands
      return !isDevServer;
    });

    if (filteredCommands.length === 0) {
      return true;
    }

    try {
      // Make sure commands run after all files are processed
      // Wait a moment to ensure file processing is complete
      await new Promise((resolve) => setTimeout(resolve, 500));

      // Clear any previous active/completed commands when starting a new batch
      setCompletedCommands(new Set());

      // Run each command in sequence
      for (const command of filteredCommands) {
        console.log(`Running shell command: ${command}`);

        // Skip empty commands
        if (!command.trim()) continue;

        // Set active command to show in UI
        setActiveCommand(command);

        // Execute the command visibly in the terminal
        // First show a clear visual separator and command echo in the terminal
        await runTerminalCommand(
          `echo \r\n\u001b[1;34m▶ Running command: ${command}\u001b[0m\r\n\u001b[1;32mdev server will restart automatically\u001b[0m`,
          'bolt-setup'
        );
        await new Promise((resolve) => setTimeout(resolve, 300));

        // Execute the actual command now with a timeout
        const commandPromise = runTerminalCommand(command, 'bolt-setup');

        try {
          // Create a timeout promise
          const timeoutPromise = new Promise((_, reject) => {
            setTimeout(() => {
              reject(
                new Error(
                  `Command timed out after ${MAX_TERMINAL_EXECUTION_TIME / 1000}s: ${command}`
                )
              );
            }, MAX_TERMINAL_EXECUTION_TIME);
          });

          // Race between command execution and timeout
          await Promise.race([commandPromise, timeoutPromise]);
        } catch (timeoutError) {
          console.error('Command execution timed out:', timeoutError);
          // Show timeout error in terminal
          await runTerminalCommand(
            `echo "\r\n\u001b[1;31m✖ Command timed out: ${command}\u001b[0m"`,
            'bolt-setup'
          );
        }

        // Mark command as completed regardless of outcome
        setActiveCommand(null);
        setCompletedCommands((prev) => {
          const newSet = new Set(prev);
          newSet.add(command);
          return newSet;
        });

        // Small delay between commands
        await new Promise((resolve) => setTimeout(resolve, 500));
      }
    } catch (error) {
      console.error('Error executing shell commands:', error);
      // Reset states on error
      setActiveCommand(null);
    }

    return commandsFound;
  };

  // Parse SSE data format
  const parseSSEData = (data: string) => {
    if (data === '[DONE]') return null;

    try {
      return JSON.parse(data);
    } catch (e) {
      // If it's not JSON, return the raw data
      return data;
    }
  };

  // Process the SSE stream from the server
  const processSSEStream = async (
    reader: ReadableStreamDefaultReader<Uint8Array>,
    decoder: TextDecoder
  ) => {
    let assistantContent = '';
    let buffer = '';
    let inProgressContent = '';

    try {
      // Initialize file extraction state if not already done
      if (!fileExtractionStateRef.current) {
        fileExtractionStateRef.current = {
          currentFilePath: null,
          partialContent: '',
          completedFiles: new Set<string>(),
          lastScanLength: 0,
          insideAction: false,
          actionType: null,
          actionFilePath: null,
          currentActionStartIndex: -1,
        };
      }

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          break;
        }

        // Decode this chunk
        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;

        // Process lines
        let newlineIndex;
        while ((newlineIndex = buffer.indexOf('\n')) !== -1) {
          const line = buffer.slice(0, newlineIndex);
          buffer = buffer.slice(newlineIndex + 1);

          if (!line || line.trim() === '') continue;

          // Handle both SSE and non-SSE formatted lines
          if (line.startsWith('data: ')) {
            // Standard SSE format
            const data = line.slice(6);

            if (data === '[DONE]') {
              continue;
            }

            const parsed = parseSSEData(data);

            if (parsed) {
              if (typeof parsed === 'string') {
                // Plain text content
                inProgressContent += parsed;
                assistantContent += parsed;
                await processStreamedContent(parsed);
              } else if (parsed.type === 'token') {
                // Token from AI
                const token = parsed.value || '';
                inProgressContent += token;
                assistantContent += token;
                await processStreamedContent(token);
              } else {
                // Special data like progress updates, usage, etc.
                processSpecialContent(parsed);
              }
            }
          } else if (line.startsWith('2:') || line.startsWith('8:')) {
            // Progress or annotation data
            try {
              const dataContent = line.slice(2);
              const parsedData = JSON.parse(dataContent);
              if (Array.isArray(parsedData) && parsedData.length > 0) {
                processSpecialContent(parsedData[0]);
              }
            } catch (e) {
              console.error('Error parsing annotation data:', e, line);
            }
          } else if (line.startsWith('0:')) {
            // Text content format from the new API
            let content = line.slice(2);

            // Handle different possible formats of content
            // If it starts with a quote but doesn't end with one, it's likely a partial string
            if (content.startsWith('"') && !content.endsWith('"')) {
              content = content.substring(1);
            }
            // If it's a complete quoted string, remove the quotes
            else if (
              content.startsWith('"') &&
              content.endsWith('"') &&
              content.length > 1
            ) {
              content = content.substring(1, content.length - 1);
            }

            // Unescape any escaped characters like \"
            content = content
              .replace(/\\"/g, '"')
              .replace(/\\n/g, '\n')
              .replace(/\\\\/g, '\\');

            inProgressContent += content;
            assistantContent += content;
            await processStreamedContent(content);
          } else if (
            line.startsWith('f:') ||
            line.startsWith('e:') ||
            line.startsWith('d:')
          ) {
            // Metadata about the request - can be used for logging
          } else if (line.trim() && !line.startsWith(':')) {
            // Any other non-empty, non-comment line

            // Try to extract any usable content even from unrecognized format
            const contentMatch = line.match(/[0-9]+:"(.*)"/);
            if (contentMatch && contentMatch[1]) {
              const extractedContent = contentMatch[1];
              inProgressContent += extractedContent;
              assistantContent += extractedContent;
              await processStreamedContent(extractedContent);
            } else {
              // If we can't parse it in any known format, add it as-is
              inProgressContent += line;
              assistantContent += line;
              await processStreamedContent(line);
            }
          }
        }

        // Process any remaining content in the buffer if it's substantial
        if (buffer.length > 0 && !buffer.trim().startsWith(':')) {
          inProgressContent += buffer;
          assistantContent += buffer;
          await processStreamedContent(buffer);
        }

        // Update the assistant's message
        setMessages((prev) => {
          const updatedMessages = [...prev];
          if (
            updatedMessages.length > 0 &&
            updatedMessages[updatedMessages.length - 1].role === 'assistant'
          ) {
            updatedMessages[updatedMessages.length - 1].content =
              assistantContent;
          }
          return updatedMessages;
        });
      }

      // Process any final content in the buffer
      if (buffer.length > 0) {
        assistantContent += buffer;
        await processStreamedContent(buffer);
      }

      return assistantContent;
    } catch (error) {
      console.error('Error processing SSE stream:', error);
      throw error;
    }
  };

  // Main function to send message to AI
  const sendMessageToAI = async (message: string) => {
    if (!message.trim() || !webContainerInstance) return;

    try {
      // Reset error state
      setOpenRouterError(null);

      // Add user message to chat history
      const userMessage = { role: 'user' as const, content: message };
      setMessages((prev) => [...prev, userMessage]);

      // Reset file tracking refs
      fileExtractionStateRef.current = {
        currentFilePath: null,
        partialContent: '',
        completedFiles: new Set<string>(),
        lastScanLength: 0,
        insideAction: false,
        actionType: null,
        actionFilePath: null,
        currentActionStartIndex: -1,
      };
      partialResponseRef.current = '';
      setStreamingData(null);

      // Start streaming indicators
      setProcessingFiles(true);
      setStreamingComplete(false);
      setActiveFile(null);
      setCompletedFiles(new Set());
      setActiveCommand(null);
      setCompletedCommands(new Set());

      // Add empty assistant message immediately to enable real-time updates
      setMessages((prev) => [...prev, { role: 'assistant', content: '' }]);

      // Prepare messages for API with proper format
      const thread = [...messages, userMessage];

      // Prepare request payload
      const requestPayload = {
        messages: thread,
        files,
        promptId: undefined, // You can add this if needed
        contextOptimization: true, // Enable context optimization
        supabase: undefined, // You can add Supabase connection details if needed
      };

      // Start the fetch to our API endpoint
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestPayload),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      if (!response.body) {
        throw new Error('Response body is null');
      }

      // Process the stream
      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      const finalContent = await processSSEStream(reader, decoder);

      // Finalize and properly close any remaining files
      await finalizeFileProcessing(finalContent || '');

      // Add a small delay to ensure all file updates are visibly complete
      await new Promise((resolve) => setTimeout(resolve, 500));

      // Process any shell commands embedded in the response
      await processShellCommands(finalContent || '');

      // Note: We no longer automatically restart npm run dev after command execution.
      // This prevents multiple dev servers from running simultaneously.

      // Reset input
      setInput('');
    } catch (error: any) {
      console.error('Error in AI API call:', error);
      setOpenRouterError(`API error: ${error.message}`);
    } finally {
      // Always mark streaming as complete
      setStreamingComplete(true);
      setProcessingFiles(false);
    }
  };

  // Helper function to finalize file processing and ensure all files are properly closed
  const finalizeFileProcessing = async (finalContent: string) => {
    if (!webContainerInstance) return;

    // Try one more thorough scan with the complete content
    await parseContentForFiles(finalContent);

    const state = fileExtractionStateRef.current;

    // If we still have an active file that wasn't completed, try to properly close it
    if (
      state.insideAction &&
      state.actionType === 'file' &&
      state.actionFilePath
    ) {
      try {
        // If we have partial content, make sure it's written
        if (state.partialContent && state.partialContent.length > 0) {
          await writeFileToWebContainer(webContainerInstance, {
            path: state.actionFilePath,
            content: state.partialContent,
          } as GeneratedFile);
        }

        // Reset action state
        state.insideAction = false;
        state.actionType = null;
        state.actionFilePath = null;
        state.currentActionStartIndex = -1;
        state.currentFilePath = null;
        setActiveFile(null);
      } catch (error) {
        console.error(`Error finalizing file ${state.actionFilePath}:`, error);
      }
    }

    // Do one last exhaustive search for any complete file actions that might have been missed
    try {
      // Use a regex that's more forgiving about matching content across multiple lines
      const fileRegex = new RegExp(
        `${BOLT_ACTION_TAG_OPEN}\\s+type="file"\\s+filePath="([^"]+)">((?:[\\s\\S](?!${BOLT_ACTION_TAG_CLOSE}))*?[\\s\\S]?)${BOLT_ACTION_TAG_CLOSE}`,
        'g'
      );
      let match;

      while ((match = fileRegex.exec(finalContent)) !== null) {
        const filePath = he.decode(match[1]);
        const fileContent = match[2];

        // Skip if already processed
        if (state.completedFiles.has(filePath)) {
          continue;
        }

        // Write the file
        await writeFileToWebContainer(webContainerInstance, {
          path: filePath,
          content: fileContent,
        } as GeneratedFile);

        // Mark as completed
        state.completedFiles.add(filePath);
        setCompletedFiles(new Set(state.completedFiles));
      }
    } catch (error) {
      console.error('Error in final file search:', error);
    }
  };

  // Expose callback to stop streaming if needed
  const stopStreaming = useCallback(() => {
    // This would ideally abort the fetch request
    // If you implement an AbortController, you can abort the request here
  }, []);

  return {
    messages,
    input,
    setInput,
    openRouterError,
    sendMessageToAI,
    stopStreaming,
    processingFiles,
    streamingComplete,
    activeFile,
    completedFiles,
    activeCommand,
    completedCommands,
    streamingData,
  };
};

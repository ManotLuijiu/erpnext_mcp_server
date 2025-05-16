'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { type FileEntry } from '@/types'; // Assuming FileEntry is in @/types
import {
  ChevronRight,
  FileIcon,
  // Loader2,
  LoaderCircle,
  Pencil,
  // Save,
} from 'lucide-react';
import Editor, { type OnMount } from '@monaco-editor/react';
import { Button } from '@/components/ui/button';
import { BinaryFile } from '@/components/BinaryFile'; // Import the new component
import { Badge } from './ui/badge';
import { ShimmerText } from './ui/text-shimmer';
import { cn } from '@/lib/utils';

interface EditorProps {
  selectedFile: string | null;
  files: Record<string, FileEntry>;
  onUpdateFile: (path: string, content: string) => void;
  isStreaming?: boolean;
  loadFileContent?: (path: string) => Promise<string>;
}

// Get language based on file extension for Monaco
const getLanguage = (filename: string | null): string => {
  if (!filename) return 'plaintext'; // Default to plaintext if no filename

  const extension = filename.split('.').pop()?.toLowerCase();

  switch (extension) {
    case 'js':
    case 'jsx':
      return 'javascript';
    case 'ts':
    case 'tsx':
      return 'typescript';
    case 'html':
    case 'htm':
      return 'html';
    case 'css':
      return 'css';
    case 'json':
      return 'json';
    case 'md':
    case 'mdx': // Add mdx for markdown variants
      return 'markdown';
    case 'vue': // Added Vue support
      return 'vue';
    case 'svelte': // Added Svelte (fallback to html)
      return 'html';
    case 'astro': // Added Astro (fallback to html)
      return 'html';
    case 'py':
      return 'python';
    case 'sh':
    case 'bash':
      return 'shell';
    case 'java':
      return 'java';
    case 'go':
      return 'go';
    case 'rb':
      return 'ruby';
    case 'php':
      return 'php';
    case 'scss':
      return 'scss';
    case 'sass':
      return 'sass';
    case 'less':
      return 'less';
    case 'yaml':
    case 'yml':
      return 'yaml';
    case 'xml':
      return 'xml';
    case 'sql':
      return 'sql';
    case 'graphql':
    case 'gql':
      return 'graphql';
    // Add more language mappings as needed
    default:
      return 'plaintext'; // Default for unrecognized extensions
  }
};

export function CodeEditor({
  selectedFile,
  files,
  onUpdateFile,
  isStreaming = false,
  loadFileContent,
}: EditorProps) {
  const [fileContent, setFileContent] = useState<string>('');
  const [unsavedContent, setUnsavedContent] = useState<string>('');
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isBinaryOrUnreadable, setIsBinaryOrUnreadable] =
    useState<boolean>(false); // New state for binary check

  // Store the selectedFile in a ref to prevent useEffect loops
  const selectedFileRef = useRef<string | null>(null);
  // Track if content has been loaded for the current file
  const contentLoadedRef = useRef<boolean>(false);
  // Track the last streamed content length to show incremental updates
  const lastContentLengthRef = useRef<number>(0);

  // Reference to the editor instance
  const editorRef = useRef<any>(null);
  // Add a ref to track error suppression during streaming
  const errorSuppressedRef = useRef<boolean>(false);

  // When Monaco editor is mounted, store reference
  const handleEditorDidMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;

    // Set TypeScript compiler options
    monaco.languages.typescript.typescriptDefaults.setCompilerOptions({
      jsx: monaco.languages.typescript.JsxEmit.React,
      jsxImportSource: 'react',
      allowNonTsExtensions: true, // Useful for Vue/Svelte/Astro
      esModuleInterop: true,
    });

    monaco.languages.typescript.typescriptDefaults.setDiagnosticsOptions({
      noSemanticValidation: true,
      noSyntaxValidation: true,
      diagnosticCodesToIgnore: [7027],
    });

    // Set editor background and colors to match the app theme
    monaco.editor.defineTheme('darkerTheme', {
      base: 'vs-dark' as const,
      inherit: true,
      rules: [],
      colors: {
        'editor.background': '#161618',
        'editor.foreground': '#f3f6f6',
        'editorLineNumber.foreground': '#969798',
        'editorLineNumber.activeForeground': '#f3f6f6',
        'editorIndentGuide.background': '#2a2a2c',
        'editor.selectionBackground': '#2a2a2c',
        'editor.inactiveSelectionBackground': '#212122',
        'editor.lineHighlightBackground': '#1c1c1e',
      },
    });

    monaco.editor.setTheme('darkerTheme');

    // Add keyboard shortcut for saving
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
      handleSave();
    });
  };

  // Handle content changes
  const handleChange = useCallback(
    (value: string | undefined) => {
      // Only allow changes if not streaming and not binary
      if (
        !isStreaming &&
        !isBinaryOrUnreadable &&
        selectedFile &&
        value !== undefined
      ) {
        setUnsavedContent(value);
        setHasUnsavedChanges(value !== fileContent);
      }
    },
    [isStreaming, selectedFile, fileContent, isBinaryOrUnreadable]
  );

  // Save changes when explicitly requested
  const handleSave = useCallback(() => {
    if (selectedFile && hasUnsavedChanges && !isBinaryOrUnreadable) {
      setIsSaving(true);
      onUpdateFile(selectedFile, unsavedContent);
      setFileContent(unsavedContent);
      setHasUnsavedChanges(false);
      setTimeout(() => setIsSaving(false), 300); // Show saving indicator briefly
    }
  }, [
    selectedFile,
    unsavedContent,
    hasUnsavedChanges,
    onUpdateFile,
    isBinaryOrUnreadable,
  ]);

  // Add polling refresh during streaming to show real-time updates
  useEffect(() => {
    if (!isStreaming || !selectedFile) return;

    // When streaming begins for a new file, reset the content length tracker
    if (selectedFile !== selectedFileRef.current) {
      lastContentLengthRef.current = 0;
      // Suppress errors during streaming of new files
      errorSuppressedRef.current = true;
    }

    // Set up interval to refresh file content during streaming
    const refreshInterval = setInterval(async () => {
      if (!selectedFile) return;

      try {
        let newContent: string | null = null;

        // First try from files state (fastest)
        if (
          files[selectedFile] &&
          typeof files[selectedFile].content === 'string'
        ) {
          newContent = files[selectedFile].content as string;
        }
        // Then try using loadFileContent
        else if (loadFileContent) {
          newContent = await loadFileContent(selectedFile);
        }

        // Only update if we got content and it's different from what we have
        if (newContent !== null) {
          // Check if the content has actually grown since last update
          if (newContent.length > lastContentLengthRef.current) {
            // Update the last content length tracker
            lastContentLengthRef.current = newContent.length;

            // Check if the new content is binary/unreadable
            const isUnreadable = newContent.includes('\0'); // Simple null byte check
            setIsBinaryOrUnreadable(isUnreadable);

            // Update the editor content only if it's readable
            if (!isUnreadable) {
              setFileContent(newContent);
              setUnsavedContent(newContent); // Keep unsaved in sync during streaming

              // Auto-scroll to the bottom of the editor after content update
              if (editorRef.current) {
                setTimeout(() => {
                  if (editorRef.current) {
                    const lineCount = editorRef.current
                      .getModel()
                      .getLineCount();
                    editorRef.current.revealLine(lineCount, 1); // Scroll to last line with smooth animation
                  }
                }, 50); // Small delay to ensure content is rendered before scrolling
              }
            } else {
              // Clear content if it becomes unreadable
              setFileContent('');
              setUnsavedContent('');
            }
          }
        }
      } catch (err) {
        console.error('Error refreshing streaming content:', err);
        // Don't set any errors during streaming to prevent flickering
      }
    }, 150); // Slightly slower refresh rate to reduce flickering (150ms instead of 100ms)

    return () => {
      clearInterval(refreshInterval);
      // Reset error suppression when streaming ends
      setTimeout(() => {
        errorSuppressedRef.current = false;
      }, 500);
    };
  }, [isStreaming, selectedFile, files, loadFileContent, isBinaryOrUnreadable]);

  // Reset state when selected file changes
  useEffect(() => {
    if (selectedFile !== selectedFileRef.current) {
      // Reset state for new file
      selectedFileRef.current = selectedFile;
      contentLoadedRef.current = false;
      lastContentLengthRef.current = 0; // Reset the content length tracker for new file
      setFileContent('');
      setUnsavedContent('');
      setHasUnsavedChanges(false);
      setError(null);
      setIsBinaryOrUnreadable(false); // Reset binary flag

      // Clear error if streaming (since file might not exist yet)
      if (isStreaming) {
        errorSuppressedRef.current = true;
      }
    }
  }, [selectedFile, isStreaming]);

  // Load file content only when needed and not already loaded
  useEffect(() => {
    const loadContent = async () => {
      // Skip if no file selected, already loading, or content already loaded
      // During streaming, allow refreshing content (handled by the streaming useEffect)
      if (
        !selectedFile ||
        isLoading ||
        (contentLoadedRef.current && !isStreaming)
      )
        return;

      setIsLoading(true);
      setIsBinaryOrUnreadable(false); // Reset binary flag before loading

      try {
        let content: string = '';

        // First check if the file has content already in the files state
        if (
          files[selectedFile] &&
          typeof files[selectedFile].content === 'string' &&
          files[selectedFile].content !== ''
        ) {
          content = files[selectedFile].content as string;
        }
        // Next try to use the loadFileContent function if available
        else if (loadFileContent) {
          try {
            content = await loadFileContent(selectedFile);
          } catch (err) {
            console.error(`Error using loadFileContent: ${selectedFile}`, err);
            throw err;
          }
        }
        // Fallback to direct WebContainer access if no loading function is provided
        else if (typeof window !== 'undefined' && window.webContainerInstance) {
          try {
            content = await window.webContainerInstance.fs.readFile(
              selectedFile,
              'utf-8'
            );
          } catch (err) {
            console.error(
              `Error reading file from WebContainer: ${selectedFile}`,
              err
            );
            // Check if error indicates it's a directory
            if (err instanceof Error && err.message.includes('EISDIR')) {
              throw new Error('Selected item is a directory, not a file.');
            }
            // Assume other errors might mean it's unreadable/binary
            setIsBinaryOrUnreadable(true);
            throw err; // Re-throw after setting flag
          }
        } else {
          throw new Error('No method available to load file content');
        }

        // Skip update if file selection has changed during async operation
        if (selectedFile !== selectedFileRef.current) return;

        // --- Binary Check ---
        // Check for null bytes as a simple heuristic for binary/unreadable content
        const isUnreadable = content.includes('\0');
        setIsBinaryOrUnreadable(isUnreadable);
        // --- End Binary Check ---

        // Mark content as loaded to prevent loops
        contentLoadedRef.current = true;

        // Update state with loaded content ONLY if it's readable
        if (!isUnreadable) {
          setFileContent(content);
          setUnsavedContent(content);
        } else {
          // Clear content if unreadable
          setFileContent('');
          setUnsavedContent('');
        }
      } catch (err) {
        console.error('Failed to load file:', err);

        // Only show errors if not streaming or suppressing errors
        if (!isStreaming && !errorSuppressedRef.current) {
          const errorMessage = err instanceof Error ? err.message : String(err);
          // Don't show error if it's just the binary screen being displayed
          if (!isBinaryOrUnreadable) {
            // Don't show ENOENT errors during streaming as AI might be creating these files
            if (!(errorMessage.includes('ENOENT') && isStreaming)) {
              setError(`Error loading file: ${errorMessage}`);
            }
          }
        }
      } finally {
        setIsLoading(false);

        // Turn off error suppression after a delay
        if (errorSuppressedRef.current) {
          setTimeout(() => {
            errorSuppressedRef.current = false;
          }, 500);
        }
      }
    };

    loadContent();
  }, [
    selectedFile,
    files,
    loadFileContent,
    isLoading,
    isStreaming,
    isBinaryOrUnreadable,
  ]);

  // --- Render Logic ---

  if (!selectedFile) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 bg-[#101012]">
        <div className="w-16 h-16 rounded-full bg-[#161618] flex items-center justify-center mb-6 shadow-lg border border-[#313133]">
          <FileIcon className="h-8 w-8 text-[#969798]" />
        </div>
        <h3 className="text-xl font-semibold mb-3 text-[#f3f6f6]">
          No file selected
        </h3>
        <p className="text-sm text-[#969798] text-center max-w-md">
          Select a file from the sidebar to start editing.
        </p>
        <div className="rounded-md bg-[#161618] border border-[#313133] px-5 py-3 mt-8 max-w-sm shadow-md">
          <p className="text-xs text-[#969798] text-center">
            Tip: Use{' '}
            <kbd className="px-2 py-1 mx-1 bg-[#212122] border border-[#313133] rounded text-[12px] font-mono shadow-sm">
              {typeof navigator !== 'undefined' &&
              navigator.userAgent.includes('Mac')
                ? 'Cmd'
                : 'Ctrl'}{' '}
              + S
            </kbd>{' '}
            to save your file.
          </p>
        </div>
      </div>
    );
  }

  // Status Indicators (for error) must be rendered inside the returned JSX
  return (
    <div className="relative h-full w-full bg-[#101012] flex flex-col">
      {/* Header */}
      <div className="flex justify-between items-center px-4 py-2 bg-[#161618] border-b border-[#313133] flex-shrink-0">
        <div className="text-sm text-[#f3f6f6] truncate flex items-center">
          {selectedFile.split('/').map((part, index, array) => (
            <>
              <pre>{array}</pre>
              <span key={index} className="flex items-center">
                {index > 0 &&
                  (selectedFile.startsWith('/') ? index > 1 : true) && (
                    <ChevronRight className="h-3 w-3 mx-0.5 text-[#969798]" />
                  )}
                {part}
              </span>
            </>
          ))}
        </div>
        {isStreaming && !isBinaryOrUnreadable && (
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className="flex items-center gap-2 py-1">
              <Pencil className="w-3.5 h-3.5 animate-pulse text-[#969798]" />
              <ShimmerText className="text-xs font-medium">Editing</ShimmerText>
            </Badge>
          </div>
        )}
        <Button
          size="sm"
          onClick={handleSave}
          // Disable save if binary, streaming, saving, or no changes
          disabled={
            isBinaryOrUnreadable ||
            !hasUnsavedChanges ||
            isStreaming ||
            isSaving
          }
          className={cn(
            'relative justify-center cursor-pointer inline-flex items-center text-center',
            'ease-out duration-200 rounded-md outline-none transition-all outline-0',
            'focus-visible:outline-4 focus-visible:outline-offset-1',
            '!h-[26px] !px-2.5 !py-1 !text-xs',
            'bg-[#161618]',
            'hover:bg-[#212122]',
            'text-[#f3f6f6]',
            '!border !border-[#313133]',
            'hover:!border-[#414143]',
            isSaving && ['!pl-7', '!bg-[#212122]', '!border-[#414143]']
          )}
        >
          <div className="flex items-center gap-1.5">
            <div
              className={cn(
                'absolute left-2.5 transition-all duration-200 ease-in-out opacity-0 -translate-x-2',
                isSaving && 'opacity-100 translate-x-0'
              )}
            >
              <LoaderCircle
                className="animate-spin text-[#969798]"
                size={12}
                strokeWidth={2}
                aria-hidden="true"
              />
            </div>
            <span>Save</span>
          </div>
        </Button>
      </div>

      {/* Editor Area or Binary Screen */}
      <div className="flex-1 relative min-h-0">
        {' '}
        {/* Added min-h-0 */}
        {isBinaryOrUnreadable ? (
          <BinaryFile />
        ) : (
          <Editor
            // Use a dynamic key to force re-render on file change AND binary status change
            key={`${selectedFile}-${isBinaryOrUnreadable}`}
            height="100%"
            language={getLanguage(selectedFile)}
            // Show current file content during streaming, otherwise show potentially unsaved content
            value={isStreaming ? fileContent : unsavedContent}
            onChange={handleChange}
            onMount={handleEditorDidMount}
            theme="darkerTheme" // Use our new darker theme
            options={{
              readOnly: isStreaming || isBinaryOrUnreadable || isLoading, // Editor is read-only if loading, streaming or binary
              // --- Standard Monaco options ---
              roundedSelection: false,
              lineNumbersMinChars: 3,
              minimap: { enabled: false },
              scrollBeyondLastLine: false,
              overviewRulerBorder: false,
              folding: true,
              lineNumbers: 'on',
              scrollbar: {
                vertical: 'visible',
                horizontal: 'visible',
                verticalScrollbarSize: 8,
                horizontalScrollbarSize: 8,
                useShadows: false,
              },
              glyphMargin: false,
              padding: { top: 16, bottom: 16 },
              wordWrap: 'on',
              tabSize: 2,
              fontSize: 14,
              automaticLayout: true, // Important for resizing
              lineDecorationsWidth: 0,
              renderLineHighlight: 'gutter', // Highlight active line in gutter
              // --- End Standard Monaco options ---
            }}
            beforeMount={(monaco) => {
              try {
                console.log('monaco', monaco);
                // Define the custom theme (already defined in onMount)
                // No need to redefine the theme here
              } catch (e) {
                console.warn(
                  'Theme might already be defined. Falling back to default theme.',
                  e
                );
              }
            }}
          />
        )}
        {/* Status Indicators */}
        {error &&
          !isBinaryOrUnreadable &&
          !errorSuppressedRef.current &&
          !isStreaming && (
            <div className="absolute top-12 left-3 bg-red-500/80 text-white px-3 py-1.5 rounded-md z-10 shadow-md">
              <span className="text-xs font-medium">{error}</span>
            </div>
          )}
      </div>
    </div>
  );
}

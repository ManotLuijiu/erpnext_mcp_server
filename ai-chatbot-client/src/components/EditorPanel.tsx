'use client';

import { useState, useEffect, useCallback } from 'react';
import { FileTree } from '@/components/FileTree';
import { CodeEditor } from '@/components/Editor';
import { type FileEntry } from '@/types';
import {
  ResizablePanelGroup,
  ResizablePanel,
  ResizableHandle,
} from '@/components/ui/resizable';
// import { cn } from '@/lib/utils';
import { Skeleton } from './ui/skeleton';
import { motion, AnimatePresence } from 'framer-motion';
import { Icons } from './ui/icons';
import { ShimmerLine } from '@/components/ui/shimmer-line';
import { ShimmerText } from '@/components/ui/text-shimmer';
import { FileTreeShimmer } from '@/components/ui/file-tree-shimmer';

interface EditorPanelProps {
  files: Record<string, FileEntry>;
  selectedFile: string | null;
  setSelectedFile: (file: string | null) => void;
  onUpdateFile: (path: string, content: string) => void;
  loadFileContent?: (path: string) => Promise<string>;
  isStreaming?: boolean;
  isLoadingGitHubFiles?: boolean;
  rateLimit?: { resetTime?: Date };
}

export function EditorPanel({
  files,
  selectedFile,
  setSelectedFile,
  onUpdateFile,
  loadFileContent,
  isStreaming = false,
  isLoadingGitHubFiles = false,
}: EditorPanelProps) {
  // Use local state to prevent the file selection from being lost
  const [stableFile, setStableFile] = useState<string | null>(selectedFile);

  // When the parent component updates selectedFile, update our stable state
  useEffect(() => {
    if (selectedFile) {
      setStableFile(selectedFile);
    }
  }, [selectedFile]);

  // Memoized handler to update both our stable state and notify parent
  const handleSelectFile = useCallback(
    (file: string) => {
      // If streaming, don't allow switching files
      if (isStreaming) {
        return;
      }
      setStableFile(file);
      setSelectedFile(file);
    },
    [setSelectedFile, isStreaming]
  );

  // Calculate loading progress for demo purposes - in a real app, this would come from actual file loading progress
  const [loadingProgress, setLoadingProgress] = useState(0);
  console.log('loadingProgress', loadingProgress);

  // Simulate loading progress when loading files
  useEffect(() => {
    if (isLoadingGitHubFiles) {
      setLoadingProgress(0);
      const interval = setInterval(() => {
        setLoadingProgress((prev) => {
          // Cap at 90% to show we're still waiting for something
          if (prev >= 90) {
            clearInterval(interval);
            return 90;
          }
          return prev + Math.random() * 10;
        });
      }, 400);

      return () => clearInterval(interval);
    } else {
      // When loading is done, jump to 100%
      setLoadingProgress(100);
    }
  }, [isLoadingGitHubFiles]);

  return (
    <div className="h-full flex flex-col">
      <div className="flex-1 flex overflow-hidden">
        <ResizablePanelGroup direction="horizontal">
          <ResizablePanel
            defaultSize={20}
            minSize={12}
            maxSize={30}
            className="bg-[#161618] min-h-0 shadow-sm"
          >
            <AnimatePresence mode="wait">
              {isLoadingGitHubFiles ? (
                <motion.div
                  key="loading"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <div className="py-2 px-3 flex-shrink-0 border-b border-[#2a2a2c]">
                    <h3 className="text-xs font-medium text-[#f3f6f6] flex items-center gap-1.5">
                      <ShimmerText className="text-xs">
                        Loading files
                      </ShimmerText>
                    </h3>
                  </div>
                  <FileTreeShimmer />
                </motion.div>
              ) : (
                <motion.div
                  key="content"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="h-full flex flex-col overflow-hidden"
                >
                  <div className="py-2 px-3 flex-shrink-0 border-b border-[#2a2a2c]">
                    <h3 className="text-xs font-medium text-[#f3f6f6] flex items-center gap-1.5">
                      <AnimatePresence mode="wait">
                        {isStreaming ? (
                          <motion.span
                            key="streaming"
                            initial={{ opacity: 0, scale: 0.9 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.9 }}
                            transition={{ duration: 0.2 }}
                            className="flex items-center gap-1.5"
                          >
                            <Icons.sparkles className="w-3.5 h-3.5 text-[#969798] animate-pulse" />
                            <ShimmerText className="text-xs">
                              AI Editing
                            </ShimmerText>
                          </motion.span>
                        ) : (
                          <motion.span
                            key="files"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            transition={{ duration: 0.2 }}
                          >
                            Files
                          </motion.span>
                        )}
                      </AnimatePresence>
                    </h3>
                  </div>
                  <div className="flex-1 min-h-0 overflow-hidden">
                    <FileTree
                      files={files}
                      selectedFile={stableFile}
                      onSelectFile={handleSelectFile}
                      isStreaming={isStreaming}
                    />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </ResizablePanel>

          <ResizableHandle className="w-[1px] bg-[#2a2a2c] data-[hover]:bg-[#3a3a3c] transition-colors" />

          <ResizablePanel defaultSize={80} className="min-h-0 bg-[#161618]">
            <AnimatePresence mode="wait">
              {isLoadingGitHubFiles ? (
                <div className="min-h-screen bg-[#161618] p-4 font-mono">
                  <div className="max-w-4xl mx-auto">
                    {/* Tab bar */}
                    <div className="flex gap-2 border-b border-[#2D2D2D] pb-3 mb-3 w-full">
                      <Skeleton className="h-4 w-[120px] bg-[#2D2D2D]" />
                      <Skeleton className="h-4 w-[100px] bg-[#2D2D2D]" />
                    </div>

                    {/* Code lines */}
                    <div className="space-y-2">
                      {Array.from({ length: 20 }).map((_, i) => (
                        <div key={i} className="flex items-center gap-4">
                          <Skeleton className="w-8 h-4 bg-[#2D2D2D]" />
                          <ShimmerLine width={`${20 + ((i * 13) % 40)}%`} />
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <motion.div
                  key="editor-content"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="h-full rounded-md shadow-sm overflow-hidden"
                >
                  <CodeEditor
                    selectedFile={stableFile}
                    files={files}
                    onUpdateFile={onUpdateFile}
                    loadFileContent={loadFileContent}
                    isStreaming={isStreaming}
                  />
                </motion.div>
              )}
            </AnimatePresence>
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>
    </div>
  );
}

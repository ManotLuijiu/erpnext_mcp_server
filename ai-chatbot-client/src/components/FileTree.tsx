'use client';

import { ChevronRight, ChevronDown, File, Folder } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import { type FileEntry } from '@/types';
import React, { useState, useEffect, useCallback, type JSX } from 'react';
import { AnimatePresence, motion } from 'framer-motion';

interface FileTreeNodeProps {
  filePath: string;
  fileName: string;
  fileType: 'file' | 'directory';
  selectedFile: string | null;
  onSelectFile: (path: string) => void;
  isExpanded?: boolean;
  onToggleExpand?: () => void;
  hasChildren?: boolean;
}

const FileTreeNode = ({
  filePath,
  fileName,
  fileType,
  selectedFile,
  onSelectFile,
  isExpanded,
  onToggleExpand,
  // hasChildren,
}: FileTreeNodeProps) => {
  const isSelected = selectedFile === filePath;

  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation(); // Prevent bubbling

      if (fileType === 'file') {
        onSelectFile(filePath);
      } else if (fileType === 'directory' && onToggleExpand) {
        onToggleExpand();
      }
    },
    [fileType, filePath, onSelectFile, onToggleExpand]
  );

  return (
    <div
      className={cn(
        'flex items-center gap-1.5 py-1 px-2 transition-colors text-xs',
        'hover:bg-[#212122] rounded-md',
        isSelected
          ? 'bg-[#212122] text-[#f3f6f6] shadow-sm rounded-md'
          : 'text-[#969798] hover:text-[#f3f6f6]',
        fileType === 'file' ? 'cursor-pointer' : 'cursor-default'
      )}
      onClick={handleClick}
    >
      {fileType === 'directory' && (
        <span className="flex-shrink-0 cursor-pointer">
          {isExpanded ? (
            <ChevronDown className="w-3 h-3" />
          ) : (
            <ChevronRight className="w-3 h-3" />
          )}
        </span>
      )}
      {fileType === 'file' ? (
        <File className="w-3.5 h-3.5 flex-shrink-0" />
      ) : (
        <Folder className="w-3.5 h-3.5 flex-shrink-0 cursor-pointer" />
      )}
      <span className="truncate" title={filePath}>
        {fileName}
      </span>
    </div>
  );
};

interface FileTreeProps {
  files: Record<string, FileEntry>;
  selectedFile: string | null;
  onSelectFile: (path: string) => void;
  isStreaming?: boolean;
}

// Type for our tree structure
interface FileNode {
  name: string;
  path: string;
  type: 'file' | 'directory';
  children: FileNode[];
}

export const FileTree = ({
  files,
  selectedFile,
  onSelectFile,
  isStreaming = false,
}: FileTreeProps) => {
  const [expandedFolders, setExpandedFolders] = useState<
    Record<string, boolean>
  >({});
  const [fileTree, setFileTree] = useState<FileNode>({
    name: '/',
    path: '',
    type: 'directory',
    children: [],
  });

  // Build tree from flat files list
  useEffect(() => {
    const root: FileNode = {
      name: '/',
      path: '',
      type: 'directory',
      children: [],
    };

    // Create a helper function to get or create a directory node
    const getOrCreateDir = (
      pathParts: string[],
      currentNode: FileNode
    ): FileNode => {
      if (pathParts.length === 0) return currentNode;

      const firstPart = pathParts[0];
      const remainingParts = pathParts.slice(1);
      const path = currentNode.path
        ? `${currentNode.path}/${firstPart}`
        : firstPart;

      // Try to find existing child node
      let childNode = currentNode.children.find(
        (node) => node.name === firstPart
      );

      // Create new directory node if it doesn't exist
      if (!childNode) {
        childNode = {
          name: firstPart,
          path: path,
          type: 'directory',
          children: [],
        };
        currentNode.children.push(childNode);
      }

      // If this is a file node that we've previously marked as a directory, continue
      if (remainingParts.length > 0) {
        return getOrCreateDir(remainingParts, childNode);
      }

      return childNode;
    };

    // Process each file and build the tree
    Object.entries(files).forEach(([path, file]) => {
      // Skip root entries and hidden directories (.bolt and dist)
      if (
        !path ||
        path === '/' ||
        path.startsWith('/.bolt') ||
        path === '/.bolt' ||
        path.startsWith('/dist') ||
        path === '/dist'
      )
        return;

      // Normalize path by removing leading slash
      const normalizedPath = path.startsWith('/') ? path.substring(1) : path;
      const pathParts = normalizedPath.split('/');

      // Skip if first part is .bolt or dist
      if (
        pathParts[0] === '.bolt' ||
        pathParts[0] === 'dist' ||
        pathParts[0] === 'node_modules'
      )
        return;

      // For files, we add to parent directory
      if (file.type === 'file') {
        const fileName = pathParts.pop()!;
        const parentNode = pathParts.length
          ? getOrCreateDir(pathParts, root)
          : root;

        // Add file node if it doesn't exist already
        if (!parentNode.children.find((node) => node.name === fileName)) {
          parentNode.children.push({
            name: fileName,
            path: path,
            type: 'file',
            children: [],
          });
        }
      }
      // For directories, we create the entire path
      else if (file.type === 'directory') {
        getOrCreateDir(pathParts, root);
      }
    });

    // Sort each directory's children: directories first, then files, both alphabetically
    const sortNode = (node: FileNode) => {
      // Sort children
      node.children.sort((a, b) => {
        // Directories first
        if (a.type !== b.type) {
          return a.type === 'directory' ? -1 : 1;
        }
        // Then alphabetically
        return a.name.localeCompare(b.name);
      });

      // Recursively sort children
      node.children.forEach(sortNode);
    };

    sortNode(root);
    setFileTree(root);

    // Auto-expand the root directory
    setExpandedFolders((prev) => ({
      ...prev,
      '': true,
    }));
  }, [files]);

  // Recursive function to render the tree
  const renderTree = (node: FileNode, depth: number = 0): JSX.Element => {
    const isExpanded = expandedFolders[node.path] || false;

    // Only render directories and files, not root
    if (node.path === '') {
      return (
        <div className="space-y-0.5">
          {node.children.map((child) => renderTree(child, depth))}
        </div>
      );
    }

    if (node.type === 'directory') {
      return (
        <div key={node.path} className="flex flex-col">
          <div style={{ paddingLeft: `${depth * 12}px` }}>
            <FileTreeNode
              filePath={node.path}
              fileName={node.name}
              fileType="directory"
              selectedFile={selectedFile}
              onSelectFile={onSelectFile}
              isExpanded={isExpanded}
              onToggleExpand={() => {
                // Prevent expanding/collapsing directories during streaming
                if (isStreaming) return;

                setExpandedFolders((prev) => ({
                  ...prev,
                  [node.path]: !prev[node.path],
                }));
              }}
              hasChildren={node.children.length > 0}
            />
          </div>

          <AnimatePresence>
            {isExpanded && node.children.length > 0 && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="flex flex-col space-y-0.5"
              >
                {node.children.map((child) => renderTree(child, depth + 1))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      );
    } else {
      const isActiveFile = isStreaming && selectedFile === node.path;

      return (
        <div key={node.path} style={{ paddingLeft: `${depth * 12}px` }}>
          <FileTreeNode
            filePath={node.path}
            fileName={node.name}
            fileType="file"
            selectedFile={selectedFile}
            onSelectFile={onSelectFile}
          />
          {isActiveFile && (
            <div className="ml-6 text-xs text-blue-400 animate-pulse">
              AI writing...
            </div>
          )}
        </div>
      );
    }
  };

  return (
    <ScrollArea className="h-full w-full">
      <div className="py-1">{renderTree(fileTree)}</div>
    </ScrollArea>
  );
};

export default FileTree;

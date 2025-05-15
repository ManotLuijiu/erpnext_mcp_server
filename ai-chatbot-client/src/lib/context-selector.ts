import { WebContainer } from '@webcontainer/api';
import { FileEntry } from '@/types';

// Export an empty array - show everything
export const IGNORE_PATTERNS: string[] = [];

/**
 * Always include all files - no more ignoring
 */
export const shouldIgnoreFile = (_filePath: string): boolean => {
  return false;
};

/**
 * Gets all files recursively from the WebContainer
 */
export const getAllFiles = async (
  webContainerInstance: WebContainer,
  dir: string = '/',
  files: Record<string, FileEntry> = {}
): Promise<Record<string, FileEntry>> => {
  try {
    const entries = await webContainerInstance.fs.readdir(dir, {
      withFileTypes: true,
    });

    for (const entry of entries) {
      const path = `${dir === '/' ? '' : dir}/${entry.name}`;

      if (entry.isDirectory()) {
        // Add the directory itself to the files
        files[path] = {
          name: path,
          content: {},
          type: 'directory',
        };
        await getAllFiles(webContainerInstance, path, files);
      } else {
        try {
          const content = await webContainerInstance.fs.readFile(path, 'utf-8');
          files[path] = {
            name: path,
            content: content,
            type: 'file',
          };
        } catch (error) {
          console.error(`Error reading file ${path}:`, error);
        }
      }
    }

    return files;
  } catch (error) {
    console.error(`Error reading directory ${dir}:`, error);
    return files;
  }
};

/**
 * Creates a context string from files for the AI
 */
export const createContextString = (
  files: Record<string, FileEntry>
): string => {
  let context = '';

  // Sort files by path to make the context more organized
  const sortedFiles = Object.entries(files).sort(([pathA], [pathB]) =>
    pathA.localeCompare(pathB)
  );

  // Limit the total size to avoid exceeding token limits
  const MAX_CONTENT_LENGTH = 150000; // Adjust based on model's token limit
  let currentLength = 0;

  for (const [path, file] of sortedFiles) {
    if (file.type === 'file') {
      // Skip binary files or very large files
      if (typeof file.content !== 'string' || file.content.length > 50000) {
        continue;
      }

      const fileEntry = `File: ${path}\n\`\`\`\n${file.content}\n\`\`\`\n\n`;

      // Check if adding this file would exceed the size limit
      if (currentLength + fileEntry.length > MAX_CONTENT_LENGTH) {
        context += `\n[Additional files omitted due to size constraints]\n`;
        break;
      }

      context += fileEntry;
      currentLength += fileEntry.length;
    }
  }

  return context;
};

/**
 * Creates a directory tree string for the AI
 */
export const createDirectoryTreeString = (
  files: Record<string, FileEntry>
): string => {
  const paths = Object.keys(files).sort();
  let treeString = 'Directory Structure:\n';

  // Build a proper tree structure
  const tree: Record<string, any> = {};

  // First build the tree structure
  for (const path of paths) {
    const parts = path.split('/').filter(Boolean);
    let current = tree;

    // Create path in tree
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      const isFile = i === parts.length - 1;

      if (isFile) {
        current[part] = null; // null means it's a file
      } else {
        if (!current[part]) {
          current[part] = {};
        }
        current = current[part];
      }
    }
  }

  // Function to print tree
  const printTree = (
    node: Record<string, any>,
    prefix: string = '',
    indent: string = ''
  ): string => {
    let result = '';
    const entries = Object.entries(node);

    for (let i = 0; i < entries.length; i++) {
      const [name, children] = entries[i];
      const isLast = i === entries.length - 1;
      const isFile = children === null;

      // Add current line
      result += `${prefix}${isLast ? '└── ' : '├── '}${name}${isFile ? '' : '/'}\n`;

      // Add children if it's a directory
      if (!isFile) {
        const newPrefix = `${prefix}${isLast ? '    ' : '│   '}`;
        result += printTree(children, newPrefix);
      }
    }

    return result;
  };

  treeString += printTree(tree);

  return treeString;
};

/**
 * Collects all file context for sending to the AI
 */
export const collectAIContext = async (
  webContainerInstance: WebContainer
): Promise<{
  files: Record<string, FileEntry>;
  contextString: string;
  treeString: string;
}> => {
  if (!webContainerInstance) {
    throw new Error('WebContainer is not initialized');
  }

  // Get all files from the WebContainer
  const files = await getAllFiles(webContainerInstance);

  // For now, just return empty context string as requested
  return {
    files,
    contextString: '',
    treeString: '',
  };
};

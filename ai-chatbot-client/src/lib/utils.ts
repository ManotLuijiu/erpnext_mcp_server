import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

import { decode as base64Decode } from 'js-base64';
import { GITHUB_API_BASE_URL } from './constants';
import he from 'he';
import { type FileEntry } from '@/types';
import { type ITheme } from '@xterm/xterm';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Define types locally since they aren't exported form types file
export interface GitHubFile {
  name: string;
  path: string;
  content: string;
}

export interface FileSystemTree {
  [key: string]: {
    file?: {
      contents: string;
    };
    directory?: FileSystemTree;
  };
}

export interface GeneratedFile {
  path: string;
  content: string;
}

export const extractRepoName = (url: string): string | null => {
  // Handle different GitHub URL formats
  // 1. https://github.com/username/repo
  // 2. https://github.com/username/repo.git
  // 3. git@github.com:username/repo.git
  // 4. username/repo (already in correct format)

  try {
    // If it's already in the format 'username/repo' or 'username/repo.git'
    if (/^[^\/]+\/[^\/]+$/.test(url) || /^[^\/]+\/[^\/]+\.git$/.test(url)) {
      return url.replace(/\.git$/, '');
    }

    // Standard https GitHub URL
    const httpsMatch = url.match(
      /github\.com\/([^/]+\/[^/]+?)(?:\.git)?(?:\/)?$/
    );
    if (httpsMatch && httpsMatch[1]) {
      return httpsMatch[1];
    }

    // SSH GitHub URL
    const sshMatch = url.match(/git@github\.com:([^/]+\/[^/]+?)(?:\.git)?$/);
    if (sshMatch && sshMatch[1]) {
      return sshMatch[1];
    }

    console.error(`Failed to extract repo name from URL: ${url}`);
    return null;
  } catch (error) {
    console.error(`Error extracting repo name from URL: ${url}`, error);
    return null;
  }
};

export const getGitHubRepoContent = async (
  repoName: string,
  path: string = ''
): Promise<GitHubFile[]> => {
  const baseUrl = GITHUB_API_BASE_URL;
  try {
    // Use GitHub token if available (increases rate limit from 60 to 5000 requests/hour)
    const token = process.env.NEXT_PUBLIC_GITHUB_ACCESS_TOKEN;
    const headers: HeadersInit = {
      Accept: 'application/vnd.github.v3+json',
    };

    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    // Log rate limit info when available
    const logRateLimits = (response: Response) => {
      const remaining = response.headers.get('x-ratelimit-remaining');
      const limit = response.headers.get('x-ratelimit-limit');
      const reset = response.headers.get('x-ratelimit-reset');

      if (remaining && limit) {
        const resetTime = reset
          ? new Date(parseInt(reset) * 1000).toLocaleTimeString()
          : 'unknown';
        // console.log(`GitHub API Rate Limit: ${remaining}/${limit} remaining. Resets at ${resetTime}`);

        console.log('resetTime', resetTime);

        // Warn if getting low on requests
        if (parseInt(remaining) < 10) {
          console.warn(
            `⚠️ GitHub API rate limit getting low: ${remaining}/${limit} remaining`
          );
        }
      }
    };

    // Fetch the content of the current path
    const response = await fetch(
      `${baseUrl}/repos/${repoName}/contents/${path}`,
      {
        headers,
      }
    );

    // Check for rate limiting
    logRateLimits(response);

    if (
      response.status === 403 &&
      response.headers.get('x-ratelimit-remaining') === '0'
    ) {
      const resetTime = response.headers.get('x-ratelimit-reset');
      const resetDate = resetTime
        ? new Date(parseInt(resetTime) * 1000).toLocaleTimeString()
        : 'unknown time';
      throw new Error(`GitHub API rate limit exceeded. Resets at ${resetDate}`);
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        `GitHub API error! Status: ${response.status}. Message: ${errorData.message || 'Unknown error'}`
      );
    }

    const data: any = await response.json();

    // Handle single file response
    if (!Array.isArray(data)) {
      if (data.type === 'file') {
        // For files, we need to get the content from the "content" field (base64 encoded)
        let content = '';
        if (data.content) {
          content = base64Decode(data.content);
        } else if (data.git_url) {
          // Fallback to blob API if content is not included
          const blobResponse = await fetch(data.git_url, { headers });
          logRateLimits(blobResponse);

          if (blobResponse.ok) {
            const blobData = await blobResponse.json();
            if (blobData.content) {
              content = base64Decode(blobData.content);
            }
          }
        }
        return [{ name: data.name, path: data.path, content }];
      }
      return [];
    }

    // Process directories and files, but introduce a delay to avoid rate limiting
    const contents: GitHubFile[] = [];

    // Process items with a small delay between each to prevent rate limiting
    for (const item of data) {
      if (item.type === 'dir') {
        // Add delay before recursive API calls
        await new Promise((resolve) => setTimeout(resolve, 100));
        const dirContents = await getGitHubRepoContent(repoName, item.path);
        contents.push(...dirContents);
      } else if (item.type === 'file') {
        // For files, use the contents API directly instead of download_url
        let fileContent = '';

        // Small files (<1MB) will have content field directly
        if (item.size < 1000000 && item.url) {
          // Add delay for each file request
          await new Promise((resolve) => setTimeout(resolve, 50));

          try {
            const fileResponse = await fetch(item.url, { headers });
            logRateLimits(fileResponse);

            if (fileResponse.ok) {
              const fileData = await fileResponse.json();
              if (fileData.content) {
                fileContent = base64Decode(fileData.content);
              }
            }
          } catch (fetchError: any) {
            console.warn(
              `Error fetching content for ${item.path}: ${fetchError.message}`
            );
          }
        } else {
          // For larger files, note that they're too large
          fileContent = `// File too large to fetch automatically (${Math.round(item.size / 1024)}KB)\n// Edit this file to load its content.`;
        }

        contents.push({
          name: item.name,
          path: item.path,
          content: fileContent,
        });
      }
    }

    return contents;
  } catch (error: any) {
    console.error(
      `Error fetching repo contents for ${repoName}/${path}:`,
      error
    );
    throw error;
  }
};

const generateTextTree = (tree: FileSystemTree, prefix = ''): string => {
  const entries = Object.entries(tree);
  let treeString = '';
  entries.forEach(([name, node], index) => {
    const isLast = index === entries.length - 1;
    const connector = isLast ? '└── ' : '├── ';
    const newPrefix = prefix + (isLast ? '    ' : '│   ');

    if (
      node &&
      typeof node === 'object' &&
      'directory' in node &&
      node.directory
    ) {
      treeString += `${prefix}${connector}${name}/\n`;
      treeString += generateTextTree(node.directory, newPrefix);
    } else if (
      node &&
      typeof node === 'object' &&
      'file' in node &&
      node.file
    ) {
      treeString += `${prefix}${connector}${name}\n`;
    }
  });
  return treeString;
};

console.log('generateTextTree', generateTextTree);

// Define the structure for the output
export interface AIContextData {
  treeString: string;
  contentString: string; // Combined content of critical/selected files
  files: Record<string, FileEntry>; // Keep the raw files if needed elsewhere
}

export const transformGitHubFilesToState = (files: GitHubFile[]) => {
  const fileState: Record<
    string,
    { name: string; content: string; type: 'file' }
  > = {};
  files.forEach((file) => {
    fileState[file.path] = {
      name: file.path,
      content: file.content,
      type: 'file',
    };
  });
  return fileState;
};

// New function to create WebContainer-mountable file system
export const createMountableFileSystem = (
  filesInput:
    | GitHubFile[]
    | Record<string, FileEntry>
    | Record<string, { name: string; content: string; type: string }>
): Record<string, any> => {
  console.log('Creating mountable file system for WebContainer...');

  // Convert input to a consistent array format
  let processedFiles: Array<{ path: string; content: string }> = [];

  if (Array.isArray(filesInput)) {
    processedFiles = filesInput.map((file) => ({
      path: file.path,
      content: file.content,
    }));
    console.log(`Processing ${processedFiles.length} files from GitHub`);
  } else {
    processedFiles = Object.entries(filesInput).map(([path, fileEntry]) => ({
      path,
      content:
        typeof fileEntry.content === 'string'
          ? fileEntry.content
          : JSON.stringify(fileEntry.content),
    }));
    console.log(`Processing ${processedFiles.length} files from state`);
  }

  // Build WebContainer-compatible file system structure
  const fileSystem: Record<string, any> = {};

  // Debug tracking
  const pathsIncluded = new Set<string>();

  for (const file of processedFiles) {
    const pathParts = file.path.split('/');
    let currentLevel = fileSystem;

    // Track the full path of each directory we're creating
    let currentPath = '';

    // Navigate through directories
    for (let i = 0; i < pathParts.length - 1; i++) {
      const dirName = pathParts[i];

      // Skip empty directory names
      if (!dirName) continue;

      // Update current path
      currentPath = currentPath ? `${currentPath}/${dirName}` : dirName;
      pathsIncluded.add(currentPath);

      // Create directory if it doesn't exist
      if (!currentLevel[dirName]) {
        currentLevel[dirName] = { directory: {} };
      } else if (!currentLevel[dirName].directory) {
        // Force directory if something else with the same name exists
        currentLevel[dirName] = { directory: {} };
      }

      // Move to the next level
      currentLevel = currentLevel[dirName].directory;
    }

    // Add the file at the current level
    const fileName = pathParts[pathParts.length - 1];
    if (fileName) {
      currentLevel[fileName] = { file: { contents: file.content } };
      pathsIncluded.add(file.path);
    }
  }

  console.log(
    `Completed file system generation. Included ${pathsIncluded.size} paths.`
  );

  // Debug info for components/ui path specifically
  if (pathsIncluded.has('components/ui')) {
    console.log('components/ui folder was successfully included');
  } else {
    console.log('Warning: components/ui folder was NOT included');
  }

  return fileSystem;
};

export const getLanguageForFilename = (filename: string): string => {
  const extension = filename.split('.').pop()?.toLowerCase();
  if (extension === 'js' || extension === 'jsx') return 'javascript';
  if (extension === 'ts' || extension === 'tsx') return 'typescript';
  if (extension === 'html') return 'html';
  if (extension === 'css') return 'css';
  if (extension === 'json') return 'json';
  if (extension === 'md') return 'markdown';
  return 'plaintext';
};

export function extractFilesFromContent(content: string): GeneratedFile[] {
  const files: GeneratedFile[] = [];

  // First extract the boltArtifact blocks
  const artifactRegex = /<boltArtifact[^>]*>([\s\S]*?)<\/boltArtifact>/g;
  let artifactMatch;

  artifactMatch = artifactRegex.exec(content);
  while (artifactMatch !== null) {
    const artifactContent = artifactMatch[1];

    // Then extract file actions from each artifact
    const fileRegex =
      /<boltAction\s+type="file"\s+filePath="([^"]+)">([\s\S]*?)(?=<\/boltAction>)/g;
    let fileMatch = fileRegex.exec(artifactContent);

    while (fileMatch !== null) {
      const [_, path, fileContent] = fileMatch;
      if (path && fileContent) {
        files.push({
          path: he.decode(path.trim()),
          content: he.decode(fileContent.trim()),
        });
      }
      fileMatch = fileRegex.exec(artifactContent);
    }
  }

  // If no boltArtifact was found, try to extract boltAction directly
  // This is for backward compatibility
  if (files.length === 0) {
    const fileRegex =
      /<boltAction\s+type="file"\s+filePath="([^"]+)">([\s\S]*?)(?=<\/boltAction>|$)/g;
    let match;

    match = fileRegex.exec(content);
    while (match !== null) {
      const [_, path, fileContent] = match;
      if (path && fileContent) {
        files.push({
          path: he.decode(path.trim()),
          content: he.decode(fileContent.trim()),
        });
      }
      match = fileRegex.exec(content);
    }
  }

  return files;
}

export function getTerminalTheme(overrides?: ITheme): ITheme {
  return {
    cursor: '#000000',
    cursorAccent: '#000000',
    foreground: '#333333',
    background: '#FFFFFF', // Using white as default background
    selectionBackground: '#00000040',
    selectionForeground: '#333333',
    selectionInactiveBackground: '#00000020',

    // ansi escape code colors
    black: '#000000',
    red: '#cd3131',
    green: '#00bc00',
    yellow: '#949800',
    blue: '#0451a5',
    magenta: '#bc05bc',
    cyan: '#0598bc',
    white: '#555555',
    brightBlack: '#686868',
    brightRed: '#cd3131',
    brightGreen: '#00bc00',
    brightYellow: '#949800',
    brightBlue: '#0451a5',
    brightMagenta: '#bc05bc',
    brightCyan: '#0598bc',
    brightWhite: '#a5a5a5',

    ...overrides,
  };
}

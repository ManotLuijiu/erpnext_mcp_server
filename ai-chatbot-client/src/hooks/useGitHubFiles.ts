'use client';

import { useState, useEffect, useCallback } from 'react';
import { WebContainer } from '@webcontainer/api';
import { type FileEntry } from '@/types';
import { GITHUB_REPO_URL } from '@/lib/constants';
import {
  extractRepoName,
  getGitHubRepoContent,
  transformGitHubFilesToState,
  createMountableFileSystem,
} from '@/lib/utils';

// Type for GitHub file structure
// interface GitHubFile {
//   name: string;
//   path: string;
//   content: string;
// }

// Rate limit type for GitHub API
interface RateLimit {
  limit: number;
  remaining: number;
  resetTime: string | null;
}

export const useGitHubFiles = (
  webContainerInstance: WebContainer | null,
  customRepoName?: string
) => {
  const [files, setFiles] = useState<Record<string, FileEntry>>({});
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [isLoadingGitHubFiles, setIsLoadingGitHubFiles] = useState(true);
  const [gitHubError, setGitHubError] = useState<string | null>(null);
  const [rateLimit, setRateLimit] = useState<RateLimit | null>(null);
  const [filesystemMonitorId, setFilesystemMonitorId] = useState<number | null>(
    null
  );

  // Set up initial files from GitHub
  useEffect(() => {
    const initializeFiles = async () => {
      if (!webContainerInstance) return;

      setIsLoadingGitHubFiles(true);
      setGitHubError(null);

      // Use custom repo name if provided, otherwise extract from default URL
      const repoURL = customRepoName || GITHUB_REPO_URL;
      const repoName = extractRepoName(repoURL);

      if (!repoName) {
        setGitHubError(`Invalid GitHub repository URL provided: ${repoURL}`);
        setIsLoadingGitHubFiles(false);
        return;
      }

      try {
        // Fetch files from GitHub
        console.log(`Fetching files from GitHub repo: ${repoName}`);
        const fetchedFiles = await getGitHubRepoContent(repoName);

        if (fetchedFiles.length === 0) {
          setGitHubError(`No files found in repository: ${repoName}`);
          setIsLoadingGitHubFiles(false);
          return;
        }

        const fileState = transformGitHubFilesToState(fetchedFiles);
        setFiles(fileState);

        const defaultFile = fetchedFiles.find(
          (f) =>
            f.path.toLowerCase() === 'readme.md' || f.path === 'package.json'
        )?.path;
        setSelectedFile(defaultFile || null);

        try {
          // Mount ALL files to WebContainer with no filtering
          const mountableFileSystem = createMountableFileSystem(fetchedFiles);
          await webContainerInstance.mount(mountableFileSystem);
          console.log('Files mounted successfully to WebContainer');
        } catch (mountError: any) {
          console.error('Error mounting files:', mountError);
          throw new Error(`Failed to mount file system: ${mountError.message}`);
        }
      } catch (error: any) {
        console.error(`GitHub fetch error for repo ${repoName}:`, error);
        setGitHubError(
          `Failed to load files from ${repoName}: ${error.message}`
        );

        // Check for rate limit in error message
        if (error.message.includes('rate limit')) {
          const rateLimitMatch = error.message.match(
            /GitHub API rate limit exceeded. Resets at (.*)/
          );
          if (rateLimitMatch && rateLimitMatch[1]) {
            setRateLimit({
              limit: 60, // Default for unauthenticated
              remaining: 0,
              resetTime: rateLimitMatch[1],
            });
          }
        }
      } finally {
        setIsLoadingGitHubFiles(false);
      }
    };

    initializeFiles();
  }, [webContainerInstance, customRepoName]);

  // Scan filesystem recursively to get all files and directories
  const scanFileSystem = useCallback(
    async (webContainer: WebContainer) => {
      const result: Record<string, FileEntry> = {};

      // Recursive function to read directory contents
      const readDir = async (dir: string) => {
        try {
          const entries = await webContainer.fs.readdir(dir, {
            withFileTypes: true,
          });

          for (const entry of entries) {
            // Skip weird node_modules paths
            if (entry.name === 'node_modules') continue;

            const path =
              dir === '/' ? `/${entry.name}` : `${dir}/${entry.name}`;

            if (entry.isDirectory()) {
              // Add directory entry
              result[path] = {
                name: path,
                content: '', // Use empty string instead of empty object
                type: 'directory',
              };

              // Recursively process subdirectory
              await readDir(path);
            } else {
              // Preserve existing file content if it exists
              if (files[path] && typeof files[path].content === 'string') {
                result[path] = { ...files[path] };
              } else {
                // For files without existing content, create entry without loading content yet
                result[path] = {
                  name: path,
                  content: '', // Empty placeholder, content loaded on demand
                  type: 'file',
                };
              }
            }
          }
        } catch (error) {
          console.error(`Error reading directory ${dir}:`, error);
        }
      };

      // Start the scan from root
      await readDir('/');
      return result;
    },
    [files]
  );

  // Function to load content for a specific file
  const loadFileContent = useCallback(
    async (path: string): Promise<string> => {
      if (!webContainerInstance)
        throw new Error('WebContainer not initialized');

      try {
        // Try to read the file content from WebContainer
        const content = await webContainerInstance.fs.readFile(path, 'utf-8');

        // Update local files state with the content
        setFiles((prevFiles) => ({
          ...prevFiles,
          [path]: {
            ...prevFiles[path],
            content,
          },
        }));

        return content;
      } catch (error) {
        console.error(`Error loading file content for ${path}:`, error);
        throw error;
      }
    },
    [webContainerInstance, setFiles]
  );

  // Update file system representation periodically
  useEffect(() => {
    if (!webContainerInstance || isLoadingGitHubFiles) return;

    // Initial scan after loading
    const initialScan = async () => {
      const newFiles = await scanFileSystem(webContainerInstance);
      setFiles(newFiles);
    };

    initialScan();

    // Set up periodic scanning to detect file system changes
    const intervalId = window.setInterval(async () => {
      try {
        const newFiles = await scanFileSystem(webContainerInstance);

        // Update files state with new scan results
        setFiles((prev) => {
          // If the number of files is different, we've had changes
          if (Object.keys(prev).length !== Object.keys(newFiles).length) {
            console.log('File count changed, updating file tree');
            return newFiles;
          }

          // Check if any files were added or removed
          const prevPaths = new Set(Object.keys(prev));
          const newPaths = new Set(Object.keys(newFiles));

          // Check for new files
          for (const path of Array.from(newPaths)) {
            if (!prevPaths.has(path)) {
              console.log(`New file detected: ${path}`);
              return newFiles; // Files were added
            }
          }

          // Check for deleted files
          for (const path of Array.from(prevPaths)) {
            if (!newPaths.has(path)) {
              console.log(`File deleted: ${path}`);
              // If the currently selected file was deleted, select null
              if (selectedFile === path) {
                setSelectedFile(null);
              }
              return newFiles; // Files were deleted
            }
          }

          // No changes detected
          return prev;
        });
      } catch (error) {
        console.error('Error during file system scan:', error);
      }
    }, 2000); // Check for changes every 2 seconds

    setFilesystemMonitorId(intervalId);

    return () => {
      if (filesystemMonitorId) {
        clearInterval(filesystemMonitorId);
      }
    };
  }, [
    webContainerInstance,
    isLoadingGitHubFiles,
    scanFileSystem,
    selectedFile,
  ]);

  return {
    files,
    setFiles,
    selectedFile,
    setSelectedFile,
    isLoadingGitHubFiles,
    gitHubError,
    rateLimit,
    loadFileContent,
  };
};

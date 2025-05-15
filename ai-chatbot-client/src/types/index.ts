import { WebContainer } from '@webcontainer/api';

export interface Env {
  [key: string]: any;
}

export interface IProviderSetting {
  apiToken?: string;
  baseUrl?: string;
  organization?: string;
}

export interface FileEntry {
  name: string;
  content?: string;
  type: 'file' | 'directory';
}

export interface ContextAnnotation {
  type: string;
  [key: string]: any;
}

export interface ProgressAnnotation {
  type: 'progress';
  label: string;
  status: 'in-progress' | 'complete' | 'error';
  order: number;
  message: string;
  [key: string]: any;
}

export interface ModelInfo {
  name: string;
  label: string;
  provider: string;
  maxTokenAllowed: number;
}

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

export interface Template {
  name: string;
  label: string;
  description: string;
  githubRepo: string;
  tags: string[];
  icon: string;
}

export interface File {
  type: 'file';
  content: string;
  isBinary: boolean;
}

export interface Folder {
  type: 'folder';
}

type Dirent = File | Folder;

export type FileMap = Record<string, Dirent | undefined>;

export interface RateLimit {
  limit: number;
  remaining: number;
  resetTime?: Date;
  resetTimeString?: string;
  used: number;
}

export interface EditorRateLimit {
  resetTime?: Date;
}

// No need to extend Window interface here as it's already defined in types.d.ts

// Add this to the global window object
declare global {
  interface Window {
    webContainerInstance: WebContainer;
  }
}

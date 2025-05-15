import {
  generateText,
  type CoreTool,
  type GenerateTextResult,
  type Message,
} from 'ai';
import ignore from 'ignore';
import { IGNORE_PATTERNS, SECONDARY_MODEL } from '../constants';
import { DEFAULT_PROVIDER } from '../provider';
import {
  createFilesContext,
  extractCurrentContext,
  extractPropertiesFromMessage,
  simplifyBoltActions,
} from './serverUtils';
import type { Env, IProviderSetting, FileMap } from '../../types/index';

// Common patterns to ignore, similar to .gitignore

const ig = ignore().add(IGNORE_PATTERNS);

export async function selectContext(props: {
  messages: Message[];
  env?: Env;
  apiKeys?: Record<string, string>;
  files: FileMap;
  providerSettings?: Record<string, IProviderSetting>;
  promptId?: string;
  contextOptimization?: boolean;
  summary?: string;
  onFinish?: (
    resp: GenerateTextResult<Record<string, CoreTool<any, any>>, never>
  ) => void;
}) {
  const {
    messages,
    env: serverEnv,
    apiKeys,
    files,
    providerSettings,
    summary,
    onFinish,
  } = props;
  let currentModel = SECONDARY_MODEL;
  const processedMessages = messages.map((message) => {
    if (message.role === 'user') {
      const { model, content } = extractPropertiesFromMessage(message);
      currentModel = model;
      return { ...message, content };
    } else if (message.role == 'assistant') {
      let content = message.content;
      content = simplifyBoltActions(content);
      content = content.replace(
        /<div class=\\"__boltThought__\\">(.|[\r\n])*?<\/div>/,
        ''
      );
      content = content.replace(/<think>(.|[\r\n])*?<\/think>/, '');
      return { ...message, content };
    }
    return message;
  });

  const provider = DEFAULT_PROVIDER;

  const { codeContext } = extractCurrentContext(processedMessages);

  let filePaths = getFilePaths(files || {});
  filePaths = filePaths.filter((x) => {
    // Ensure we're using a relative path for the ignore check
    // Handle leading slash paths
    if (x.startsWith('/')) {
      // Find the last part of the path after the last slash
      const parts = x.split('/');
      const relativePath = parts[parts.length - 1];
      return !ig.ignores(relativePath);
    }

    // For relative paths, just use the path as is
    const relPath = x.replace('/home/project/', '');
    return !ig.ignores(relPath);
  });

  let context = '';
  const currrentFiles: string[] = [];
  const contextFiles: FileMap = {};

  if (codeContext?.type === 'codeContext') {
    const codeContextFiles: string[] = codeContext.files || [];
    Object.keys(files || {}).forEach((path) => {
      let relativePath = path;

      if (path.startsWith('/home/project/')) {
        relativePath = path.replace('/home/project/', '');
      }

      if (codeContextFiles.includes(relativePath)) {
        contextFiles[relativePath] = files[path];
        currrentFiles.push(relativePath);
      }
    });
    context = createFilesContext(contextFiles);
  }

  const summaryText = summary
    ? `Here is the summary of the chat till now: ${summary}`
    : 'No summary available yet. This is the beginning of the conversation.';

  const extractTextContent = (message: Message) =>
    Array.isArray(message.content)
      ? (message.content.find((item) => item.type === 'text')
          ?.text as string) || ''
      : message.content;

  const lastUserMessage = processedMessages
    .filter((x) => x.role == 'user')
    .pop();

  if (!lastUserMessage) {
    throw new Error('No user message found');
  }

  // Step 1: Generate file list with paths
  const filesList = filePaths.map((path) => {
    // Extract just the filename for display
    const filenameMatch = path.match(/([^/]+)$/);
    const filename = filenameMatch ? filenameMatch[1] : path;

    return `${path}`;
  });

  // Step 2: Select which files to include in the context
  const resp = await generateText({
    system: `
You are a senior software engineer reviewing code for another developer. You need to analyze the user's question and the code files available in the project to determine which files are most relevant for answering their question.

Please choose only the files that are ACTUALLY NEEDED to solve the user's problem.
Important rules:
1. Be VERY selective - choose only files that are directly relevant
2. Prioritize files that contain:
   - Code that needs to be modified
   - API endpoints or functions mentioned in the question
   - Model/schema definitions related to the question
   - Core utilities needed to understand the code
3. DO NOT select files just because they seem generally important
4. DO NOT select files that are definitely irrelevant to the question (like test files if testing isn't mentioned)
5. DO NOT include node_modules, .git, or other standard folders

Your task is to review the list of files and select ONLY the minimum set needed to properly answer the user's question.
`,
    prompt: `
${summaryText}

The most recent user query is:
---
${extractTextContent(lastUserMessage)}
---

Here are the files available in the project:
---
${filesList.join('\n')}
---

Based on the user's query, which files from this list should be included in the context for answering their question?
Please respond ONLY with a list of file paths without any explanation or commentary. Just the file paths separated by new lines.
`,
    model: provider.getModelInstance({
      model: currentModel,
      serverEnv: serverEnv || {},
      apiKeys,
      providerSettings,
    }) as any,
  });

  const selectedFiles = resp.text
    .split('\n')
    .map((file) => file.trim())
    .filter((file) => file.length > 0);

  console.debug('Selected Files:', selectedFiles);

  // Step 3: Create the actual context from selected files
  const selectedFileMap: FileMap = {};
  selectedFiles.forEach((file) => {
    const foundPath = filePaths.find(
      (path) => path.includes(file) || file.includes(path)
    );
    if (foundPath && files[foundPath]) {
      selectedFileMap[foundPath] = files[foundPath];
    }
  });

  if (onFinish) {
    // Make sure there's always usage information even if the response doesn't have it
    const safeResp = {
      ...resp,
      usage: resp.usage || {
        promptTokens: 100,
        completionTokens: 100,
        totalTokens: 200,
      },
    };
    onFinish(safeResp);
  }

  // Normalize all paths to be relative (remove any leading slashes)
  const normalizedFileMap: FileMap = {};
  Object.keys(selectedFileMap).forEach((path) => {
    let normalizedPath = path;

    // Remove WORK_DIR prefix if present
    if (normalizedPath.startsWith('/home/project/')) {
      normalizedPath = normalizedPath.replace('/home/project/', '');
    }

    // Remove any leading slashes to ensure it's relative
    while (normalizedPath.startsWith('/')) {
      normalizedPath = normalizedPath.substring(1);
    }

    // Use the normalized path as the new key
    normalizedFileMap[normalizedPath] = selectedFileMap[path];
  });

  return normalizedFileMap;
}

export function getFilePaths(files: FileMap): string[] {
  return Object.keys(files);
}

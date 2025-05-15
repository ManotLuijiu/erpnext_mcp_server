import {
  convertToCoreMessages,
  streamText as _streamText,
  type Message,
} from 'ai';
import { getSystemPrompt } from '../prompt';
import { DEFAULT_MODEL } from '../constants';
import {
  WORK_DIR,
  MODIFICATIONS_TAG_NAME,
  allowedHTMLElements,
} from '../prompt';
import {
  createFilesContext,
  extractPropertiesFromMessage,
} from './serverUtils';
import { getFilePaths } from './select-context';
import { DEFAULT_PROVIDER } from '../provider';
import type { Env, IProviderSetting } from '../../types/index';
import type { FileMap } from '../constants';

export type Messages = Message[];

export interface StreamingOptions
  extends Omit<Parameters<typeof _streamText>[0], 'model'> {
  supabaseConnection?: {
    isConnected: boolean;
    hasSelectedProject: boolean;
    credentials?: {
      anonKey?: string;
      supabaseUrl?: string;
    };
  };
}

// Fixed model settings for google/gemini-2.5-pro-preview-03-25
const FIXED_MAX_OUTPUT = 65535;

export async function streamText(props: {
  messages: Omit<Message, 'id'>[];
  env?: Env;
  options?: StreamingOptions;
  apiKeys?: Record<string, string>;
  files?: FileMap;
  providerSettings?: Record<string, IProviderSetting>;
  promptId?: string;
  contextOptimization?: boolean;
  contextFiles?: FileMap;
  summary?: string;
  messageSliceId?: number;
  promptEnhancing?: boolean;
}) {
  const {
    messages,
    env: serverEnv,
    options,
    apiKeys,
    files,
    providerSettings,
    promptId,
    contextOptimization,
    contextFiles,
    summary,
    promptEnhancing,
  } = props;

  // Force use of DEFAULT_MODEL only
  let currentModel = DEFAULT_MODEL;
  if (promptEnhancing) {
    currentModel = 'openai/gpt-4o-mini';
  }

  let processedMessages = messages.map((message) => {
    if (message.role === 'user') {
      const { content } = extractPropertiesFromMessage(message);
      return { ...message, content };
    } else if (message.role == 'assistant') {
      let content = message.content;
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

  // Simple prompt library implementation
  const getPromptFromLibrary = (promptId: string, options: any) => {
    // Default implementation - just return system prompt
    return getSystemPrompt(options.cwd);
  };

  let systemPrompt = promptId
    ? getPromptFromLibrary(promptId, {
        cwd: WORK_DIR,
        allowedHtmlElements: allowedHTMLElements,
        modificationTagName: MODIFICATIONS_TAG_NAME,
        supabase: {
          isConnected: options?.supabaseConnection?.isConnected || false,
          hasSelectedProject:
            options?.supabaseConnection?.hasSelectedProject || false,
          credentials: options?.supabaseConnection?.credentials || undefined,
        },
      })
    : getSystemPrompt();

  if (files && contextFiles && contextOptimization) {
    const codeContext = createFilesContext(contextFiles, true);
    const filePaths = getFilePaths(files);

    systemPrompt = `${systemPrompt}
Below are all the files present in the project:
---
${filePaths.join('\n')}
---

Below is the artifact containing the context loaded into context buffer for you to have knowledge of and might need changes to fullfill current user request.
CONTEXT BUFFER:
---
${codeContext}
---
`;

    if (summary) {
      systemPrompt = `${systemPrompt}
      below is the chat history till now
CHAT SUMMARY:
---
${props.summary}
---
`;

      if (props.messageSliceId) {
        processedMessages = processedMessages.slice(props.messageSliceId);
      } else {
        const lastMessage = processedMessages.pop();

        if (lastMessage) {
          processedMessages = [lastMessage];
        }
      }
    }
  }

  console.info(
    `Sending llm call to ${provider.name} with model ${currentModel}`
  );

  // Store original messages for reference
  const originalMessages = [...messages];
  const hasMultimodalContent = originalMessages.some((msg) =>
    Array.isArray(msg.content)
  );

  try {
    console.log('StreamText params:', {
      modelName: currentModel,
      hasMultimodalContent,
      messageCount: processedMessages.length,
      hasSummary: Boolean(summary),
      hasContextFiles: Boolean(contextFiles),
    });

    if (hasMultimodalContent) {
      /*
       * For multimodal content, we need to preserve the original array structure
       * but make sure the roles are valid and content items are properly formatted
       */
      const multimodalMessages = originalMessages.map((msg) => ({
        role:
          msg.role === 'system' ||
          msg.role === 'user' ||
          msg.role === 'assistant'
            ? msg.role
            : 'user',
        content: Array.isArray(msg.content)
          ? msg.content.map((item) => {
              // Ensure each content item has the correct format
              if (typeof item === 'string') {
                return { type: 'text', text: item };
              }

              if (item && typeof item === 'object') {
                if (item.type === 'image' && item.image) {
                  return { type: 'image', image: item.image };
                }

                if (item.type === 'text') {
                  return { type: 'text', text: item.text || '' };
                }
              }

              // Default fallback for unknown formats
              return { type: 'text', text: String(item || '') };
            })
          : [
              {
                type: 'text',
                text:
                  typeof msg.content === 'string'
                    ? msg.content
                    : String(msg.content || ''),
              },
            ],
      }));

      return await _streamText({
        model: provider.getModelInstance({
          model: currentModel,
          serverEnv: serverEnv || {},
          apiKeys,
          providerSettings,
        }) as any,
        system: systemPrompt,
        maxTokens: FIXED_MAX_OUTPUT,
        messages: multimodalMessages as any,
        ...options,
      });
    } else {
      // For non-multimodal content, we use the standard approach
      const normalizedTextMessages = processedMessages.map((msg) => ({
        role:
          msg.role === 'system' ||
          msg.role === 'user' ||
          msg.role === 'assistant'
            ? msg.role
            : 'user',
        content:
          typeof msg.content === 'string'
            ? msg.content
            : String(msg.content || ''),
      }));

      return await _streamText({
        model: provider.getModelInstance({
          model: currentModel,
          serverEnv: serverEnv || {},
          apiKeys,
          providerSettings,
        }) as any,
        system: systemPrompt,
        maxTokens: FIXED_MAX_OUTPUT,
        messages: convertToCoreMessages(normalizedTextMessages),
        ...options,
      });
    }
  } catch (error: any) {
    console.error('Error in streamText:', error);
    console.error('Error stack:', error.stack);

    // Special handling for format errors
    if (
      error.message &&
      error.message.includes(
        'messages must be an array of CoreMessage or UIMessage'
      )
    ) {
      console.warn(
        'Message format error detected, attempting recovery with explicit formatting...'
      );

      // Create properly formatted messages for all cases as a last resort
      const fallbackMessages = processedMessages.map((msg) => {
        // Determine text content with careful type handling
        let textContent = '';

        if (typeof msg.content === 'string') {
          textContent = msg.content;
        } else if (Array.isArray(msg.content)) {
          // Handle array content safely
          const contentArray = msg.content as any[];
          textContent = contentArray
            .map((contentItem) =>
              typeof contentItem === 'string'
                ? contentItem
                : contentItem?.text ||
                  contentItem?.image ||
                  String(contentItem || '')
            )
            .join(' ');
        } else {
          textContent = String(msg.content || '');
        }

        return {
          role:
            msg.role === 'system' ||
            msg.role === 'user' ||
            msg.role === 'assistant'
              ? msg.role
              : 'user',
          content: [
            {
              type: 'text',
              text: textContent,
            },
          ],
        };
      });

      // Try one more time with the fallback format
      return await _streamText({
        model: provider.getModelInstance({
          model: currentModel,
          serverEnv: serverEnv || {},
          apiKeys,
          providerSettings,
        }) as any,
        system: systemPrompt,
        maxTokens: FIXED_MAX_OUTPUT,
        messages: fallbackMessages as any,
        ...options,
      });
    }

    // If it's not a format error, re-throw the original error
    throw error;
  }
}

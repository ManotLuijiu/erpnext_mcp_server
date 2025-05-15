import {
  generateText,
  type CoreTool,
  type GenerateTextResult,
  type Message,
} from 'ai';
import { SECONDARY_MODEL } from '../constants';
import { DEFAULT_PROVIDER } from '../provider';
import {
  extractCurrentContext,
  extractPropertiesFromMessage,
  simplifyBoltActions,
} from './serverUtils';
import type { Env, IProviderSetting } from '@/types/index';

export async function createSummary(props: {
  messages: Message[];
  env?: Env;
  apiKeys?: Record<string, string>;
  providerSettings?: Record<string, IProviderSetting>;
  promptId?: string;
  contextOptimization?: boolean;
  onFinish?: (
    resp: GenerateTextResult<Record<string, CoreTool<any, any>>, never>
  ) => void;
}) {
  const {
    messages,
    env: serverEnv,
    apiKeys,
    providerSettings,
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

  let slicedMessages = processedMessages;
  const { summary } = extractCurrentContext(processedMessages);
  let summaryText: string | undefined = undefined;
  let chatId: string | undefined = undefined;

  if (summary && summary.type === 'chatSummary') {
    chatId = (summary as any).chatId;
    summaryText = `Below is the Chat Summary till now, this is chat summary before the conversation provided by the user 
you should also use this as historical message while providing the response to the user.        
${(summary as any).summary}`;

    if (chatId) {
      let index = 0;

      for (let i = 0; i < processedMessages.length; i++) {
        if (processedMessages[i].id === chatId) {
          index = i;
          break;
        }
      }
      slicedMessages = processedMessages.slice(index + 1);
    }
  }

  console.debug('Sliced Messages:', slicedMessages.length);

  const extractTextContent = (message: Message) =>
    Array.isArray(message.content)
      ? (message.content.find((item) => item.type === 'text')
          ?.text as string) || ''
      : message.content;

  // select files from the list of code file from the project that might be useful for the current request from the user
  const resp = await generateText({
    system: `
        You are a software engineer. You are working on a project. you need to summarize the work till now and provide a summary of the chat till now.

        Please only use the following format to generate the summary:
---
# Project Overview
- **Project**: {project_name} - {brief_description}
- **Current Phase**: {phase}
- **Tech Stack**: {languages}, {frameworks}, {key_dependencies}
- **Environment**: {critical_env_details}

# Conversation Context
- **Last Topic**: {main_discussion_point}
- **Key Decisions**: {important_decisions_made}
- **User Context**:
  - Technical Level: {expertise_level}
  - Preferences: {coding_style_preferences}
  - Communication: {preferred_explanation_style}

# Implementation Status
## Current State
- **Active Feature**: {feature_in_development}
- **Progress**: {what_works_and_what_doesn't}
- **Blockers**: {current_challenges}

## Code Evolution
- **Recent Changes**: {latest_modifications}
- **Working Patterns**: {successful_approaches}
- **Failed Approaches**: {attempted_solutions_that_failed}

# Requirements
- **Implemented**: {completed_features}
- **In Progress**: {current_focus}
- **Pending**: {upcoming_features}
- **Technical Constraints**: {critical_constraints}

# Critical Memory
- **Must Preserve**: {crucial_technical_context}
- **User Requirements**: {specific_user_needs}
- **Known Issues**: {documented_problems}

# Next Actions
- **Immediate**: {next_steps}
- **Open Questions**: {unresolved_issues}

---
Note:
4. Keep entries concise and focused on information needed for continuity


---
        
        RULES:
        * Only provide the whole summary of the chat till now.
        * Do not provide any new information.
        * DO not need to think too much just start writing imidiately
        * do not write any thing other that the summary with with the provided structure
        `,
    prompt: `

Here is the previous summary of the chat:
<old_summary>
${summaryText} 
</old_summary>

Below is the chat after that:
---
<new_chats>
${slicedMessages
  .map((x) => {
    return `---\n[${x.role}] ${extractTextContent(x)}\n---`;
  })
  .join('\n')}
</new_chats>
---

Please provide a summary of the chat till now including the hitorical summary of the chat.
`,
    model: provider.getModelInstance({
      model: currentModel,
      serverEnv: serverEnv || {},
      apiKeys,
      providerSettings,
    }) as any,
  });

  const response = resp.text;

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

  return response;
}

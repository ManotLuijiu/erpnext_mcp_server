import type { IProviderSetting, ModelInfo, Env } from '@/types/index';
import type { LanguageModelV1 } from 'ai';
import { createOpenRouter } from '@openrouter/ai-sdk-provider';

interface OpenRouterModel {
  name: string;
  id: string;
  context_length: number;
  pricing: {
    prompt: number;
    completion: number;
  };
}

interface OpenRouterModelsResponse {
  data: OpenRouterModel[];
}

// Simple abstract BaseProvider class implementation
export abstract class BaseProvider {
  abstract name: string;
  abstract getApiKeyLink: string;
  abstract config: {
    apiTokenKey: string;
  };
  abstract staticModels: ModelInfo[];
  abstract getDynamicModels(
    apiKeys?: Record<string, string>,
    settings?: IProviderSetting,
    serverEnv?: Record<string, string>
  ): Promise<ModelInfo[]>;
  abstract getModelInstance(options: {
    model: string;
    serverEnv: Env;
    apiKeys?: Record<string, string>;
    providerSettings?: Record<string, IProviderSetting>;
  }): LanguageModelV1;
}

export default class OpenRouterProvider extends BaseProvider {
  name = 'OpenRouter';
  getApiKeyLink = 'https://openrouter.ai/settings/keys';

  config = {
    apiTokenKey: 'OPENROUTER_API_KEY',
  };

  staticModels: ModelInfo[] = [
    {
      name: 'anthropic/claude-3.5-sonnet',
      label: 'Anthropic: Claude 3.5 Sonnet (OpenRouter)',
      provider: 'OpenRouter',
      maxTokenAllowed: 8000,
    },
    {
      name: 'anthropic/claude-3-haiku',
      label: 'Anthropic: Claude 3 Haiku (OpenRouter)',
      provider: 'OpenRouter',
      maxTokenAllowed: 8000,
    },
    {
      name: 'deepseek/deepseek-coder',
      label: 'Deepseek-Coder V2 236B (OpenRouter)',
      provider: 'OpenRouter',
      maxTokenAllowed: 8000,
    },
    {
      name: 'google/gemini-flash-1.5',
      label: 'Google Gemini Flash 1.5 (OpenRouter)',
      provider: 'OpenRouter',
      maxTokenAllowed: 8000,
    },
    {
      name: 'google/gemini-pro-1.5',
      label: 'Google Gemini Pro 1.5 (OpenRouter)',
      provider: 'OpenRouter',
      maxTokenAllowed: 8000,
    },
    {
      name: 'x-ai/grok-beta',
      label: 'xAI Grok Beta (OpenRouter)',
      provider: 'OpenRouter',
      maxTokenAllowed: 8000,
    },
    {
      name: 'mistralai/mistral-nemo',
      label: 'OpenRouter Mistral Nemo (OpenRouter)',
      provider: 'OpenRouter',
      maxTokenAllowed: 8000,
    },
    {
      name: 'qwen/qwen-110b-chat',
      label: 'OpenRouter Qwen 110b Chat (OpenRouter)',
      provider: 'OpenRouter',
      maxTokenAllowed: 8000,
    },
    {
      name: 'cohere/command',
      label: 'Cohere Command (OpenRouter)',
      provider: 'OpenRouter',
      maxTokenAllowed: 4096,
    },
  ];

  async getDynamicModels(
    _apiKeys?: Record<string, string>,
    _settings?: IProviderSetting,
    _serverEnv: Record<string, string> = {}
  ): Promise<ModelInfo[]> {
    try {
      const response = await fetch('https://openrouter.ai/api/v1/models', {
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const data = (await response.json()) as OpenRouterModelsResponse;

      return data.data
        .sort((a, b) => a.name.localeCompare(b.name))
        .map((m) => ({
          name: m.id,
          label: `${m.name} - in:$${(m.pricing.prompt * 1_000_000).toFixed(2)} out:$${(m.pricing.completion * 1_000_000).toFixed(2)} - context ${Math.floor(m.context_length / 1000)}k`,
          provider: this.name,
          maxTokenAllowed: 8000,
        }));
    } catch (error) {
      console.error('Error getting OpenRouter models:', error);
      return [];
    }
  }

  getModelInstance(options: {
    model: string;
    serverEnv: Env;
    apiKeys?: Record<string, string>;
    providerSettings?: Record<string, IProviderSetting>;
  }): LanguageModelV1 {
    const { model } = options;

    // Get API key directly from process.env
    const apiKey = process.env[this.config.apiTokenKey];

    if (!apiKey) {
      throw new Error(
        `Missing API key for ${this.name} provider. Please set ${this.config.apiTokenKey} in your .env.local file.`
      );
    }

    const openRouter = createOpenRouter({
      apiKey,
    });
    const instance = openRouter.chat(model) as LanguageModelV1;

    return instance;
  }
}

// Create an instance of the default provider
export const DEFAULT_PROVIDER = new OpenRouterProvider();

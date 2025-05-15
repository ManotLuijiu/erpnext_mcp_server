import { encode } from 'gpt-tokenizer';

type ModelFamily = 'gpt' | 'claude' | 'gemini' | 'default';

/**
 * Counts tokens for various model families using the gpt-tokenizer
 * @param text The text to count tokens for
 * @param modelFamily The model family to use for counting ('gpt', 'claude', 'gemini', or 'default')
 * @returns The number of tokens in the text
 */
export function countTokens(
  text: string,
  modelFamily: ModelFamily = 'default'
): number {
  try {
    // All major models (GPT, Claude, Gemini) use tokenizers based on similar principles
    // gpt-tokenizer uses GPT-3/4 tokenization which is a good approximation for all of them
    const tokens = encode(text);
    return tokens.length;
  } catch (error) {
    console.error('Error counting tokens:', error);
    // Fallback to rough character-based estimation if tokenizer fails
    return Math.ceil(text.length / 4);
  }
}

/**
 * Counts tokens in a message array
 * @param messages Array of messages to count tokens for
 * @param modelFamily The model family to use for token counting
 * @returns Total token count across all messages
 */
export function countMessageTokens(
  messages: Array<{ role: string; content: string }>,
  modelFamily: ModelFamily = 'default'
): number {
  // Count tokens in each message and sum them
  return messages.reduce((total, message) => {
    // Add tokens for message content
    const contentTokens = countTokens(message.content, modelFamily);

    // Add tokens for message metadata (role, etc.) - roughly 4 tokens per message
    const metadataTokens = 4;

    return total + contentTokens + metadataTokens;
  }, 0);
}

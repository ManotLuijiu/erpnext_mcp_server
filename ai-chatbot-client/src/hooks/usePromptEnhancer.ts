'use client';

import { useState } from 'react';

interface ProviderInfo {
  name: string;
  [key: string]: any;
}

export function usePromptEnhancer() {
  const [enhancingPrompt, setEnhancingPrompt] = useState(false);
  const [promptEnhanced, setPromptEnhanced] = useState(false);

  const resetEnhancer = () => {
    setEnhancingPrompt(false);
    setPromptEnhanced(false);
  };

  const enhancePrompt = async (
    input: string,
    setInput: (value: string) => void,
    model: string,
    provider: ProviderInfo
  ) => {
    if (!input.trim()) return;

    setEnhancingPrompt(true);
    setPromptEnhanced(false);

    const requestBody = {
      message: input,
      model,
      provider,
    };

    try {
      const response = await fetch('/api/enhancer', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        console.error('Error from enhancer API:', response.status);
        throw new Error(`Enhancer API error: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('Failed to get reader from response');
      }

      const originalInput = input;
      const decoder = new TextDecoder();
      let enhancedInput = '';

      try {
        setInput('');

        while (true) {
          const { value, done } = await reader.read();

          if (done) {
            break;
          }

          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.trim() === '' || !line.startsWith('data: ')) continue;

            const data = line.slice(6);
            if (data === '[DONE]') continue;

            try {
              const json = JSON.parse(data);
              const token = json.choices?.[0]?.delta?.content || '';

              if (token) {
                enhancedInput += token;
                console.log('Enhanced token:', token);

                // Update input in real-time
                setInput(enhancedInput);
              }
            } catch (error) {
              console.error('Error parsing JSON from stream:', error);
            }
          }
        }

        // Final update
        if (enhancedInput.trim()) {
          setInput(enhancedInput);
        } else {
          setInput(originalInput);
        }
      } catch (error) {
        console.error('Error processing enhancer stream:', error);
        setInput(originalInput);
        throw error;
      } finally {
        setEnhancingPrompt(false);
        setPromptEnhanced(true);
      }
    } catch (error) {
      console.error('Error enhancing prompt:', error);
      setEnhancingPrompt(false);
      setInput(input); // Revert to original input on error
    }
  };

  return { enhancingPrompt, promptEnhanced, enhancePrompt, resetEnhancer };
}

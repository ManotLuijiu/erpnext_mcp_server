import { useState, useCallback } from 'react';
import { useFrappePostCall } from 'frappe-react-sdk';
import type { TranslationRequest, TranslationResult } from '../types';

/**!SECTION
 * Custom hook for handling translations
 */
export const useTranslation = () => {
  const [isTranslating, setIsTranslating] = useState<boolean>(false);
  const [lastResult, setLastResult] = useState<TranslationResult | null>(null);

  const { loading, error, call } = useFrappePostCall<TranslationResult>(
    'erpnext_mcp_server.api.translation.translate_single_entry'
  );

  const translate = useCallback(
    async (request: TranslationRequest) => {
      setIsTranslating(true);

      try {
        const result = await call({
          file_path: request.filePath,
          entry_id: request.entryId,
          model_provider: request.modelProvider || 'openai',
          model: request.model,
        });

        setLastResult(result);
        return result;
      } catch (error) {
        console.error('Translation error: ', error);
        throw error;
      } finally {
        setIsTranslating(false);
      }
    },
    [call]
  );
  return {
    translate,
    isTranslating: isTranslating || loading,
    lastResult,
    error,
  };
};

export const useFrappeTranslation = () => {
  const isFrappe = (text: string): string => {
    if (window.__ && typeof window.__ === 'function') {
      return window.__(text);
    }
    return text;
  };

  return { __: isFrappe };
};

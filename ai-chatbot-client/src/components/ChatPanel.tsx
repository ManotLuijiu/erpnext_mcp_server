'use client';

import { useRef, useEffect, useState } from 'react';
import {
  MessageSquare,
  AlertTriangle,
  Loader2,
  Terminal,
  Check,
  ArrowUp,
  Paperclip,
  ChevronDown,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import { usePromptEnhancer } from '@/hooks/usePromptEnhancer';
import { cn } from '@/lib/utils';
import { motion, AnimatePresence } from 'framer-motion';
import { UserMessage } from '@/components/chat/UserMessage';
import {
  AssistantMessage,
  ProgressType,
  ProgressStatus,
} from '@/components/chat/AssistantMessage';
import { LoadingProgressPanel } from '@/components/chat/LoadingProgressPanel';
import { ErrorMessage } from '@/components/chat/ErrorMessage';
import { Icons } from './ui/icons';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

interface ProgressIndicator {
  label: ProgressType;
  status: ProgressStatus;
  message: string;
  order: number;
}

interface ChatPanelProps {
  messages: ChatMessage[];
  input: string;
  setInput: (input: string) => void;
  sendMessageToAI: (message: string) => void;
  openRouterError: string | null;
  isProcessing?: boolean;
  streamingComplete?: boolean;
  activeFile?: string | null;
  completedFiles?: Set<string>;
  activeCommand?: string | null;
  completedCommands?: Set<string>;
  isLoadingGitHubFiles?: boolean;
  isInstallingDeps?: boolean;
  isStartingDevServer?: boolean;
  progress?: ProgressIndicator[];
}

export const ChatPanel = ({
  messages,
  input,
  setInput,
  sendMessageToAI,
  openRouterError,
  isProcessing = false,
  streamingComplete = true,
  activeFile,
  completedFiles,
  activeCommand,
  completedCommands,
  isLoadingGitHubFiles = false,
  isInstallingDeps = false,
  isStartingDevServer = false,
  progress = [],
}: ChatPanelProps) => {
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { enhancingPrompt, enhancePrompt } = usePromptEnhancer();
  const [isScrolledToBottom, setIsScrolledToBottom] = useState(true);
  const [projectHasBeenLoaded, setProjectHasBeenLoaded] = useState(false);

  const hasLoadingStarted =
    isLoadingGitHubFiles ||
    isInstallingDeps ||
    isStartingDevServer ||
    projectHasBeenLoaded;

  useEffect(() => {
    if (isLoadingGitHubFiles || isInstallingDeps || isStartingDevServer) {
      setProjectHasBeenLoaded(true);
    }
  }, [isLoadingGitHubFiles, isInstallingDeps, isStartingDevServer]);

  const scrollToBottom = () => {
    if (chatContainerRef.current) {
      const scrollContainer = chatContainerRef.current.querySelector(
        '[data-radix-scroll-area-viewport]'
      );
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight;
        setIsScrolledToBottom(true);
      }
    }
  };

  // Handle scroll events to determine if we're at the bottom
  const handleScroll = () => {
    if (chatContainerRef.current) {
      const scrollContainer = chatContainerRef.current.querySelector(
        '[data-radix-scroll-area-viewport]'
      );
      if (scrollContainer) {
        const { scrollTop, scrollHeight, clientHeight } = scrollContainer;
        // Consider "at bottom" if within 50px of the bottom
        setIsScrolledToBottom(scrollHeight - scrollTop - clientHeight < 50);
      }
    }
  };

  useEffect(() => {
    scrollToBottom();

    // Add scroll event listener
    const scrollContainer = chatContainerRef.current?.querySelector(
      '[data-radix-scroll-area-viewport]'
    );
    if (scrollContainer) {
      scrollContainer.addEventListener('scroll', handleScroll);
      return () => scrollContainer.removeEventListener('scroll', handleScroll);
    }
  }, [messages]);

  // Auto-resize textarea based on content
  useEffect(() => {
    if (textareaRef.current) {
      // Reset height to auto to get the correct scrollHeight
      textareaRef.current.style.height = 'auto';

      // Calculate new height (capped at max height)
      const maxHeight = window.innerHeight * 0.3; // 30% of viewport height
      const scrollHeight = textareaRef.current.scrollHeight;
      const newHeight = Math.min(Math.max(80, scrollHeight), maxHeight);

      textareaRef.current.style.height = `${newHeight}px`;

      // Auto scroll to the bottom of the textarea
      textareaRef.current.scrollTop = textareaRef.current.scrollHeight;
    }
  }, [input]);

  // Handle sending message
  const handleSendMessage = () => {
    if (!input.trim() || isProcessing) return;

    const message = input.trim();
    sendMessageToAI(message);
    setInput(''); // Clear input after sending
  };

  return (
    <div className="w-full flex flex-col h-full bg-[#101012] border-r border-[#313133] shadow-lg overflow-hidden">
      <div className="relative flex-1 overflow-hidden">
        <ScrollArea className="h-full bg-[#101012]" ref={chatContainerRef}>
          <div className="py-8 px-4">
            <AnimatePresence>
              <div className="flex flex-col break-words word-wrap">
                {hasLoadingStarted && (
                  <LoadingProgressPanel
                    isLoadingGitHubFiles={isLoadingGitHubFiles}
                    isInstallingDeps={isInstallingDeps}
                    isStartingDevServer={isStartingDevServer}
                  />
                )}

                {messages.map((message, index) =>
                  message.role === 'user' ? (
                    <UserMessage
                      key={`user-${index}`}
                      content={message.content}
                    />
                  ) : (
                    <AssistantMessage
                      key={`assistant-${index}`}
                      content={message.content}
                      isStreaming={
                        !streamingComplete && index === messages.length - 1
                      }
                      activeFile={
                        index === messages.length - 1 ? activeFile : undefined
                      }
                      completedFiles={
                        index === messages.length - 1
                          ? completedFiles
                          : undefined
                      }
                      activeCommand={
                        index === messages.length - 1
                          ? activeCommand
                          : undefined
                      }
                      completedCommands={
                        index === messages.length - 1
                          ? completedCommands
                          : undefined
                      }
                      progress={
                        index === messages.length - 1 ? progress : undefined
                      }
                    />
                  )
                )}

                {openRouterError && <ErrorMessage error={openRouterError} />}
              </div>
            </AnimatePresence>
          </div>
        </ScrollArea>

        <div
          className="absolute bottom-0 left-0 right-0 h-16 pointer-events-none"
          style={{
            background:
              'linear-gradient(to bottom, rgba(16, 16, 18, 0) 0%, rgba(16, 16, 18, 0.8) 50%, rgba(16, 16, 18, 1) 100%)',
          }}
        />

        <AnimatePresence>
          {!isScrolledToBottom && (
            <motion.button
              className="absolute bottom-4 right-4 h-8 w-8 rounded-full bg-[#212122] text-[#f3f6f6] flex items-center justify-center shadow-md hover:bg-[#313133] transition-colors z-10"
              onClick={scrollToBottom}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              whileHover={{ scale: 1.05 }}
              title="Scroll to bottom"
            >
              <ChevronDown className="w-4 h-4" />
            </motion.button>
          )}
        </AnimatePresence>
      </div>

      <div className="p-3">
        <div className="relative rounded-lg border border-[#313133] bg-[#161618] overflow-hidden shadow-md">
          <Textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Describe the changes you want to make"
            className={cn(
              'flex-1 border-0 bg-[#161618] text-[#f3f6f6] placeholder:text-[#969798] resize-none text-sm p-3 pr-12 pb-12 min-h-[80px] max-h-[30vh] overflow-y-auto focus-visible:ring-0 focus-visible:ring-offset-0 focus:outline-none focus-visible:outline-none transition-all duration-200'
            )}
            rows={1}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
              }
            }}
            disabled={isProcessing || enhancingPrompt}
          />

          <div className="absolute bottom-0 left-0 right-0 flex items-center px-3 py-2 bg-[#161618]">
            <div className="flex items-center gap-1">
              <Button
                size="icon"
                variant="ghost"
                className="h-8 w-8 text-[#969798] hover:text-[#f3f6f6] hover:bg-[#212122]"
              >
                <Paperclip className="h-4 w-4" />
              </Button>
              <AnimatePresence>
                {input.length > 0 && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.8 }}
                    transition={{ duration: 0.2 }}
                  >
                    <Button
                      onClick={() =>
                        enhancePrompt(input, setInput, 'gpt-4o', {
                          name: 'OpenAI',
                          apiKey: process.env.OPENAI_API_KEY,
                        })
                      }
                      size="icon"
                      variant="ghost"
                      className="h-8 w-8 text-[#969798] hover:text-[#f3f6f6] hover:bg-[#212122]"
                    >
                      <Icons.sparkles
                        className={cn(
                          'h-4 w-4',
                          enhancingPrompt && 'animate-pulse'
                        )}
                      />
                    </Button>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            <div className="flex items-center gap-2 ml-auto">
              <Button
                size="icon"
                onClick={handleSendMessage}
                className={cn(
                  'h-8 w-8 rounded-full transition-colors duration-200',
                  input.trim() && !isProcessing
                    ? 'bg-[#f3f6f6] text-[#161618] hover:bg-[#e3e6e6]'
                    : 'bg-[#212122] text-[#969798]'
                )}
                disabled={
                  isProcessing ||
                  !input.trim() ||
                  (messages.length > 0 &&
                    messages[messages.length - 1].content === '...')
                }
              >
                {isProcessing ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <ArrowUp className="w-4 h-4" />
                )}
              </Button>
            </div>
          </div>
        </div>

        <motion.p
          className="text-xs text-[#969798] mt-2 flex items-center gap-1.5 justify-center"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5, duration: 0.3 }}
        >
          <AlertTriangle className="w-3 h-3" />
          Assistant can make mistakes
        </motion.p>
      </div>
    </div>
  );
};

'use client';

import { Markdown } from '@/components/Markdown';
import { motion } from 'framer-motion';
import { BookDashed, Brain, MessageSquare, WrapText } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

export type ProgressType = 'summary' | 'context' | 'response';
export type ProgressStatus = 'in-progress' | 'complete';

interface ProgressIndicator {
  label: ProgressType;
  status: ProgressStatus;
  message: string;
  order: number;
}

interface AssistantMessageProps {
  content: string;
  isStreaming?: boolean;
  activeFile?: string | null;
  completedFiles?: Set<string>;
  activeCommand?: string | null;
  completedCommands?: Set<string>;
  progress?: ProgressIndicator[];
}

// Helper function to process content with bolt artifacts
const processContent = (
  content: string
): { beforeBolt: string; afterBolt: string } => {
  // Default result
  const result = { beforeBolt: '', afterBolt: '' };

  // If there are no bolt artifacts, return the whole content as beforeBolt
  if (!content.includes('<boltArtifact')) {
    result.beforeBolt = content;
    return result;
  }

  // Find the first opening boltArtifact tag
  const startIndex = content.indexOf('<boltArtifact');
  if (startIndex !== -1) {
    // Everything before the first <boltArtifact> goes in beforeBolt
    result.beforeBolt = content.substring(0, startIndex).trim();

    // Find the last closing boltArtifact tag
    const endTagPattern = '</boltArtifact>';
    const endIndex = content.lastIndexOf(endTagPattern);

    if (endIndex !== -1) {
      // Everything after the last </boltArtifact> goes in afterBolt
      const afterEndIndex = endIndex + endTagPattern.length;
      result.afterBolt = content.substring(afterEndIndex).trim();
    }
  }

  return result;
};

const AiStreamState = ({
  isStreaming,
  progress,
}: { isStreaming: boolean; progress?: ProgressIndicator[] }) => {
  const [isTransitioning, setIsTransitioning] = useState(false);

  // Determine current state based on progress data
  const currentState = useMemo(() => {
    if (!progress || progress.length === 0) return 'summary';

    // Find the most recent in-progress item
    const inProgressItem = progress
      .filter((item) => item.status === 'in-progress')
      .sort((a, b) => b.order - a.order)[0];

    if (inProgressItem) {
      return inProgressItem.label;
    }

    // If no in-progress items, find the most recent completed item
    const lastCompleted = progress
      .filter((item) => item.status === 'complete')
      .sort((a, b) => b.order - a.order)[0];

    if (lastCompleted) {
      if (lastCompleted.label === 'summary') return 'context';
      if (lastCompleted.label === 'context') return 'response';
      return 'thinking';
    }

    return 'summary';
  }, [progress]);

  // Handle transitions
  useEffect(() => {
    if (!isStreaming) return;

    setIsTransitioning(true);
    const transitionTimeout = setTimeout(() => {
      setIsTransitioning(false);
    }, 300);

    return () => clearTimeout(transitionTimeout);
  }, [isStreaming, currentState]);

  let icon;
  let displayText;

  switch (currentState) {
    case 'summary':
      icon = <WrapText className="w-4 h-4 text-[#969798]" />;
      displayText = 'Creating summary';
      break;
    case 'context':
      icon = <BookDashed className="w-4 h-4 text-[#969798]" />;
      displayText = 'Selecting context';
      break;
    case 'response':
    default:
      icon = <Brain className="w-4 h-4 text-[#969798]" />;
      displayText = 'Reasoning';
  }

  // Calculate text length-based dynamic spread (similar to text-shimmer component)
  const spread = displayText.length * 2;

  return (
    <motion.div
      className={`flex items-center gap-2 mb-3 ${isTransitioning ? 'blur-sm' : 'blur-0'}`}
      animate={{ filter: isTransitioning ? 'blur(4px)' : 'blur(0px)' }}
      transition={{ duration: 0.3, ease: 'easeInOut' }}
    >
      <div className={`${isTransitioning ? '' : 'animate-pulse'}`}>{icon}</div>
      <motion.span
        className="text-sm font-medium text-transparent bg-clip-text relative inline-block"
        initial={{ backgroundPosition: '100% center' }}
        animate={{ backgroundPosition: '0% center' }}
        transition={{
          repeat: Infinity,
          duration: 2,
          ease: 'linear',
          repeatType: 'loop',
        }}
        style={{
          backgroundImage: `linear-gradient(90deg, rgba(0,0,0,0) calc(50% - ${spread}px), #fefefe, rgba(0,0,0,0) calc(50% + ${spread}px)), linear-gradient(#969798, #969798)`,
          backgroundSize: '250% 100%, 100% 100%',
          backgroundRepeat: 'no-repeat, no-repeat',
        }}
      >
        {displayText}
      </motion.span>
    </motion.div>
  );
};

export const AssistantMessage = ({
  content,
  isStreaming,
  activeFile,
  completedFiles,
  activeCommand,
  completedCommands,
  progress = [],
}: AssistantMessageProps) => {
  const [displayContent, setDisplayContent] = useState<React.ReactNode>(null);

  useEffect(() => {
    if (content) {
      // Extract content before and after bolt artifacts
      const { beforeBolt, afterBolt } = processContent(content);

      // Build the display content
      setDisplayContent(
        <div className="flex flex-col w-full gap-2">
          {/* Text before the bolt artifact */}
          {beforeBolt && (
            <Markdown content={beforeBolt} isStreaming={isStreaming} />
          )}

          {/* File and command updates - only show if we have any status to display */}
          {(activeFile ||
            (completedFiles && completedFiles.size > 0) ||
            activeCommand ||
            (completedCommands && completedCommands.size > 0)) && (
            <Markdown
              content=""
              activeFile={activeFile}
              completedFiles={completedFiles}
              activeCommand={activeCommand}
              completedCommands={completedCommands}
              isStreaming={isStreaming}
            />
          )}

          {/* Text after the bolt artifact */}
          {afterBolt && (
            <Markdown content={afterBolt} isStreaming={isStreaming} />
          )}
        </div>
      );
    }
  }, [
    content,
    isStreaming,
    activeFile,
    completedFiles,
    activeCommand,
    completedCommands,
    progress,
  ]);

  return (
    <motion.div
      className="flex flex-col w-full mb-4"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="flex w-full items-start gap-2">
        <div className="h-6 w-6 rounded-full bg-[#2a2a2c] flex-shrink-0 flex items-center justify-center">
          <MessageSquare className="w-3.5 h-3.5 text-[#969798]" />
        </div>
        <div className="flex-1 text-[#f3f6f6] overflow-hidden break-words whitespace-pre-wrap overflow-wrap-anywhere">
          {/* Show progress indicator when streaming but no content yet */}
          {isStreaming && !content && (
            <AiStreamState isStreaming={isStreaming} progress={progress} />
          )}

          {displayContent}
        </div>
      </div>
    </motion.div>
  );
};

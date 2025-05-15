'use client';

import { memo } from 'react';
import { motion } from 'framer-motion';
import { User } from 'lucide-react';

interface UserMessageProps {
  content: string;
}

export const UserMessage = memo(({ content }: UserMessageProps) => {
  return (
    <motion.div
      className="flex flex-col w-full mb-4"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="flex w-full items-start gap-2">
        <div className="h-6 w-6 rounded-full bg-[#2a2a2c] flex-shrink-0 flex items-center justify-center">
          <User className="w-3.5 h-3.5 text-[#e3e6e6]" />
        </div>
        <div className="flex-1 text-[#f2f6f6] break-words whitespace-pre-wrap overflow-wrap-anywhere pr-2 overflow-hidden">
          {content}
        </div>
      </div>
    </motion.div>
  );
});

UserMessage.displayName = 'UserMessage';

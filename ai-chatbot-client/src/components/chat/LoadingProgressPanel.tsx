'use client';

import { motion } from 'framer-motion';
import { MessageSquare, Loader2, Terminal, Check } from 'lucide-react';
import { cn } from '@/lib/utils';

interface LoadingProgressPanelProps {
  isLoadingGitHubFiles: boolean;
  isInstallingDeps: boolean;
  isStartingDevServer: boolean;
}

export const LoadingProgressPanel = ({
  isLoadingGitHubFiles,
  isInstallingDeps,
  isStartingDevServer,
}: LoadingProgressPanelProps) => {
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
        <div className="flex-1">
          <div className="text-sm text-[#f3f6f6] mb-4">
            I&apos;m importing your project into the WebContainer. This may take
            a moment as I set everything up.
          </div>

          <div className="border border-[#313133] overflow-hidden rounded-lg w-full shadow-md">
            <div className="p-4 bg-[#161618] text-[#f3f6f6] font-medium border-b border-[#313133]">
              Importing Project
            </div>
            <div className="p-4 bg-[#161618]">
              <ul className="list-none space-y-4">
                <li>
                  <div className="flex items-center gap-2 mb-1 text-sm">
                    {/* Files loading status */}
                    {isLoadingGitHubFiles === true ? (
                      <div className="h-5 w-5 rounded-full border-2 border-t-transparent border-blue-400 animate-spin" />
                    ) : !isLoadingGitHubFiles ? (
                      <div className="h-5 w-5 rounded-full bg-blue-500/20 flex items-center justify-center">
                        <Check className="h-3 w-3 text-blue-400" />
                      </div>
                    ) : (
                      <div className="h-5 w-5 rounded-full border border-[#313133] flex items-center justify-center">
                        <div className="h-2 w-2 rounded-full bg-[#313133]" />
                      </div>
                    )}
                    <div
                      className={cn(
                        isLoadingGitHubFiles === true
                          ? 'text-blue-400'
                          : !isLoadingGitHubFiles
                            ? 'text-[#f3f6f6]'
                            : 'text-[#969798]'
                      )}
                    >
                      Loading project files
                    </div>
                  </div>
                </li>

                <li>
                  <div className="flex items-center gap-2 mb-1 text-sm">
                    {/* Deps installation status */}
                    {isInstallingDeps === true ? (
                      <div className="h-5 w-5 rounded-full border-2 border-t-transparent border-blue-400 animate-spin" />
                    ) : isInstallingDeps === false && !isLoadingGitHubFiles ? (
                      <div className="h-5 w-5 rounded-full bg-blue-500/20 flex items-center justify-center">
                        <Check className="h-3 w-3 text-blue-400" />
                      </div>
                    ) : (
                      <div className="h-5 w-5 rounded-full border border-[#313133] flex items-center justify-center">
                        <div className="h-2 w-2 rounded-full bg-[#313133]" />
                      </div>
                    )}
                    <div
                      className={cn(
                        isInstallingDeps === true
                          ? 'text-blue-400'
                          : isInstallingDeps === false && !isLoadingGitHubFiles
                            ? 'text-[#f3f6f6]'
                            : 'text-[#969798]'
                      )}
                    >
                      Install dependencies
                    </div>
                  </div>
                  {isInstallingDeps === true && (
                    <motion.div
                      className="text-xs border border-[#313133] rounded-md p-2 bg-[#101012] font-mono mt-2 mb-2"
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      transition={{ duration: 0.2 }}
                    >
                      npm install
                    </motion.div>
                  )}
                </li>

                <li>
                  <div className="flex items-center gap-2 mb-1 text-sm">
                    {/* Server starting status */}
                    {isStartingDevServer === true ? (
                      <div className="h-5 w-5 rounded-full border-2 border-t-transparent border-blue-400 animate-spin" />
                    ) : isStartingDevServer === false &&
                      !isInstallingDeps &&
                      !isLoadingGitHubFiles ? (
                      <div className="h-5 w-5 rounded-full bg-blue-500/20 flex items-center justify-center">
                        <Terminal className="h-3 w-3 text-blue-400" />
                      </div>
                    ) : (
                      <div className="h-5 w-5 rounded-full border border-[#313133] flex items-center justify-center">
                        <div className="h-2 w-2 rounded-full bg-[#313133]" />
                      </div>
                    )}
                    <div
                      className={cn(
                        isStartingDevServer === true
                          ? 'text-blue-400'
                          : isStartingDevServer === false &&
                              !isInstallingDeps &&
                              !isLoadingGitHubFiles
                            ? 'text-blue-400'
                            : 'text-[#969798]'
                      )}
                    >
                      Start application
                    </div>
                  </div>
                  {(isStartingDevServer === true ||
                    (isStartingDevServer === false &&
                      !isInstallingDeps &&
                      !isLoadingGitHubFiles)) && (
                    <motion.div
                      className="text-xs border border-[#313133] rounded-md p-2 bg-[#101012] font-mono mt-2"
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      transition={{ duration: 0.2 }}
                    >
                      npm run dev
                    </motion.div>
                  )}
                </li>
              </ul>
            </div>
          </div>
          {isStartingDevServer === true ||
            (isStartingDevServer === false &&
              !isInstallingDeps &&
              !isLoadingGitHubFiles && (
                <motion.p
                  className="text-sm text-[#f3f6f6] mt-4"
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3 }}
                >
                  I have imported your project into the WebContainer. You can
                  now start coding.
                </motion.p>
              ))}
        </div>
      </div>
    </motion.div>
  );
};

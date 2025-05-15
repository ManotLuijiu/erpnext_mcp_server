'use client';

import { AlertTriangle, Github } from 'lucide-react';
import { Skeleton } from './ui/skeleton';

interface LoadingOverlayProps {
  error: string | null;
  isGitHubRateLimited?: boolean;
  rateLimitResetTime?: string | null;
}

export const LoadingOverlay = ({
  error,
  isGitHubRateLimited = false,
  rateLimitResetTime = null,
}: LoadingOverlayProps) => {
  if (error) {
    const isRateLimitError =
      error.includes('rate limit exceeded') || isGitHubRateLimited;
    const isNotFoundError =
      error.includes('Status: 404') || error.includes('Not Found');

    return (
      <div className="absolute inset-0 bg-app-background/95 backdrop-blur-sm flex flex-col items-center justify-center z-50 text-text-primary p-6">
        <div className="max-w-lg w-full bg-[#161618] border border-[#313133] px-6 py-8 rounded-lg">
          <div className="flex items-start">
            <AlertTriangle className="w-6 h-6 text-red-500 mr-4 flex-shrink-0 mt-1" />
            <div>
              <h2 className="text-lg font-medium mb-3">
                Initialization Failed
              </h2>
              <p className="text-text-secondary text-sm mb-4">{error}</p>
            </div>
          </div>

          {isRateLimitError && (
            <div className="mt-4 bg-secondary/30 p-4 border-l-2 border-red-500">
              <div className="flex items-center mb-2">
                <Github className="mr-2 text-text-secondary" size={16} />
                <h3 className="text-sm font-medium">
                  GitHub API Rate Limit Exceeded
                </h3>
              </div>

              {rateLimitResetTime && (
                <p className="text-text-secondary text-xs">
                  Rate limit will reset at: {rateLimitResetTime}
                </p>
              )}

              <p className="text-text-secondary text-xs mt-2">
                Consider adding a GitHub personal access token to increase your
                rate limit.
              </p>
            </div>
          )}

          {isNotFoundError && (
            <div className="mt-4 bg-secondary/30 p-4 border-l-2 border-red-500">
              <div className="flex items-center mb-2">
                <Github className="mr-2 text-text-secondary" size={16} />
                <h3 className="text-sm font-medium">Repository Not Found</h3>
              </div>

              <p className="text-text-secondary text-xs mt-2">
                The GitHub repository could not be found. This could be because:
              </p>
              <ul className="text-text-secondary text-xs mt-1 space-y-1 pl-4">
                <li>• The repository URL is incorrect</li>
                <li>• The repository is private and requires authentication</li>
                <li>• The repository has been deleted or renamed</li>
              </ul>

              <p className="text-text-secondary text-xs mt-2">
                You will be automatically redirected to the default template.
              </p>
            </div>
          )}

          <div className="mt-6 pt-4 border-t border-panel">
            <p className="text-xs text-text-secondary">
              Please check the repository URL, your GitHub token (if required),
              and the browser console for more details. Refreshing the page
              might help.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return null;
};

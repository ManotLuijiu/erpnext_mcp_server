'use client';

import { useState, useCallback } from 'react';
import {
  Loader2,
  OctagonAlert,
  RefreshCcw,
  ExternalLink,
  ChevronDown,
  ArrowLeft,
  ArrowRight,
  Search,
  RotateCw,
  Code,
  Server,
} from 'lucide-react';
import { Skeleton } from './ui/skeleton';
import { cn } from '@/lib/utils';
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
} from '@/components/ui/dropdown-menu';

interface PreviewPanelProps {
  previews: { port: number; url: string }[];
  isLoading: boolean;
  initialRoute?: string;
}

export const PreviewPanel = ({
  previews,
  isLoading,
  initialRoute = '/',
}: PreviewPanelProps) => {
  const [selectedPort, setSelectedPort] = useState<number | null>(
    previews.length > 0 ? previews[0].port : null
  );
  const [route, setRoute] = useState<string>(initialRoute);
  const [isPortDropdownOpen, setIsPortDropdownOpen] = useState(false);
  const [iframeKey, setIframeKey] = useState<number>(0);

  const selectedPreview =
    previews.find((p) => p.port === selectedPort) || previews[0];
  const iframeSrc = selectedPreview
    ? selectedPreview.url.replace(/\/$/, '') + route
    : '';

  const refreshPreview = useCallback(() => {
    setIframeKey((prev) => prev + 1);
  }, []);

  const openInNewTab = useCallback(() => {
    if (iframeSrc) {
      window.open(iframeSrc, '_blank');
    }
  }, [iframeSrc]);

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center bg-[#101012]">
        <div className="text-center max-w-md px-4">
          <div className="w-16 h-16 rounded-full bg-[#161618] border border-[#313133] flex items-center justify-center mx-auto mb-6">
            <Server className="w-8 h-8 text-[#4f4f57] animate-pulse" />
          </div>
          <h3 className="text-lg font-medium text-[#f3f6f6] mb-3">
            Starting preview server...
          </h3>
          <p className="text-sm text-[#969798]">
            This process should take a few moments while we&apos;re setting up
            the web container and starting the dev server.
          </p>
        </div>
      </div>
    );
  }

  if (!previews.length) {
    return (
      <div className="h-full flex items-center justify-center bg-[#101012]">
        <div className="text-center max-w-md px-4">
          <div className="inline-flex items-center justify-center p-3 bg-[#161618] rounded-full mb-4 border border-[#313133]">
            <OctagonAlert className="w-6 h-6 text-red-500" />
          </div>
          <h3 className="text-lg font-medium text-[#f3f6f6] mb-2">
            Preview server failed to start
          </h3>
          <p className="text-sm text-[#969798]">
            The development server couldn&apos;t be started. Please check the
            terminal for error messages or try refreshing the page.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-[#101012]">
      {/* Chrome-like address bar */}
      <div className="bg-[#161618] border-b border-[#313133] p-2 space-y-2">
        <div className="flex items-center gap-2">
          <button
            className="p-1.5 rounded hover:bg-[#2a2a2c] text-[#969798] hover:text-[#f3f6f6] transition-colors"
            onClick={refreshPreview}
            aria-label="Refresh"
          >
            <RotateCw className="w-4 h-4" />
          </button>

          {/* URL bar with flexible width */}
          <div className="flex-1 flex items-center gap-1 bg-[#212122] border border-[#313133] rounded-lg px-3 py-1.5 focus-within:ring-1 focus-within:ring-[#464649] group">
            {/* Port selector inside URL bar */}
            <DropdownMenu>
              <DropdownMenuTrigger className="flex items-center gap-1 text-[#969798] hover:text-[#f3f6f6] pr-2 border-r border-[#313133] focus:outline-none">
                <span className="text-xs">
                  {selectedPort ||
                    (previews.length > 0 ? previews[0].port : 'Port')}
                </span>
                <ChevronDown className="w-3 h-3" />
              </DropdownMenuTrigger>
              <DropdownMenuContent
                className="bg-[#212122] border-[#313133] text-[#f3f6f6] rounded-md shadow-md"
                align="start"
              >
                <div className="px-2 py-1.5 text-xs font-semibold text-[#969798] border-b border-[#313133] mb-1">
                  Ports
                </div>
                {previews.map((p) => (
                  <DropdownMenuItem
                    key={p.port}
                    className={cn(
                      'text-sm cursor-pointer focus:bg-[#2a2a2c] focus:text-[#f3f6f6]',
                      p.port === selectedPort
                        ? 'text-[#f3f6f6] bg-[#2a2a2c]'
                        : 'text-[#969798]'
                    )}
                    onClick={() => setSelectedPort(p.port)}
                  >
                    {p.port}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
            <input
              className="flex-1 bg-transparent border-none outline-none text-sm text-[#f3f6f6] placeholder-[#969798]"
              value={route}
              onChange={(e) =>
                setRoute(
                  e.target.value.startsWith('/')
                    ? e.target.value
                    : '/' + e.target.value
                )
              }
              placeholder="/"
            />
          </div>

          <button
            className="p-1.5 rounded hover:bg-[#2a2a2c] text-[#969798] hover:text-[#f3f6f6] transition-colors"
            onClick={openInNewTab}
            aria-label="Open in new tab"
          >
            <ExternalLink className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Content area */}
      <div className="flex-1 bg-white">
        <iframe
          key={`${iframeSrc}-${iframeKey}`}
          src={iframeSrc}
          className="w-full h-full border-0 bg-[#101012]"
          title="WebContainer Preview"
          sandbox="allow-scripts allow-same-origin allow-forms allow-modals allow-popups"
        />
      </div>
    </div>
  );
};

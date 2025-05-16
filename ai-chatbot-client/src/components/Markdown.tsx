'use client';

import React, { memo, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { createHighlighter, type BundledLanguage } from 'shiki';
import { Loader2, Copy, Check, Terminal, FileCode } from 'lucide-react';
import { cn } from '@/lib/utils';

interface MarkdownProps {
  content: string;
  isStreaming?: boolean;
  activeFile?: string | null;
  completedFiles?: Set<string>;
  activeCommand?: string | null;
  completedCommands?: Set<string>;
}

// Code highlighting component with proper syntax highlighting
const CodeHighlighter = memo(
  ({
    code,
    language,
    isBash,
  }: {
    code: string;
    language: string;
    isBash: boolean;
  }) => {
    const [highlightedCode, setHighlightedCode] = React.useState<string>('');
    const [isCopied, setIsCopied] = React.useState(false);

    useEffect(() => {
      async function highlight() {
        try {
          // Initialize highlighter with specific languages only when needed
          const highlighter = await createHighlighter({
            themes: ['github-dark'],
            langs: [(language as BundledLanguage) || 'plaintext'],
          });

          const html = highlighter.codeToHtml(code, {
            lang: language || 'plaintext',
            theme: 'github-dark',
          });

          setHighlightedCode(html);
        } catch (error) {
          console.error('Highlighting error:', error);
          // Safe fallback if highlighting fails
          setHighlightedCode(
            `<pre class="shiki" style="background-color:#0d1117;color:#e6edf3"><code>${code
              .replace(/</g, '&lt;')
              .replace(/>/g, '&gt;')}</code></pre>`
          );
        }
      }

      highlight();
    }, [code, language]);

    const handleCopy = () => {
      navigator.clipboard.writeText(code);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    };

    return (
      <div className="relative group my-3 rounded-lg overflow-hidden bg-[#161618] shadow-sm border border-[#313133]">
        {/* Language header bar for bash */}
        {isBash && (
          <div className="flex items-center justify-between px-3 py-1.5 bg-[#101012] border-b border-[#2e2e32]">
            <div className="flex items-center gap-2 text-xs text-[#969696]">
              <Terminal className="w-3.5 h-3.5" />
              <span>bash</span>
            </div>
            <button
              onClick={handleCopy}
              className="flex items-center justify-center h-6 w-6 rounded bg-[#313133]/50 text-[#969696] hover:text-[#f3f6f6] hover:bg-[#313133] transition-colors"
              aria-label="Copy command"
            >
              {isCopied ? (
                <Check className="w-3.5 h-3.5" />
              ) : (
                <Copy className="w-3.5 h-3.5" />
              )}
            </button>
          </div>
        )}

        {/* Copy button for non-bash */}
        {!isBash && (
          <div className="absolute top-2 right-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={handleCopy}
              className="flex items-center justify-center h-7 w-7 rounded bg-[#313133]/70 text-[#969696] hover:text-[#f3f6f6] hover:bg-[#313133]"
              aria-label="Copy code"
            >
              {isCopied ? (
                <Check className="w-4 h-4" />
              ) : (
                <Copy className="w-4 h-4" />
              )}
            </button>
          </div>
        )}

        {/* Language badge for non-bash code */}
        {!isBash && language !== 'plaintext' && (
          <div className="absolute top-2 left-2 px-1.5 py-0.5 text-xs rounded bg-[#3e3e3e]/70 text-[#969696] opacity-0 group-hover:opacity-100 transition-opacity">
            {language}
          </div>
        )}

        {/* Code content */}
        <div
          className={cn(
            'shiki-container text-sm overflow-x-auto break-words whitespace-pre-wrap',
            isBash ? 'p-3' : 'p-4'
          )}
          dangerouslySetInnerHTML={{ __html: highlightedCode }}
        />
      </div>
    );
  }
);
CodeHighlighter.displayName = 'CodeHighlighter';

// Bash Command Component - specialized for bash/shell commands
const BashCommand = memo(({ command }: { command: string }) => {
  const [isCopied, setIsCopied] = React.useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(command);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };

  return (
    <div className="relative group my-3 rounded-lg overflow-hidden bg-[#161618] shadow-sm border border-[#313133]">
      <div className="flex items-center justify-between px-3 py-1.5 bg-[#101012] border-b border-[#2e2e32]">
        <div className="flex items-center gap-2 text-xs text-[#969696]">
          <Terminal className="w-3.5 h-3.5" />
          <span>bash</span>
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center justify-center h-6 w-6 rounded bg-[#313133]/50 text-[#969696] hover:text-[#f3f6f6] hover:bg-[#313133] transition-colors"
          aria-label="Copy command"
        >
          {isCopied ? (
            <Check className="w-3.5 h-3.5" />
          ) : (
            <Copy className="w-3.5 h-3.5" />
          )}
        </button>
      </div>
      <div className="p-3 font-mono text-sm overflow-x-auto text-[#e6edf3] break-words whitespace-pre-wrap overflow-wrap-anywhere">
        {command}
      </div>
    </div>
  );
});
BashCommand.displayName = 'BashCommand';

// Inline code component for simpler styling
const InlineCode = memo(({ children }: { children: React.ReactNode }) => (
  <code className="inline text-[#f3f6f6] font-mono break-words whitespace-pre-wrap overflow-wrap-anywhere px-1 py-0.5 text-[0.9em] rounded bg-[#161618] border border-[#313133]">
    {children}
  </code>
));
InlineCode.displayName = 'InlineCode';

// File Updates Panel Component
const FileUpdatesPanel = memo(
  ({
    activeFile,
    completedFiles,
    activeCommand,
    completedCommands,
  }: {
    activeFile?: string | null;
    completedFiles?: Set<string>;
    activeCommand?: string | null;
    completedCommands?: Set<string>;
  }) => {
    const completedFilesArray = completedFiles
      ? Array.from(completedFiles)
      : [];
    const completedCommandsArray = completedCommands
      ? Array.from(completedCommands)
      : [];

    if (
      !activeFile &&
      completedFilesArray.length === 0 &&
      !activeCommand &&
      completedCommandsArray.length === 0
    ) {
      return null;
    }

    return (
      <div className="mb-4 border border-[#313133] overflow-hidden rounded-lg w-full shadow-sm">
        <div className="p-3 bg-[#161618] text-[#f3f6f6] font-medium border-b border-[#313133]">
          {activeCommand || completedCommandsArray.length > 0
            ? 'File & Command Updates'
            : 'File Updates'}
        </div>
        <div className="p-3 bg-[#161618] space-y-2">
          {completedFilesArray.map((filePath) => (
            <div
              key={`file-${filePath}`}
              className="flex items-center text-sm bg-[#101012] py-1.5 px-3 rounded-md border border-[#313133]"
            >
              <Check className="h-4 w-4 mr-2 text-blue-400 flex-shrink-0" />
              <span className="text-[#f3f6f6] break-all">
                Updated{' '}
                <span className="text-blue-400 font-mono">{filePath}</span>
              </span>
            </div>
          ))}
          {activeFile && (
            <div
              key={`file-updating-${activeFile}`}
              className="flex items-center text-sm bg-[#101012] py-1.5 px-3 rounded-md border border-[#313133]"
            >
              <Loader2 className="h-4 w-4 mr-2 text-blue-400 animate-spin flex-shrink-0" />
              <span className="text-[#f3f6f6] break-all">
                Updating{' '}
                <span className="text-blue-400 font-mono">{activeFile}</span>
              </span>
            </div>
          )}

          {/* Command updates */}
          {completedCommandsArray.map((command) => (
            <div
              key={`cmd-${command}`}
              className="flex items-center text-sm bg-[#101012] py-1.5 px-3 rounded-md border border-[#313133]"
            >
              <Terminal className="h-4 w-4 mr-2 text-blue-400 flex-shrink-0" />
              <span className="text-[#f3f6f6] break-all">
                Ran <span className="text-blue-400 font-mono">{command}</span>
              </span>
            </div>
          ))}
          {activeCommand && (
            <div
              key={`cmd-running-${activeCommand}`}
              className="flex items-center text-sm bg-[#101012] py-1.5 px-3 rounded-md border border-[#313133]"
            >
              <Loader2 className="h-4 w-4 mr-2 text-blue-400 animate-spin flex-shrink-0" />
              <span className="text-[#f3f6f6] break-all">
                Running{' '}
                <span className="text-blue-400 font-mono">{activeCommand}</span>
              </span>
            </div>
          )}
        </div>
      </div>
    );
  }
);
FileUpdatesPanel.displayName = 'FileUpdatesPanel';

// Artifact Title Component
const ArtifactTitle = memo(({ title }: { title: string }) => {
  return (
    <div className="mb-3 bg-[#161618] p-3 rounded-lg border border-[#313133] shadow-sm not-prose">
      <div className="flex items-center gap-2 text-[#f3f6f6] font-medium">
        <FileCode className="h-4 w-4" />
        <span>{title}</span>
      </div>
    </div>
  );
});
ArtifactTitle.displayName = 'ArtifactTitle';

// Function to detect if text contains a curl or npm/npx command
const isBashCommand = (text: string): boolean => {
  const normalizedText = text.trim();
  return (
    normalizedText.startsWith('curl ') ||
    normalizedText.startsWith('npm ') ||
    normalizedText.startsWith('npx ') ||
    normalizedText.startsWith('yarn ') ||
    normalizedText.startsWith('pnpm ') ||
    normalizedText.startsWith('node ') ||
    normalizedText.match(/^(git|ssh|http|https):\/\/[^\s]+/) !== null
  );
};

// Main Markdown Component
export const Markdown = memo(
  ({
    content,
    // isStreaming,
    activeFile,
    completedFiles,
    activeCommand,
    completedCommands,
  }: MarkdownProps) => {
    const containerRef = useRef<HTMLDivElement>(null);

    // Improved preprocessing for bolt content
    const processContent = (content: string) => {
      // Extract artifact title before we filter out the boltArtifact tags
      const artifactTitleMatch = content.match(
        /<boltArtifact\s+title="([^"]+)"[^>]*>/
      );
      const artifactTitle = artifactTitleMatch ? artifactTitleMatch[1] : null;

      // Filter out boltArtifact and boltAction tags AND their content completely
      // This regex pattern matches the entire boltArtifact/boltAction blocks including their content
      // The code inside these blocks will be streamed to the editor instead of displayed in the chat
      let cleanedContent = content
        .replace(/<boltArtifact[^>]*>[\s\S]*?<\/boltArtifact>/g, '')
        .replace(/<boltAction[^>]*>[\s\S]*?<\/boltAction>/g, '');

      // Trim any empty lines or excessive whitespace that might remain
      cleanedContent = cleanedContent.trim();

      return { artifactTitle, cleanedContent };
    };

    const { artifactTitle, cleanedContent } = processContent(content);

    return (
      <div
        ref={containerRef}
        className="markdown-content prose prose-invert prose-sm max-w-none text-[#f3f6f6] break-words overflow-hidden w-full"
      >
        {artifactTitle && <ArtifactTitle title={artifactTitle} />}
        <FileUpdatesPanel
          activeFile={activeFile}
          completedFiles={completedFiles}
          activeCommand={activeCommand}
          completedCommands={completedCommands}
        />

        <div className="break-words overflow-wrap-anywhere whitespace-pre-wrap">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              // The key here is to individually define each component without the inline property issue
              code: ({ className, children, ...rest }) => {
                console.log('...rest', rest);
                const codeStr = String(children).replace(/\n$/, '');

                // Detect if the code block is inline based on classname presence
                const isInlineCode = !className;

                if (isInlineCode) {
                  // Check if this is a potential bash command first
                  if (isBashCommand(codeStr)) {
                    return <BashCommand command={codeStr} />;
                  }
                  return <InlineCode>{children}</InlineCode>;
                }

                // Handle full code blocks with language detection
                const lang = className
                  ? className.replace('language-', '')
                  : 'plaintext';
                const isBash = lang === 'bash' || lang === 'sh';

                // For bash single-line commands, use simpler renderer
                if (
                  isBash &&
                  !codeStr.includes('\n') &&
                  isBashCommand(codeStr)
                ) {
                  return <BashCommand command={codeStr} />;
                }

                return (
                  <CodeHighlighter
                    code={codeStr}
                    language={lang}
                    isBash={isBash}
                  />
                );
              },

              p: ({ children, ...rest }) => {
                // Check if paragraph has actual content
                const textContent = React.Children.toArray(children)
                  .map((child) => (typeof child === 'string' ? child : ''))
                  .join('')
                  .trim();

                if (!textContent) return null;

                // Check if the paragraph is actually a bash command
                if (isBashCommand(textContent) && !textContent.includes('\n')) {
                  return <BashCommand command={textContent} />;
                }

                return (
                  <p className="mb-2 last:mb-0" {...rest}>
                    {children}
                  </p>
                );
              },

              h1: (props) => (
                <h1
                  className="text-2xl font-semibold mt-4 mb-2 pb-1 border-b border-[#313133]"
                  {...props}
                />
              ),
              h2: (props) => (
                <h2
                  className="text-xl font-semibold mt-4 mb-2 pb-1 border-b border-[#313133]"
                  {...props}
                />
              ),
              h3: (props) => (
                <h3 className="text-lg font-semibold mt-3 mb-2" {...props} />
              ),
              h4: (props) => (
                <h4 className="text-base font-semibold mt-3 mb-2" {...props} />
              ),

              ul: (props) => (
                <ul
                  className="list-disc list-outside pl-5 space-y-1 my-2"
                  {...props}
                />
              ),
              ol: (props) => (
                <ol
                  className="list-decimal list-outside pl-5 space-y-1 my-2"
                  {...props}
                />
              ),
              li: (props) => <li className="pl-1" {...props} />,

              blockquote: (props) => (
                <blockquote
                  className="pl-4 border-l-2 border-[#3e3e3e] text-[#c0c2c3] my-3 italic"
                  {...props}
                />
              ),

              a: (props) => (
                <a
                  className="text-blue-400 hover:underline"
                  target="_blank"
                  rel="noopener noreferrer"
                  {...props}
                />
              ),

              hr: () => <hr className="my-4 border-t border-[#313133]" />,
            }}
          >
            {cleanedContent}
          </ReactMarkdown>
        </div>
      </div>
    );
  }
);

Markdown.displayName = 'Markdown';

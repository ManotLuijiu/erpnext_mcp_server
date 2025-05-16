import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sparkles, Paperclip, ArrowUp, MessageSquare } from 'lucide-react';
import { STARTER_TEMPLATES, DEFAULT_TEMPLATE } from '@/lib/constants';
import { Icons } from '@/components/ui/icons';
import { usePromptEnhancer } from '@/hooks/usePromptEnhancer';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

const HomePage = () => {
  const navigate = useNavigate();
  const [prompt, setPrompt] = useState('');
  const { enhancePrompt, enhancingPrompt } = usePromptEnhancer();
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = (e: any) => {
    e.preventDefault();

    if (prompt.trim()) {
      // Use the default template when user submits a prompt
      navigate(
        `/${DEFAULT_TEMPLATE.name}?prompt=${encodeURIComponent(prompt)}`
      );
    }
  };

  // Auto-resize the textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    console.log('textarea', textarea);
    if (!textarea) return;

    // Reset height to auto to get the correct scrollHeight
    textarea.style.height = 'auto';

    // Set new height based on content (with a min of 44px)
    const newHeight = Math.max(44, Math.min(textarea.scrollHeight, 250));
    textarea.style.height = `${newHeight}px`;
  }, [prompt]);

  const examplePrompts = [
    'A todo app with React and TypeScript',
    'E-commerce dashboard with React',
    'Blog with React and Tailwind',
    'Chat app with React and Firebase',
    'Job board with Express and MongoDB',
  ];
  return (
    <div className="min-h-screen bg-[#101012] text-white">
      <div className="max-w-4xl mx-auto px-6 py-16 flex flex-col gap-12">
        {/* Header */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Badge className="bg-blue-500/10 text-blue-400 hover:bg-blue-500/20 border-0">
              Beta
            </Badge>
          </div>
          <h1 className="text-3xl font-medium tracking-tight">Welcome back</h1>
          <p className="text-gray-400 text-lg">Prototype an app with AI</p>
        </div>

        {/* Main prompt area */}
        <div className="w-full">
          <form onSubmit={handleSubmit}>
            <div className="border border-[#313133] rounded-xl bg-[#161618] overflow-hidden shadow-sm">
              <div className="p-3 relative">
                <Textarea
                  ref={textareaRef}
                  placeholder="An app that helps me plan my day"
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  className="min-h-[56px] max-h-[250px] resize-none border-0 p-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 placeholder:text-gray-500 text-sm pr-12 overflow-y-auto"
                  translate="no"
                  style={{
                    transition: 'height 0.1s ease',
                  }}
                />
                {prompt.length > 6 && (
                  <div className="absolute top-3 right-3">
                    <Button
                      type="submit"
                      size="icon"
                      className="h-10 w-10 rounded-full bg-blue-500 hover:bg-blue-600"
                    >
                      <ArrowUp className="w-10 h-10 text-[#101012]" />
                    </Button>
                  </div>
                )}
              </div>
              <div className="flex justify-start p-3">
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    className="text-gray-400 hover:text-gray-300 transition-colors"
                    aria-label="Upload files"
                  >
                    <Paperclip className="w-4 h-4" />
                  </button>
                  <button
                    type="button"
                    className="text-gray-400 hover:text-gray-300 transition-colors cursor-pointer"
                    onClick={() =>
                      enhancePrompt(prompt, setPrompt, 'gpt-4o', {
                        name: 'OpenAI',
                        apiKey: import.meta.env.VITE_OPENAI_API_KEY,
                      })
                    }
                    disabled={enhancingPrompt || prompt.length === 0}
                  >
                    <Icons.sparkles
                      className={`w-4 h-4 ${enhancingPrompt ? 'animate-pulse' : ''}`}
                    />
                  </button>
                </div>
              </div>
            </div>
          </form>
        </div>

        {/* Example Prompts */}
        <div className="space-y-3">
          <div className="text-sm text-gray-400">Try building</div>
          <div className="flex flex-wrap gap-2">
            {examplePrompts.map((example, index) => (
              <button
                key={index}
                className="px-3 py-1.5 text-sm bg-[#161618] border border-[#313133] rounded-full hover:bg-[#1e1e20] transition-colors"
                onClick={() => setPrompt(example)}
              >
                {example}
              </button>
            ))}
          </div>
        </div>

        {/* Start coding section */}
        <div className="space-y-6">
          <h2 className="text-lg font-medium">
            Or start a blank app with your favorite stack
          </h2>

          <div className="flex items-center space-x-6 overflow-x-auto pb-2">
            <div className="flex items-center gap-6">
              {STARTER_TEMPLATES.map((template) => (
                <a
                  key={template.name}
                  href={`/${template.name}`}
                  className="flex flex-col items-center gap-2 group"
                  aria-label={template.label}
                >
                  <div className="w-8 h-8 flex items-center justify-center opacity-70 group-hover:opacity-100 transition-opacity">
                    {Icons[template.icon as keyof typeof Icons]({
                      className: 'w-8 h-8',
                      style: { maskType: 'alpha' },
                    })}
                  </div>
                </a>
              ))}
            </div>
          </div>
        </div>

        {/* Recently used area */}
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-medium">Your chats</h2>
            <div className="text-sm text-gray-400 cursor-pointer hover:text-white transition-colors">
              View all
            </div>
          </div>

          <div className="space-y-1">
            {/* Empty state or would show recent projects */}
            <div className="border border-[#313133] rounded-lg bg-[#161618] p-4 flex items-center justify-between group hover:bg-[#1a1a1c] transition-colors">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-blue-500/20 rounded-full flex items-center justify-center">
                  <MessageSquare className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-sm font-medium">React App</div>
                  <div className="text-xs text-gray-500">
                    Last edited 2 days ago
                  </div>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="opacity-0 group-hover:opacity-100"
              >
                Open
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HomePage;

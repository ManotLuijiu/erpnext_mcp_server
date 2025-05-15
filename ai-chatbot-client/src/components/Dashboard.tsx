import React, { useState, useRef, useEffect } from 'react';
import type { FormEvent } from 'react';
import { useFrappeCreateDoc, useFrappeGetCall } from 'frappe-react-sdk';
import {
  Sparkles,
  Paperclip,
  ArrowUp,
  MessageSquare,
  Terminal,
  History,
  Send,
} from 'lucide-react';
import { Textarea } from '@/components/ui/textarea';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { toast } from 'sonner';
import { ScrollArea } from '@/components/ui/scroll-area';

type CommandHistory = {
  command: string;
  timestamp: string;
  success: boolean;
};

const Dashboard = () => {
  const [prompt, setPrompt] = useState('');
  const [commandHistory, setCommandHistory] = useState<CommandHistory[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Fetch command history
  const { data, error, isLoading, mutate } = useFrappeGetCall<{
    message: CommandHistory[];
  }>('erpnext_mcp_server.mcp.bridge.get_command_history', {});

  useEffect(() => {
    if (data && data.message) {
      setCommandHistory(data.message);
    }
  }, [data]);

  // Process commands
  const { createDoc, loading: submitting } = useFrappeCreateDoc();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    if (!prompt.trim() || isProcessing) return;

    setIsProcessing(true);

    try {
      const response = await window.frappe.call({
        method: 'erpnext_mcp_server.mcp.bridge.process_command',
        args: { command: prompt },
      });

      if (response.message) {
        toast({
          title: 'Command executed',
          description: 'Command was processed successfully',
        });

        // Refresh command history
        mutate();
      }

      // Clear the prompt
      setPrompt('');
    } catch (error) {
      console.error('Error processing command:', error);
      toast({
        title: 'Error',
        description: 'Failed to process command',
        variant: 'destructive',
      });
    } finally {
      setIsProcessing(false);
    }
  };

  // Auto-resize the textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    // Reset height to auto to get the correct scrollHeight
    textarea.style.height = 'auto';

    // Set new height based on content (with a min of 44px)
    const newHeight = Math.max(44, Math.min(textarea.scrollHeight, 250));
    textarea.style.height = `${newHeight}px`;
  }, [prompt]);

  const exampleCommands = [
    'Show help',
    'List all files',
    'Display system info',
    'Show active users',
    'Check network status',
  ];

  const handleCommandClick = (command: string) => {
    setPrompt(command);
    // Focus the textarea
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  };

  const handleRerunCommand = (command: string) => {
    setPrompt(command);
    // Submit the form immediately
    setTimeout(() => {
      if (textareaRef.current?.form) {
        textareaRef.current.form.dispatchEvent(
          new Event('submit', { cancelable: true, bubbles: true })
        );
      }
    }, 100);
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <div className="container mx-auto px-4 py-8 flex-1 flex flex-col gap-6">
        {/* Header */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className="bg-primary/10 text-primary">
              <Terminal className="w-3 h-3 mr-1" />
              MCP Terminal
            </Badge>
          </div>
          <h1 className="text-3xl font-semibold tracking-tight">
            Model Context Protocol Terminal
          </h1>
          <p className="text-muted-foreground">
            Interact with your MCP Server through natural language or commands
          </p>
          <Separator className="my-4" />
        </div>

        {/* Main prompt area */}
        <Card className="border-border">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">Enter a command</CardTitle>
            <CardDescription>Type your command or query below</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-2">
              <div className="relative">
                <Textarea
                  ref={textareaRef}
                  placeholder="Enter a command or query..."
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  className="min-h-[56px] max-h-[250px] pr-12 resize-none"
                  disabled={isProcessing}
                  style={{ transition: 'height 0.1s ease' }}
                />
                {prompt.length > 0 && (
                  <Button
                    type="submit"
                    size="icon"
                    disabled={isProcessing}
                    className="absolute right-2 bottom-2 h-8 w-8"
                  >
                    {isProcessing ? (
                      <div className="animate-spin h-4 w-4 border-2 border-current border-t-transparent rounded-full" />
                    ) : (
                      <Send className="h-4 w-4" />
                    )}
                  </Button>
                )}
              </div>
              <div className="flex justify-start pt-2">
                <div className="flex items-center gap-3">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="text-muted-foreground"
                    aria-label="Upload files"
                    disabled={isProcessing}
                  >
                    <Paperclip className="w-4 h-4 mr-2" />
                    Attach
                  </Button>
                  <Separator orientation="vertical" className="h-6" />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="text-muted-foreground"
                    onClick={() =>
                      toast({
                        title: 'Enhanced',
                        description: 'Command enhanced with AI',
                      })
                    }
                    disabled={isProcessing || prompt.length === 0}
                  >
                    <Sparkles className="w-4 h-4 mr-2" />
                    Enhance
                  </Button>
                </div>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* Example Commands */}
        <div className="space-y-3">
          <h2 className="text-sm font-medium text-muted-foreground">
            Try these commands
          </h2>
          <div className="flex flex-wrap gap-2">
            {exampleCommands.map((command, index) => (
              <Button
                key={index}
                variant="outline"
                size="sm"
                className="rounded-full"
                onClick={() => handleCommandClick(command)}
                disabled={isProcessing}
              >
                {command}
              </Button>
            ))}
          </div>
        </div>

        {/* Command History */}
        <div className="space-y-4 flex-1">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold">Command History</h2>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => mutate()}
              disabled={isLoading}
            >
              <History className="w-4 h-4 mr-2" />
              Refresh
            </Button>
          </div>

          <ScrollArea className="h-[300px] rounded-md border">
            {isLoading ? (
              <div className="p-4 text-center text-muted-foreground">
                Loading history...
              </div>
            ) : commandHistory.length === 0 ? (
              <div className="p-4 text-center text-muted-foreground">
                No command history yet
              </div>
            ) : (
              <div className="space-y-1 p-2">
                {commandHistory.map((item, index) => (
                  <Card key={index} className="group">
                    <CardHeader className="p-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div
                            className={`w-8 h-8 rounded-full flex items-center justify-center ${
                              item.success ? 'bg-green-500/20' : 'bg-red-500/20'
                            }`}
                          >
                            <Terminal className="w-4 h-4" />
                          </div>
                          <div>
                            <div className="text-sm font-medium">
                              {item.command}
                            </div>
                            <div className="text-xs text-muted-foreground">
                              {item.timestamp}
                            </div>
                          </div>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="opacity-0 group-hover:opacity-100 transition-opacity"
                          onClick={() => handleRerunCommand(item.command)}
                        >
                          Run again
                        </Button>
                      </div>
                    </CardHeader>
                  </Card>
                ))}
              </div>
            )}
          </ScrollArea>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;

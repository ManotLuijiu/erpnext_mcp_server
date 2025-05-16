import { type Template } from '@/types';
// ai-chatbot-client/src/types/index.ts

export const OPENROUTER_API_URL =
  'https://openrouter.ai/api/v1/chat/completions';
// export const DEFAULT_MODEL = 'google/gemini-2.5-pro-preview-03-25';
export const DEFAULT_MODEL = 'openai/gpt-4.1';

export const SECONDARY_MODEL = 'google/gemini-2.0-flash-001';
export const GITHUB_REPO_URL =
  'https://github.com/thecodacus/bolt-nextjs-shadcn-template.git';
export const GITHUB_API_BASE_URL = 'https://api.github.com';
export const MAX_TOKENS_NO_SUMMARY = 8000; // Maximum tokens before requiring chat summary
export const IGNORE_PATTERNS = [
  'node_modules/**',
  '.git/**',
  'dist/**',
  'build/**',
  '.next/**',
  'coverage/**',
  '.cache/**',
  '.vscode/**',
  '.idea/**',
  '**/*.log',
  '**/.DS_Store',
  '**/npm-debug.log*',
  '**/yarn-debug.log*',
  '**/yarn-error.log*',
  '**/*lock.json',
  '**/*lock.yml',
];

export const STARTER_TEMPLATES: Template[] = [
  {
    name: 'bolt-nextjs-shadcn',
    label: 'Next.js with shadcn/ui',
    description:
      'Next.js starter fullstack template integrated with shadcn/ui components and styling system',
    githubRepo: 'https://github.com/thecodacus/bolt-nextjs-shadcn-template.git',
    tags: ['nextjs', 'react', 'typescript', 'shadcn', 'tailwind'],
    icon: 'next',
  },
  {
    name: 'bolt-sveltekit',
    label: 'SvelteKit',
    description:
      'SvelteKit starter template for building fast, efficient web applications',
    githubRepo: 'https://github.com/thecodacus/bolt-sveltekit-template.git',
    tags: ['svelte', 'sveltekit', 'typescript'],
    icon: 'svelte',
  },
  {
    name: 'bolt-vite-react',
    label: 'React + Vite + typescript',
    description:
      'React starter template powered by Vite for fast development experience',
    githubRepo: 'https://github.com/thecodacus/bolt-vite-react-ts-template.git',
    tags: ['react', 'vite', 'frontend'],
    icon: 'react',
  },
  {
    name: 'bolt-vite-ts',
    label: 'Vite + TypeScript',
    description:
      'Vite starter template with TypeScript configuration for type-safe development',
    githubRepo: 'https://github.com/thecodacus/bolt-vite-ts-template.git',
    tags: ['vite', 'typescript', 'minimal'],
    icon: 'typescript',
  },
  {
    name: 'bolt-vue',
    label: 'Vue.js',
    description:
      'Vue.js starter template with modern tooling and best practices',
    githubRepo: 'https://github.com/thecodacus/bolt-vue-template.git',
    tags: ['vue', 'typescript', 'frontend'],
    icon: 'vue',
  },
  {
    name: 'vanilla-vite',
    label: 'Vanilla + Vite',
    description:
      'Minimal Vite starter template for vanilla JavaScript projects',
    githubRepo: 'https://github.com/thecodacus/vanilla-vite-template.git',
    tags: ['vite', 'vanilla-js', 'minimal'],
    icon: 'vite',
  },
  {
    name: 'bolt-astro-basic',
    label: 'Astro Basic',
    description:
      'Lightweight Astro starter template for building fast static websites',
    githubRepo: 'https://github.com/thecodacus/bolt-astro-basic-template.git',
    tags: ['astro', 'blog', 'performance'],
    icon: 'astro',
  },
];

// Default template when user enters prompt without selecting a template
export const DEFAULT_TEMPLATE =
  STARTER_TEMPLATES.find((t) => t.name === 'bolt-nextjs-shadcn') ||
  STARTER_TEMPLATES[0];

// Maximum time in milliseconds to wait for a terminal command to complete
export const MAX_TERMINAL_EXECUTION_TIME = 15000; // 15 seconds

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import './assets/fonts/fonts.css';
import './index.css';
import App from './App.tsx';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TranslationProvider } from './context/TranslationContext.tsx';
import { NuqsAdapter } from 'nuqs/adapters/react';

const queryClient = new QueryClient();

if (import.meta.env.DEV) {
  fetch(
    '/api/method/erpnext_mcp_server.www.ai_chatbot_client.get_context_for_dev',
    {
      method: 'POST',
    }
  )
    .then((response) => response.json())
    .then((values) => {
      const v = JSON.parse(values.message);
      // if (!window.frappe) window.frappe = {};
      if (!window.frappe) {
        window.frappe = {
          __: (text: string) => text, // Provide a default implementation for the __ function
          show_alert: (message: string) => alert(message), // Provide a default implementation for show_alert
        };
      }
      window.frappe.boot = v;
    });
}

const rootElement = document.getElementById('root');
if (rootElement) {
  createRoot(rootElement).render(
    <StrictMode>
      <BrowserRouter>
        <NuqsAdapter>
          <QueryClientProvider client={queryClient}>
            <TranslationProvider>
              <App />
            </TranslationProvider>
          </QueryClientProvider>
        </NuqsAdapter>
      </BrowserRouter>
    </StrictMode>
  );
}

// createRoot(document.getElementById('root')!).render(
//   <StrictMode>
//     <BrowserRouter>
//       <NuqsAdapter>
//         <App />
//       </NuqsAdapter>
//     </BrowserRouter>
//   </StrictMode>
// );

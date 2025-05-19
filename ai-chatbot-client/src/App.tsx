// import React from 'react';
import { FrappeProvider } from 'frappe-react-sdk';
import { Toaster } from '@/components/ui/sonner';
import { AppProvider } from './context/AppProvider';
// import Dashboard from './components/Dashboard';
import { Routes, Route } from 'react-router-dom';
import Workspace from './pages/Workspace';
import HomePage from './pages/HomePage';
import Terminal from './components/Terminal2';
import { useTheme } from './hooks/useTheme';
import { ThemeProvider } from '@/components/ThemeProvider';
import { ErrorBoundary } from '@/components/ErrorBoundary';

function App() {
  const theme = useTheme();
  console.log('theme erpnext_mcp_server', theme);
  return (
    <FrappeProvider
      siteName={import.meta.env.VITE_SITE_NAME}
      socketPort={import.meta.env.VITE_SOCKET_PORT}
    >
      <ErrorBoundary fallback={<p>Opps! Something broke.</p>}>
        <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
          <AppProvider>
            {/* <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/:id" element={<Workspace />} />
        </Routes> */}
            <div className="frappe-page">
              <div className="page-head flex justify-between">
                <div>
                  <h1 className="page-title">MCP Terminal</h1>
                  <p className="text-muted text-sm">
                    Terminal interface for ERPNext MCP Server
                  </p>
                </div>
              </div>
              <div className="page-body">
                <div className="card">
                  <div className="card-body p-0">
                    <Terminal />
                  </div>
                </div>
              </div>
              <Toaster richColors position="bottom-right" />
            </div>
          </AppProvider>
        </ThemeProvider>
      </ErrorBoundary>
    </FrappeProvider>
  );
}

export default App;

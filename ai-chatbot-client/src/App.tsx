import { FrappeProvider } from 'frappe-react-sdk';
import { Toaster } from '@/components/ui/sonner';
import { AppProvider } from './context/AppProvider';
// import { useTheme } from './hooks/useTheme';
import { ThemeProvider } from '@/components/ThemeProvider';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import Sidebar from './components/playground/Sidebar';
import { ChatArea } from './components/playground/ChatArea';

function App() {
  // const theme = useTheme();
  // console.log('theme erpnext_mcp_server', theme);
  return (
    <FrappeProvider
      siteName={import.meta.env.VITE_SITE_NAME}
      socketPort={import.meta.env.VITE_SOCKET_PORT}
    >
      <ErrorBoundary fallback={<p>__(Opps! Something broke.)</p>}>
        <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
          <AppProvider>
            <div className="flex h-screen bg-background/80">
              <Sidebar />
              <ChatArea />
              <Toaster richColors position="bottom-right" />
            </div>
          </AppProvider>
        </ThemeProvider>
      </ErrorBoundary>
    </FrappeProvider>
  );
}

export default App;

import React from 'react';
import { FrappeProvider } from 'frappe-react-sdk';
import { Toaster } from '@/components/ui/sonner';
import Dashboard from './components/Dashboard';
function App() {
  return (
    <div className="App">
      <FrappeProvider>
        <div>
          <Dashboard />
        </div>
        <Toaster />
      </FrappeProvider>
    </div>
  );
}

export default App;

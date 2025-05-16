// import React from 'react';
import { FrappeProvider } from 'frappe-react-sdk';
import { Toaster } from '@/components/ui/sonner';
// import Dashboard from './components/Dashboard';
import { Routes, Route } from 'react-router-dom';
import Workspace from './pages/Workspace';
import HomePage from './pages/HomePage';

function App() {
  return (
    <div className="App">
      <FrappeProvider>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/:id" element={<Workspace />} />
        </Routes>
        <Toaster />
      </FrappeProvider>
    </div>
  );
}

export default App;

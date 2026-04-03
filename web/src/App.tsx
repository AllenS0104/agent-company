import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Sidebar } from './components/Sidebar';
import { LoadingScreen } from './components/LoadingScreen';
import { WelcomePage } from './pages/WelcomePage';
import { DiscussPage } from './pages/DiscussPage';
import { HistoryPage } from './pages/HistoryPage';
import { MemoryPage } from './pages/MemoryPage';
import { AgentsPage } from './pages/AgentsPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { getConfig } from './api/client';

export default function App() {
  const [isConfigured, setIsConfigured] = useState<boolean | null>(null); // null = loading

  useEffect(() => {
    getConfig()
      .then((cfg: any) => {
        const anyConfigured = Object.values(cfg.providers || {}).some(
          (p: any) => p.configured,
        );
        setIsConfigured(anyConfigured);
      })
      .catch(() => setIsConfigured(false));
  }, []);

  if (isConfigured === null) return <LoadingScreen />;
  if (!isConfigured) return <WelcomePage onConfigured={() => setIsConfigured(true)} />;

  return (
    <BrowserRouter>
      <div className="flex h-screen bg-slate-950">
        <Sidebar />
        <main className="flex-1 overflow-hidden">
          <Routes>
            <Route path="/" element={<DiscussPage onReconfigure={() => setIsConfigured(false)} />} />
            <Route path="/agents" element={<AgentsPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/memory" element={<MemoryPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

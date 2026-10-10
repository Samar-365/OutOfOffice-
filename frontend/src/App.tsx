/**
 * OutOfOffice AI — Root Application Component
 * Flat, minimalist, professional developer UI.
 */

import React, { useState } from 'react';
import { Navbar } from './components/Navbar';
import { Dashboard } from './views/Dashboard';
import { TraceView } from './views/TraceView';
import { ResultsHub } from './views/ResultsHub';
import { Terminal } from 'lucide-react';

export const App: React.FC = () => {
  const [activeScreen, setActiveScreen] = useState<'dashboard' | 'trace' | 'results'>('dashboard');

  return (
    <div className="min-h-screen flex flex-col bg-[#0b0f12] text-slate-100 antialiased">
      <Navbar activeScreen={activeScreen} onNavigate={setActiveScreen} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeScreen === 'dashboard' && (
          <Dashboard onNavigate={setActiveScreen} />
        )}

        {activeScreen === 'trace' && (
          <TraceView onNavigate={setActiveScreen} />
        )}

        {activeScreen === 'results' && (
          <ResultsHub onNavigate={setActiveScreen} />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-[#222d35] py-4 bg-[#0b0f12]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-500 font-mono">
          <div className="flex items-center gap-2">
            <Terminal className="h-3.5 w-3.5 text-emerald-400" />
            <span>OutOfOffice AI • Local Autonomous Coding Agent</span>
          </div>
          <div>
            Powered by Google Gemma 2 • Sentry Tracing • ElevenLabs Voice
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;

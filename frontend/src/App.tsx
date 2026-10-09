import React, { useState } from 'react';
import { Navbar } from './components/Navbar';
import { Dashboard } from './views/Dashboard';
import { AwayScreen } from './views/AwayScreen';
import { TraceView } from './views/TraceView';
import { Trees } from 'lucide-react';

export const App: React.FC = () => {
  const [activeScreen, setActiveScreen] = useState<'dashboard' | 'away' | 'trace' | 'results'>('dashboard');

  return (
    <div className="min-h-screen flex flex-col bg-dark-bg text-slate-100">
      <Navbar activeScreen={activeScreen} onNavigate={setActiveScreen} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeScreen === 'dashboard' && (
          <Dashboard onNavigate={setActiveScreen} />
        )}

        {activeScreen === 'away' && (
          <AwayScreen onNavigate={setActiveScreen} />
        )}

        {activeScreen === 'trace' && (
          <TraceView onNavigate={setActiveScreen} />
        )}

        {activeScreen === 'results' && (
          <div className="glass-card p-12 text-center space-y-4 max-w-2xl mx-auto border border-forest-700/50">
            <h2 className="text-2xl font-bold text-white">Results Hub & Unified Diff (Submodule 8.6)</h2>
            <p className="text-sm text-slate-400">
              ElevenLabs audio debrief player and verified code diffs will be rendered here.
            </p>
            <button
              onClick={() => setActiveScreen('dashboard')}
              className="btn-secondary text-xs px-4 py-2"
            >
              Back to Dashboard
            </button>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-forest-900/60 py-6 bg-dark-bg/60">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500 font-mono">
          <div className="flex items-center gap-2">
            <Trees className="h-4 w-4 text-grass-neon" />
            <span>OutOfOffice AI • Built for Hacktoberfest 2026</span>
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


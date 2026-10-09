import React, { useState } from 'react';
import { Navbar } from './components/Navbar';
import { Trees, Cpu, Terminal, ArrowRight } from 'lucide-react';

export const App: React.FC = () => {
  const [activeScreen, setActiveScreen] = useState<'dashboard' | 'away' | 'trace' | 'results'>('dashboard');
  const [selectedMode, setSelectedMode] = useState<'AUDIT' | 'FIX'>('AUDIT');

  return (
    <div className="min-h-screen flex flex-col bg-dark-bg text-slate-100">
      <Navbar activeScreen={activeScreen} onNavigate={setActiveScreen} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Design System & Theme Showcase */}
        <div className="space-y-8">
          {/* Hero Branding Banner */}
          <div className="glass-panel p-8 sm:p-10 relative overflow-hidden border border-forest-600/30">
            <div className="absolute top-0 right-0 w-96 h-96 bg-grass-neon/5 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20"></div>
            <div className="relative z-10 max-w-3xl">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-forest-900/80 border border-grass-neon/30 text-grass-neon text-xs font-semibold mb-4 shadow-sm">
                <Trees className="h-3.5 w-3.5" /> Hacktoberfest 2026: "Touch Grass" Edition
              </div>
              <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-white mb-4 leading-tight">
                Give your code a job. <br />
                <span className="text-glow-gradient">Go touch grass.</span>
              </h1>
              <p className="text-slate-300 text-base sm:text-lg leading-relaxed mb-6 font-normal">
                Autonomous local-first AI coding agent powered by Google Gemma 2. Plans AST refactoring, executes test suites, applies isolated Git patches, and debriefs you with ElevenLabs voice narration upon your return.
              </p>
              
              <div className="flex flex-wrap items-center gap-4">
                <button
                  onClick={() => alert("Touch Grass mode activated!")}
                  className="btn-touch-grass animate-grass-pulse cursor-pointer"
                >
                  <Trees className="h-5 w-5" />
                  <span>[ 🌳 GO TOUCH GRASS ]</span>
                </button>
                <button
                  onClick={() => setActiveScreen('trace')}
                  className="btn-secondary cursor-pointer"
                >
                  <Terminal className="h-4 w-4 text-grass-neon" />
                  <span>View Telemetry Trace</span>
                  <ArrowRight className="h-4 w-4 ml-1" />
                </button>
              </div>
            </div>
          </div>

          {/* Design Tokens & Theme Components Preview Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Card 1: Mode Switcher */}
            <div className="glass-card p-6 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-mono uppercase tracking-wider text-slate-400">Execution Mode</span>
                  <span className="badge-grass">Deterministic</span>
                </div>
                <h3 className="text-lg font-bold text-white mb-2">Safety Sandbox</h3>
                <p className="text-xs text-slate-400 mb-4">
                  Switch between read-only audit inspections and isolated Git branch repairs.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-2 bg-dark-input p-1.5 rounded-xl border border-forest-800/60">
                <button
                  onClick={() => setSelectedMode('AUDIT')}
                  className={`py-2 px-3 rounded-lg text-xs font-bold transition-all ${
                    selectedMode === 'AUDIT'
                      ? 'bg-forest-700 text-white shadow-sm'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  🛡️ Audit Mode
                </button>
                <button
                  onClick={() => setSelectedMode('FIX')}
                  className={`py-2 px-3 rounded-lg text-xs font-bold transition-all ${
                    selectedMode === 'FIX'
                      ? 'bg-amber-600/80 text-white shadow-sm'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  ⚡ Fix Mode
                </button>
              </div>
            </div>

            {/* Card 2: Local AI Inference Core */}
            <div className="glass-card p-6 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-mono uppercase tracking-wider text-slate-400">Local AI Engine</span>
                  <span className="badge-grass">100% Offline</span>
                </div>
                <h3 className="text-lg font-bold text-white mb-2">Google Gemma 2 Core</h3>
                <p className="text-xs text-slate-400 mb-4">
                  Structured JSON schemas strictly enforced with zero external API fees or telemetry leak.
                </p>
              </div>

              <div className="flex items-center gap-2 p-2.5 rounded-lg bg-forest-950/60 border border-forest-800/40 font-mono text-xs text-grass-neon">
                <Cpu className="h-4 w-4" />
                <span>Ollama daemon: gemma2:9b active</span>
              </div>
            </div>

            {/* Card 3: Touch Grass Metrics Badge */}
            <div className="glass-card p-6 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-mono uppercase tracking-wider text-slate-400">Outdoor Freedom</span>
                  <span className="badge-grass">🌳 Park Ranger</span>
                </div>
                <h3 className="text-lg font-bold text-white mb-2">Away-Time Tracker</h3>
                <p className="text-xs text-slate-400 mb-4">
                  Computes developer screen-freedom duration and synthesizes audio voice debriefs.
                </p>
              </div>

              <div className="flex items-center justify-between p-2.5 rounded-lg bg-forest-950/60 border border-forest-800/40 font-mono text-xs">
                <span className="text-slate-400">Grass Touched:</span>
                <span className="text-grass-neon font-bold">00:24:18 (2,400 steps)</span>
              </div>
            </div>
          </div>
        </div>
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

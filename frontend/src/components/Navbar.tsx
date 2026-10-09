import React from 'react';
import { Trees, Sparkles, Activity, ShieldCheck } from 'lucide-react';

interface NavbarProps {
  activeScreen?: 'dashboard' | 'away' | 'trace' | 'results';
  onNavigate?: (screen: 'dashboard' | 'away' | 'trace' | 'results') => void;
  ollamaOnline?: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeScreen = 'dashboard',
  onNavigate,
  ollamaOnline = true,
}) => {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-forest-800/40 bg-dark-bg/80 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand & Logo */}
        <div 
          onClick={() => onNavigate && onNavigate('dashboard')}
          className="flex items-center gap-3 cursor-pointer group"
        >
          <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-grass-neon to-forest-700 flex items-center justify-center shadow-glow-subtle group-hover:shadow-glow-grass transition-all duration-300">
            <Trees className="h-5 w-5 text-forest-950" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-lg tracking-tight text-white group-hover:text-grass-neon transition-colors">
                OutOfOffice <span className="text-grass-neon font-black">AI</span>
              </span>
              <span className="badge-grass hidden sm:inline-flex">
                <Sparkles className="h-3 w-3" /> Gemma 2 Local
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-mono tracking-wide -mt-0.5">
              100% Offline • Autonomous Coding Agent
            </p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="hidden md:flex items-center gap-1.5 bg-forest-950/60 p-1 rounded-xl border border-forest-800/50">
          <button
            onClick={() => onNavigate && onNavigate('dashboard')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeScreen === 'dashboard'
                ? 'bg-forest-700/80 text-grass-neon border border-grass-neon/30 shadow-sm'
                : 'text-slate-400 hover:text-white hover:bg-forest-900/40'
            }`}
          >
            Mission Control
          </button>
          <button
            onClick={() => onNavigate && onNavigate('away')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeScreen === 'away'
                ? 'bg-forest-700/80 text-grass-neon border border-grass-neon/30 shadow-sm'
                : 'text-slate-400 hover:text-white hover:bg-forest-900/40'
            }`}
          >
            🌱 Away Screen
          </button>
          <button
            onClick={() => onNavigate && onNavigate('trace')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeScreen === 'trace'
                ? 'bg-forest-700/80 text-grass-neon border border-grass-neon/30 shadow-sm'
                : 'text-slate-400 hover:text-white hover:bg-forest-900/40'
            }`}
          >
            <Activity className="h-3 w-3 inline mr-1" /> Telemetry
          </button>
          <button
            onClick={() => onNavigate && onNavigate('results')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeScreen === 'results'
                ? 'bg-forest-700/80 text-grass-neon border border-grass-neon/30 shadow-sm'
                : 'text-slate-400 hover:text-white hover:bg-forest-900/40'
            }`}
          >
            <ShieldCheck className="h-3 w-3 inline mr-1" /> Results Hub
          </button>
        </nav>

        {/* Live Status Indicators */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-forest-900/50 border border-forest-800/40">
            <span className="relative flex h-2.5 w-2.5">
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${ollamaOnline ? 'bg-grass-neon' : 'bg-amber-400'}`}></span>
              <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${ollamaOnline ? 'bg-grass-neon' : 'bg-amber-500'}`}></span>
            </span>
            <span className="text-xs font-mono text-slate-300 font-medium hidden sm:inline">
              {ollamaOnline ? 'OLLAMA READY' : 'LOCAL ENGINE'}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};

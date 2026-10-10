/**
 * Flat Minimalist Navigation Bar Component
 * Clean, professional developer styling without emojis.
 */

import React from 'react';
import { Terminal, Activity, ShieldCheck, Layers } from 'lucide-react';

interface NavbarProps {
  activeScreen?: 'dashboard' | 'trace' | 'results';
  onNavigate?: (screen: 'dashboard' | 'trace' | 'results') => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeScreen = 'dashboard',
  onNavigate,
}) => {

  return (
    <header className="sticky top-0 z-50 w-full border-b border-[#222d35] bg-[#0b0f12]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
        {/* Brand & Logo */}
        <div
          onClick={() => onNavigate && onNavigate('dashboard')}
          className="flex items-center gap-2.5 cursor-pointer select-none"
        >
          <div className="h-8 w-8 rounded bg-[#182026] border border-[#222d35] flex items-center justify-center text-emerald-400">
            <Terminal className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm tracking-tight text-white">
                OutOfOffice <span className="text-emerald-400 font-mono text-xs font-normal">AI</span>
              </span>
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex items-center gap-1 bg-[#12181c] p-1 rounded-md border border-[#222d35]">
          <button
            onClick={() => onNavigate && onNavigate('dashboard')}
            className={`px-3 py-1 rounded text-xs font-medium transition-colors ${activeScreen === 'dashboard'
              ? 'bg-[#182026] text-white border border-[#2e3e4a]'
              : 'text-slate-400 hover:text-slate-200'
              }`}
          >
            <Layers className="h-3 w-3 inline mr-1 text-slate-400" />
            Dashboard
          </button>
          <button
            onClick={() => onNavigate && onNavigate('trace')}
            className={`px-3 py-1 rounded text-xs font-medium transition-colors ${activeScreen === 'trace'
              ? 'bg-[#182026] text-white border border-[#2e3e4a]'
              : 'text-slate-400 hover:text-slate-200'
              }`}
          >
            <Activity className="h-3 w-3 inline mr-1 text-slate-400" />
            Telemetry
          </button>
          <button
            onClick={() => onNavigate && onNavigate('results')}
            className={`px-3 py-1 rounded text-xs font-medium transition-colors ${activeScreen === 'results'
              ? 'bg-[#182026] text-white border border-[#2e3e4a]'
              : 'text-slate-400 hover:text-slate-200'
              }`}
          >
            <ShieldCheck className="h-3 w-3 inline mr-1 text-slate-400" />
            Results Hub
          </button>
        </nav>
      </div>
    </header>
  );
};

export default Navbar;

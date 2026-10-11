import React from 'react';
import {
  Cpu,
  Activity,
  Volume2,
  ArrowRight,
  ShieldCheck,
} from 'lucide-react';

interface LandingPageProps {
  onNavigate: (screen: 'landing' | 'dashboard' | 'trace' | 'results') => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onNavigate }) => {
  return (
    <div className="w-full flex-1 flex flex-col justify-center items-center max-w-5xl mx-auto py-8">
      {/* Hero Section */}
      <section className="text-center space-y-6 w-full max-w-2xl mx-auto">
        <h1 className="text-5xl sm:text-7xl font-extrabold tracking-tight text-white leading-none">
          OOO
        </h1>

        <p className="text-sm sm:text-base text-slate-400 leading-relaxed px-4">
          OutOfOffice AI delegates maintenance, dead code cleanup, and test repairs to local Google Gemma 2 models. Your private code never leaves your workstation.
        </p>

        <div className="pt-2 flex justify-center">
          <button
            type="button"
            onClick={() => onNavigate('dashboard')}
            className="px-6 py-2.5 rounded-md bg-emerald-500 hover:bg-emerald-400 text-[#090d10] font-semibold text-sm transition-colors inline-flex items-center justify-center gap-2 shadow-lg shadow-emerald-500/10"
          >
            <span>Launch Mission Control</span>
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </section>

      {/* Architecture Highlights */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 w-full mt-16">
        <div className="p-5 rounded-lg bg-[#0e1418] border border-[#1e272f] space-y-2 flex flex-col justify-start">
          <div className="flex items-center gap-2 text-emerald-400">
            <Cpu className="h-4 w-4 shrink-0" />
            <span className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-300">Local Gemma 2</span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Inference runs locally through Ollama. Zero network latency, zero token costs, and 100% data privacy.
          </p>
        </div>

        <div className="p-5 rounded-lg bg-[#0e1418] border border-[#1e272f] space-y-2 flex flex-col justify-start">
          <div className="flex items-center gap-2 text-purple-400">
            <Activity className="h-4 w-4 shrink-0" />
            <span className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-300">Sentry Tracing</span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Granular span telemetry and distributed tracing instrument every planning step and execution node.
          </p>
        </div>

        <div className="p-5 rounded-lg bg-[#0e1418] border border-[#1e272f] space-y-2 flex flex-col justify-start">
          <div className="flex items-center gap-2 text-sky-400">
            <Volume2 className="h-4 w-4 shrink-0" />
            <span className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-300">Voice Debrief</span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            ElevenLabs generates an executive audio briefing summarizing codebase health and modified files.
          </p>
        </div>

        <div className="p-5 rounded-lg bg-[#0e1418] border border-[#1e272f] space-y-2 flex flex-col justify-start">
          <div className="flex items-center gap-2 text-amber-400">
            <ShieldCheck className="h-4 w-4 shrink-0" />
            <span className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-300">Git Safety</span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Modifications occur in dedicated isolated branches with automated AST syntax checking before output.
          </p>
        </div>
      </section>
    </div>
  );
};

export default LandingPage;

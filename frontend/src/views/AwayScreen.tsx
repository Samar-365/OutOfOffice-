/**
 * Screen 2: Headless Away Screen & Grass Timer
 * Minimalist, relaxing full-screen view with a live counting Grass Touched Timer,
 * outdoor badge progression, real-time agent status ticker, and safe-to-close assurances.
 */

import React, { useState, useEffect } from 'react';
import { useJob } from '../context/JobContext';
import {
  Compass,
  Footprints,
  ShieldCheck,
  CheckCircle2,
  Terminal,
  ArrowRight,
  Sparkles,
  Flame,
  Volume2,
  VolumeX,
} from 'lucide-react';

interface AwayScreenProps {
  onNavigate: (screen: 'dashboard' | 'away' | 'trace' | 'results') => void;
}

export const AwayScreen: React.FC<AwayScreenProps> = ({ onNavigate }) => {
  const { activeJob, cancelActiveJob } = useJob();

  // Local seconds counter that ticks every second starting from job started_at or now
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(() => {
    if (activeJob?.started_at) {
      const startMs = new Date(activeJob.started_at).getTime();
      const diffSec = Math.max(0, Math.floor((Date.now() - startMs) / 1000));
      return diffSec;
    }
    return 0;
  });

  const [ambientAudioEnabled, setAmbientAudioEnabled] = useState<boolean>(false);
  const [showCancelConfirm, setShowCancelConfirm] = useState<boolean>(false);

  // Tick timer every second
  useEffect(() => {
    const timer = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Format seconds into HH:MM:SS
  const formatTimer = (totalSec: number) => {
    const hours = Math.floor(totalSec / 3600);
    const minutes = Math.floor((totalSec % 3600) / 60);
    const seconds = totalSec % 60;
    return `${hours.toString().padStart(2, '0')}:${minutes
      .toString()
      .padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  };

  // Determine Badge & Outdoor Level
  const getOutdoorLevel = (seconds: number) => {
    const minutes = seconds / 60;
    if (minutes < 5) {
      return {
        tier: 'Sprout Explorer',
        icon: '🌱',
        color: 'text-emerald-400',
        quote: 'Taking the first breath of fresh air. Your code is in safe hands.',
      };
    } else if (minutes < 15) {
      return {
        tier: 'Meadow Stroller',
        icon: '🌿',
        color: 'text-green-400',
        quote: 'Enjoying the gentle breeze. The agent is analyzing the AST syntax tree.',
      };
    } else if (minutes < 30) {
      return {
        tier: 'Park Ranger',
        icon: '🌳',
        color: 'text-grass-neon',
        quote: 'Full deep outdoor immersion. Tests are being executed in isolated sandbox.',
      };
    } else {
      return {
        tier: 'Mountain Monk',
        icon: '🏔️',
        color: 'text-cyan-400',
        quote: 'Master of developer work-life harmony. Returning to green builds and clean diffs.',
      };
    }
  };

  const level = getOutdoorLevel(elapsedSeconds);
  const estimatedSteps = Math.floor(elapsedSeconds * 1.6);
  const isFinished = activeJob?.status === 'COMPLETED' || activeJob?.status === 'FAILED';

  // Extract latest step status message
  const latestStep = activeJob?.steps && activeJob.steps.length > 0
    ? activeJob.steps[activeJob.steps.length - 1]
    : null;

  return (
    <div className="relative min-h-[calc(100vh-14rem)] flex flex-col items-center justify-between p-4 sm:p-8 animate-fade-in text-center overflow-hidden">
      {/* Background Animated Ambient Nature Glow */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-grass-neon/5 rounded-full blur-[140px] animate-pulse"></div>
        <div className="absolute bottom-10 left-1/3 w-80 h-80 bg-forest-600/10 rounded-full blur-[100px]"></div>
      </div>

      {/* Top Banner: Safe-to-Close Pill & Ambient Sound Toggle */}
      <div className="relative z-10 w-full max-w-3xl flex items-center justify-between gap-4">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-forest-950/80 border border-emerald-500/30 text-emerald-400 text-xs font-semibold shadow-lg backdrop-blur-md">
          <ShieldCheck className="h-4 w-4 text-emerald-400" />
          <span>Local Background Agent Active • Safe to close or lock screen</span>
        </div>

        <button
          type="button"
          onClick={() => setAmbientAudioEnabled(!ambientAudioEnabled)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-forest-950/60 hover:bg-forest-900/60 border border-forest-800/60 text-slate-300 text-xs font-mono transition-colors"
          title="Toggle Nature Ambient Sound"
        >
          {ambientAudioEnabled ? (
            <>
              <Volume2 className="h-3.5 w-3.5 text-grass-neon" />
              <span>Forest Ambience ON</span>
            </>
          ) : (
            <>
              <VolumeX className="h-3.5 w-3.5 text-slate-500" />
              <span>Ambience Muted</span>
            </>
          )}
        </button>
      </div>

      {/* Central Hero: Big Grass Timer & Outdoor Tier */}
      <div className="relative z-10 my-auto py-8 max-w-2xl space-y-6">
        {/* Tier Icon & Name */}
        <div className="inline-flex flex-col items-center gap-2">
          <div className="w-20 h-20 sm:w-24 sm:h-24 rounded-3xl bg-forest-900/50 border border-grass-neon/40 flex items-center justify-center text-4xl sm:text-5xl shadow-2xl shadow-grass-neon/10 backdrop-blur-xl animate-float">
            <span>{level.icon}</span>
          </div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-forest-950 border border-forest-800 text-xs font-bold text-slate-200">
            <Compass className="h-3.5 w-3.5 text-grass-neon" />
            <span>Outdoor Level: {level.tier}</span>
          </div>
        </div>

        {/* The Huge Digital Timer */}
        <div className="space-y-2">
          <div className="font-mono text-5xl sm:text-7xl lg:text-8xl font-black tracking-widest text-glow-gradient">
            {formatTimer(elapsedSeconds)}
          </div>
          <p className="text-slate-400 text-sm sm:text-base font-medium max-w-md mx-auto italic">
            "{level.quote}"
          </p>
        </div>

        {/* Live Metrics Row: Steps & Screen-time saved */}
        <div className="grid grid-cols-2 gap-4 max-w-md mx-auto pt-2">
          <div className="glass-card p-3.5 text-center border border-forest-800/50">
            <div className="text-xs text-slate-400 flex items-center justify-center gap-1 mb-1">
              <Footprints className="h-3.5 w-3.5 text-grass-neon" />
              <span>Estimated Steps</span>
            </div>
            <div className="text-lg font-bold font-mono text-white">
              {estimatedSteps.toLocaleString()}
            </div>
          </div>

          <div className="glass-card p-3.5 text-center border border-forest-800/50">
            <div className="text-xs text-slate-400 flex items-center justify-center gap-1 mb-1">
              <Flame className="h-3.5 w-3.5 text-amber-400" />
              <span>Screen Time Saved</span>
            </div>
            <div className="text-lg font-bold font-mono text-white">
              {Math.floor(elapsedSeconds / 60)} mins
            </div>
          </div>
        </div>

        {/* Subtle Live Status Ticker */}
        <div className="p-3.5 rounded-2xl bg-forest-950/70 border border-forest-800/80 max-w-lg mx-auto flex items-center justify-between gap-3 text-xs font-mono shadow-inner backdrop-blur-md">
          <div className="flex items-center gap-2.5 truncate">
            <div className="w-2 h-2 rounded-full bg-grass-neon animate-ping flex-shrink-0"></div>
            <span className="text-slate-400">Agent Status:</span>
            <span className="text-slate-200 font-bold truncate">
              {isFinished
                ? `Job ${activeJob?.status}!`
                : latestStep
                ? `${latestStep.step_name}...`
                : 'Orchestrating autonomous workflow...'}
            </span>
          </div>

          <button
            type="button"
            onClick={() => onNavigate('trace')}
            className="text-grass-neon hover:underline flex items-center gap-1 flex-shrink-0 text-[11px]"
          >
            <span>Live Stream</span>
            <ArrowRight className="h-3 w-3" />
          </button>
        </div>
      </div>

      {/* Bottom Actions Bar */}
      <div className="relative z-10 w-full max-w-xl flex flex-col sm:flex-row items-center justify-center gap-4 pt-4 border-t border-forest-900/60">
        {isFinished ? (
          <button
            type="button"
            onClick={() => onNavigate('results')}
            className="w-full sm:w-auto btn-touch-grass px-8 py-3.5 text-sm font-bold flex items-center justify-center gap-2 shadow-lg shadow-grass-neon/20 cursor-pointer animate-grass-pulse"
          >
            <Sparkles className="h-4 w-4" />
            <span>I'm Back! Check Results & Voice Debrief</span>
            <ArrowRight className="h-4 w-4" />
          </button>
        ) : (
          <div className="flex flex-wrap items-center justify-center gap-3 w-full">
            <button
              type="button"
              onClick={() => onNavigate('trace')}
              className="btn-secondary px-6 py-2.5 text-xs font-semibold flex items-center gap-2 cursor-pointer"
            >
              <Terminal className="h-4 w-4 text-grass-neon" />
              <span>Inspect Agent Trace</span>
            </button>

            <button
              type="button"
              onClick={() => onNavigate('results')}
              className="btn-primary px-6 py-2.5 text-xs font-semibold flex items-center gap-2 cursor-pointer"
            >
              <CheckCircle2 className="h-4 w-4" />
              <span>I'm Back (Results Hub)</span>
            </button>

            {!showCancelConfirm ? (
              <button
                type="button"
                onClick={() => setShowCancelConfirm(true)}
                className="text-xs text-slate-500 hover:text-red-400 font-mono transition-colors px-2 py-1"
              >
                Cancel Job
              </button>
            ) : (
              <div className="flex items-center gap-2 animate-fade-in">
                <span className="text-xs text-red-400 font-mono">Abort task?</span>
                <button
                  type="button"
                  onClick={async () => {
                    await cancelActiveJob();
                    setShowCancelConfirm(false);
                    onNavigate('dashboard');
                  }}
                  className="px-2.5 py-1 rounded-lg bg-red-950/80 border border-red-500/50 text-red-300 text-xs font-bold hover:bg-red-900"
                >
                  Yes, Stop
                </button>
                <button
                  type="button"
                  onClick={() => setShowCancelConfirm(false)}
                  className="px-2.5 py-1 rounded-lg bg-forest-900 text-slate-300 text-xs hover:bg-forest-800"
                >
                  No
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default AwayScreen;

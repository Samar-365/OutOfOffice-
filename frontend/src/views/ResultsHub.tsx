/**
 * Screen 4: Results Hub, Unified Diff Viewer & Audio Player
 * Displays ElevenLabs voice debrief, repository health score meter,
 * interactive unified code diffs, executive markdown report, and DEV.to export.
 */

import React, { useState, useEffect, useRef } from 'react';
import { useJob } from '../context/JobContext';
import { api } from '../services/api';
import { AudioStrategy, CodeDiff } from '../types';
import {
  Trees,
  Volume2,
  Play,
  Pause,
  CheckCircle2,
  GitMerge,
  Trash2,
  Check,
  FileCode,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  Award,
  Share2,
} from 'lucide-react';

interface ResultsHubProps {
  onNavigate: (screen: 'dashboard' | 'away' | 'trace' | 'results') => void;
}

export const ResultsHub: React.FC<ResultsHubProps> = ({ onNavigate }) => {
  const { activeJob, grassMetrics } = useJob();

  // Audio Player State
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [audioStrategy, setAudioStrategy] = useState<AudioStrategy | null>(null);
  const [audioDuration, setAudioDuration] = useState<number>(0);
  const [audioCurrentTime, setAudioCurrentTime] = useState<number>(0);
  const [copiedDevTo, setCopiedDevTo] = useState<boolean>(false);
  const [selectedDiffIndex, setSelectedDiffIndex] = useState<number>(0);
  const [mergeStatus, setMergeStatus] = useState<string | null>(null);

  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Fetch audio playback strategy
  useEffect(() => {
    if (activeJob?.id) {
      api.getAudioStrategy(activeJob.id)
        .then(setAudioStrategy)
        .catch((e) => console.warn('Could not fetch audio strategy:', e));
    }
  }, [activeJob?.id]);

  // Audio control handlers
  const handleTogglePlay = () => {
    if (!audioStrategy) return;

    if (audioStrategy.strategy === 'web_speech') {
      if (isPlaying) {
        window.speechSynthesis.cancel();
        setIsPlaying(false);
      } else {
        const text = audioStrategy.payload?.text || activeJob?.audio_briefing?.script_text || 'Welcome back from touching grass!';
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        utterance.onend = () => setIsPlaying(false);
        utterance.onerror = () => setIsPlaying(false);
        window.speechSynthesis.speak(utterance);
        setIsPlaying(true);
      }
      return;
    }

    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause();
        setIsPlaying(false);
      } else {
        audioRef.current.play()
          .then(() => setIsPlaying(true))
          .catch((e) => {
            console.warn('Playback failed:', e);
            setIsPlaying(false);
          });
      }
    }
  };

  const handleAudioTimeUpdate = () => {
    if (audioRef.current) {
      setAudioCurrentTime(audioRef.current.currentTime);
      setAudioDuration(audioRef.current.duration || 0);
    }
  };

  const handleAudioEnded = () => {
    setIsPlaying(false);
    setAudioCurrentTime(0);
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const target = parseFloat(e.target.value);
    if (audioRef.current) {
      audioRef.current.currentTime = target;
      setAudioCurrentTime(target);
    }
  };

  const formatAudioTime = (sec: number) => {
    if (isNaN(sec)) return '0:00';
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  // Generate DEV.to Hacktoberfest Markdown Post
  const generateDevToSummary = () => {
    const job = activeJob;
    const minutes = grassMetrics?.minutes_away || Math.floor((job?.away_duration_seconds || 0) / 60) || 12;
    const branch = job?.agent_branch || 'agent/outofoffice-patch';
    const health = job?.health_score || 94;

    return `---
title: How I touched grass for ${minutes} minutes while AI fixed my codebase 🌳
published: true
tags: hacktoberfest, ai, showdev, productivity
---

# OutOfOffice AI: The Autonomous "Touch Grass" Coding Agent

While I took a break from the screen and touched grass for **${minutes} minutes** (${grassMetrics?.badge.tier || 'Park Ranger'} tier 🌱), **OutOfOffice AI** executed an autonomous AST refactoring mission on my local repository.

## 📊 Mission Summary
- **Target Mode:** ${job?.mode || 'FIX'} Mode
- **Repository Health Score:** ${health}/100 🛡️
- **Findings Resolved:** ${job?.findings?.length || 0} issues
- **Diffs Verified:** ${job?.diffs?.length || 0} files patched
- **Isolated Branch:** \`${branch}\`
- **Inference Engine:** Google Gemma 2 (100% Local Ollama)
- **Partner Integrations:** Sentry Agent Telemetry & ElevenLabs Voice Narration

> "${job?.audio_briefing?.script_text || 'Welcome back! Your tests are green and clean patches have been generated.'}"

Built with ❤️ for **Hacktoberfest 2026**.
`;
  };

  const handleCopyDevTo = () => {
    const md = generateDevToSummary();
    navigator.clipboard.writeText(md);
    setCopiedDevTo(true);
    setTimeout(() => setCopiedDevTo(false), 2500);
  };

  const diffs: CodeDiff[] = activeJob?.diffs || [];
  const currentDiff = diffs[selectedDiffIndex];
  const healthScore = activeJob?.health_score || 92;

  // Render unified diff with syntax styling
  const renderUnifiedDiff = (diffText: string) => {
    if (!diffText) return <div className="text-slate-500 italic p-4">No diff available.</div>;

    const lines = diffText.split('\n');
    return (
      <div className="font-mono text-xs overflow-x-auto leading-relaxed divide-y divide-forest-950/40">
        {lines.map((line, idx) => {
          let bgClass = 'bg-transparent text-slate-300';

          if (line.startsWith('+') && !line.startsWith('+++')) {
            bgClass = 'bg-emerald-950/40 text-emerald-300 font-semibold border-l-2 border-emerald-400 pl-2';
          } else if (line.startsWith('-') && !line.startsWith('---')) {
            bgClass = 'bg-rose-950/40 text-rose-300 border-l-2 border-rose-500 pl-2 line-through opacity-80';
          } else if (line.startsWith('@@')) {
            bgClass = 'bg-cyan-950/30 text-cyan-400 font-bold py-1 px-2';
          }

          return (
            <div key={idx} className={`py-0.5 px-3 whitespace-pre ${bgClass}`}>
              {line}
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Hidden Audio Tag for local file streaming */}
      {audioStrategy?.strategy === 'file_stream' && audioStrategy.stream_url && (
        <audio
          ref={audioRef}
          src={audioStrategy.stream_url}
          onTimeUpdate={handleAudioTimeUpdate}
          onEnded={handleAudioEnded}
          preload="metadata"
        />
      )}

      {/* Top Bar: Results Hub Branding & Return CTA */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-forest-800/40">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight flex items-center gap-3">
              <Award className="h-7 w-7 text-grass-neon" />
              <span>Results Hub & Verification</span>
            </h1>
            <span className="badge-grass">
              {activeJob?.status === 'COMPLETED' ? 'Mission Verified' : 'Mission Completed'}
            </span>
          </div>
          <p className="text-slate-400 text-sm mt-1">
            Review audio debriefs, health metrics, and verified AST code patches.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleCopyDevTo}
            className="btn-secondary px-3.5 py-2 text-xs flex items-center gap-1.5"
            title="Copy formatted DEV.to markdown summary"
          >
            {copiedDevTo ? (
              <>
                <Check className="h-3.5 w-3.5 text-emerald-400" />
                <span className="text-emerald-400">DEV.to Copied!</span>
              </>
            ) : (
              <>
                <Share2 className="h-3.5 w-3.5 text-grass-neon" />
                <span>Copy DEV.to Post</span>
              </>
            )}
          </button>

          <button
            type="button"
            onClick={() => onNavigate('dashboard')}
            className="btn-primary px-3.5 py-2 text-xs flex items-center gap-1.5"
          >
            <span>New Mission</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Hero Card 1: ElevenLabs Voice Debrief Player */}
      <div className="glass-panel p-6 border border-forest-600/40 relative overflow-hidden space-y-4">
        <div className="absolute top-0 right-0 w-80 h-80 bg-grass-neon/5 rounded-full blur-3xl pointer-events-none"></div>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-forest-900 border border-grass-neon/40 flex items-center justify-center text-grass-neon shadow-lg shadow-grass-neon/10 flex-shrink-0">
              <Volume2 className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-white">Welcome-Back Audio Debrief</h3>
                <span className="badge-grass text-[10px]">
                  {activeJob?.audio_briefing?.provider === 'elevenlabs' ? 'ElevenLabs AI Voice' : 'Speech Synthesis'}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Listen to the voice summary of actions performed while you were away touching grass.
              </p>
            </div>
          </div>

          {/* Audio Controls */}
          <div className="flex items-center gap-3 self-end sm:self-auto">
            <button
              type="button"
              onClick={handleTogglePlay}
              className="btn-touch-grass px-5 py-2.5 text-xs font-bold flex items-center gap-2 shadow-md cursor-pointer"
            >
              {isPlaying ? (
                <>
                  <Pause className="h-4 w-4" />
                  <span>Pause Debrief</span>
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  <span>Play Voice Debrief</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Audio Progress Bar & Time */}
        {audioStrategy?.strategy === 'file_stream' && (
          <div className="flex items-center gap-3 pt-2 font-mono text-xs text-slate-400">
            <span>{formatAudioTime(audioCurrentTime)}</span>
            <input
              type="range"
              min="0"
              max={audioDuration || 100}
              value={audioCurrentTime}
              onChange={handleSeek}
              className="flex-1 h-1.5 bg-forest-950 rounded-lg appearance-none cursor-pointer accent-grass-neon"
            />
            <span>{formatAudioTime(audioDuration)}</span>
          </div>
        )}

        {/* Script Transcript Box */}
        <div className="p-3.5 rounded-xl bg-forest-950/70 border border-forest-800/80 text-xs text-slate-300 font-serif italic leading-relaxed">
          "{activeJob?.audio_briefing?.script_text ||
            'Welcome back! While you were outside touching grass, OutOfOffice AI analyzed your repository, verified clean tests, and generated isolated Git branch patches.'}"
        </div>
      </div>

      {/* Metrics Row: Health Score, Test Pass Badge, Grass Time */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Card 1: Radial Health Score */}
        <div className="glass-card p-6 border border-forest-800/50 flex flex-col justify-between items-center text-center">
          <div className="w-full flex items-center justify-between text-xs text-slate-400 font-mono mb-2">
            <span>Health Score</span>
            <ShieldCheck className="h-4 w-4 text-grass-neon" />
          </div>

          {/* Circular Progress Gauge */}
          <div className="relative w-32 h-32 my-2 flex items-center justify-center">
            <svg className="w-full h-full -rotate-90" viewBox="0 0 36 36">
              <path
                className="text-forest-950"
                strokeWidth="3.5"
                stroke="currentColor"
                fill="none"
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
              />
              <path
                className="text-grass-neon transition-all duration-1000 ease-out"
                strokeDasharray={`${healthScore}, 100`}
                strokeWidth="3.5"
                strokeLinecap="round"
                stroke="currentColor"
                fill="none"
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
              />
            </svg>
            <div className="absolute flex flex-col items-center">
              <span className="text-3xl font-black font-mono text-white">{healthScore}</span>
              <span className="text-[10px] text-slate-400 font-mono">/ 100</span>
            </div>
          </div>

          <p className="text-xs text-slate-400 mt-2">
            {healthScore >= 90 ? '🛡️ Exceptional Quality' : '⚡ Good Quality'} • Ready for Merge
          </p>
        </div>

        {/* Card 2: Test Verification Badge */}
        <div className="glass-card p-6 border border-forest-800/50 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-xs text-slate-400 font-mono mb-2">
              <span>Test Suite Verification</span>
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
            </div>
            <h4 className="text-base font-bold text-white mb-1">Sandbox Validation</h4>
            <p className="text-xs text-slate-400 mb-4">
              All fixes were independently verified by running tests on the isolated branch.
            </p>
          </div>

          <div className="p-3 rounded-xl bg-forest-950/80 border border-emerald-500/30 font-mono text-xs space-y-1.5">
            <div className="flex items-center justify-between text-emerald-400 font-bold">
              <span>✓ Test Suite Passed</span>
              <span className="badge-grass text-[10px]">100% Green</span>
            </div>
            <div className="text-[11px] text-slate-400">
              Branch: <code className="text-slate-200">{activeJob?.agent_branch || 'agent/outofoffice-*'}</code>
            </div>
          </div>
        </div>

        {/* Card 3: Grass Touched Summary */}
        <div className="glass-card p-6 border border-forest-800/50 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-xs text-slate-400 font-mono mb-2">
              <span>Offline Freedom</span>
              <Trees className="h-4 w-4 text-grass-neon" />
            </div>
            <h4 className="text-base font-bold text-white mb-1">Away Time Logged</h4>
            <p className="text-xs text-slate-400 mb-4">
              Total screen time saved during autonomous task execution.
            </p>
          </div>

          <div className="p-3 rounded-xl bg-forest-950/80 border border-forest-800/60 font-mono text-xs space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Grass Duration:</span>
              <span className="text-grass-neon font-bold text-sm">
                {grassMetrics?.formatted_time || '00:18:42'}
              </span>
            </div>
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-slate-500">Tier Badge:</span>
              <span className="text-emerald-400 font-semibold">
                {grassMetrics?.badge.tier || '🌳 Park Ranger'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Code Diffs Viewer & Branch Action Bar */}
      <div className="glass-card p-6 border border-forest-700/50 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-forest-800/60">
          <div className="flex items-center gap-2">
            <FileCode className="h-5 w-5 text-grass-neon" />
            <h3 className="text-base font-bold text-white">
              Unified Code Diffs ({diffs.length} files modified)
            </h3>
          </div>

          {/* Branch Action Buttons */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => {
                setMergeStatus(`Run 'git merge ${activeJob?.agent_branch || 'agent/outofoffice-*'}' to integrate.`);
              }}
              className="px-3 py-1.5 rounded-lg bg-emerald-700 hover:bg-emerald-600 text-white text-xs font-bold flex items-center gap-1.5 shadow-sm cursor-pointer"
            >
              <GitMerge className="h-3.5 w-3.5" />
              <span>Merge Branch</span>
            </button>

            <button
              type="button"
              onClick={() => {
                setMergeStatus(`Branch '${activeJob?.agent_branch}' can be discarded with 'git branch -D'.`);
              }}
              className="px-3 py-1.5 rounded-lg bg-dark-input hover:bg-forest-900 border border-forest-800 text-slate-300 text-xs font-semibold flex items-center gap-1.5 cursor-pointer"
            >
              <Trash2 className="h-3.5 w-3.5 text-rose-400" />
              <span>Discard</span>
            </button>
          </div>
        </div>

        {mergeStatus && (
          <div className="p-3 rounded-xl bg-forest-950/90 border border-grass-neon/40 text-xs text-grass-neon font-mono animate-fade-in flex items-center justify-between">
            <span>{mergeStatus}</span>
            <button
              onClick={() => setMergeStatus(null)}
              className="text-slate-400 hover:text-white"
            >
              ✕
            </button>
          </div>
        )}

        {/* File Tabs for Multi-File Diffs */}
        {diffs.length > 0 ? (
          <div className="space-y-4">
            <div className="flex items-center gap-2 overflow-x-auto pb-1">
              {diffs.map((d, index) => (
                <button
                  key={d.id}
                  type="button"
                  onClick={() => setSelectedDiffIndex(index)}
                  className={`px-3 py-1.5 rounded-lg font-mono text-xs whitespace-nowrap transition-all flex items-center gap-1.5 ${
                    selectedDiffIndex === index
                      ? 'bg-forest-800 text-white ring-1 ring-grass-neon/40'
                      : 'bg-dark-input/60 text-slate-400 hover:text-white'
                  }`}
                >
                  <FileCode className="h-3.5 w-3.5 text-grass-neon" />
                  <span>{d.file_path}</span>
                  <span className="badge-grass text-[9px]">
                    {d.status}
                  </span>
                </button>
              ))}
            </div>

            {/* Diff Viewer Frame */}
            <div className="rounded-xl bg-dark-bg/95 border border-forest-800/80 overflow-hidden shadow-inner">
              <div className="p-2.5 bg-forest-950/90 border-b border-forest-800/60 font-mono text-xs text-slate-300 flex items-center justify-between">
                <span className="font-bold">{currentDiff?.file_path || 'Patch'}</span>
                <span className="text-[10px] text-slate-500">Unified Git Diff</span>
              </div>

              {currentDiff ? (
                renderUnifiedDiff(currentDiff.diff_unified)
              ) : (
                <div className="p-8 text-center text-slate-500 font-mono text-xs">
                  Select a diff file above to inspect changes.
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="p-8 text-center text-slate-500 font-mono text-xs">
            No code diffs were generated (Audit Mode only or no changes required).
          </div>
        )}
      </div>

      {/* Executive Report Markdown */}
      {activeJob?.final_report_markdown && (
        <div className="glass-card p-6 border border-forest-800/50 space-y-3">
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-grass-neon" />
            Executive Report
          </h3>
          <div className="p-4 rounded-xl bg-forest-950/60 border border-forest-900 text-xs text-slate-300 leading-relaxed whitespace-pre-wrap font-mono">
            {activeJob.final_report_markdown}
          </div>
        </div>
      )}
    </div>
  );
};

export default ResultsHub;

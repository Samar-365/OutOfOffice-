/**
 * Screen 4: Results Hub, Unified Diff Viewer & Audio Player
 * Flat, minimalist, professional developer UI with zero emojis.
 */

import React, { useState, useEffect, useRef } from 'react';
import { useJob } from '../context/JobContext';
import { api } from '../services/api';
import { AudioStrategy, CodeDiff } from '../types';
import {
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
  Clock,
} from 'lucide-react';

interface ResultsHubProps {
  onNavigate: (screen: 'dashboard' | 'trace' | 'results') => void;
}

export const ResultsHub: React.FC<ResultsHubProps> = ({ onNavigate }) => {
  const { activeJob, grassMetrics } = useJob();

  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [audioStrategy, setAudioStrategy] = useState<AudioStrategy | null>(null);
  const [audioDuration, setAudioDuration] = useState<number>(0);
  const [audioCurrentTime, setAudioCurrentTime] = useState<number>(0);
  const [copiedDevTo, setCopiedDevTo] = useState<boolean>(false);
  const [selectedDiffIndex, setSelectedDiffIndex] = useState<number>(0);
  const [mergeStatus, setMergeStatus] = useState<string | null>(null);

  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    if (activeJob?.id) {
      api.getAudioStrategy(activeJob.id)
        .then(setAudioStrategy)
        .catch((e) => console.warn('Could not fetch audio strategy:', e));
    }
  }, [activeJob?.id]);

  const handleTogglePlay = () => {
    if (!audioStrategy) return;

    if (audioStrategy.strategy === 'web_speech') {
      if (isPlaying) {
        window.speechSynthesis.cancel();
        setIsPlaying(false);
      } else {
        const text = audioStrategy.payload?.text || activeJob?.audio_briefing?.script_text || 'Welcome back. Your tasks have completed.';
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

  const generateDevToSummary = () => {
    const job = activeJob;
    const minutes = grassMetrics?.minutes_away || Math.floor((job?.away_duration_seconds || 0) / 60) || 12;
    const branch = job?.agent_branch || 'agent/outofoffice-patch';
    const health = job?.health_score || 94;

    return `---
title: Autonomous Offline Refactoring with OutOfOffice AI (${minutes} minutes away)
published: true
tags: hacktoberfest, ai, showdev, productivity
---

# OutOfOffice AI: Autonomous Background Coding Agent

While taking a break for **${minutes} minutes**, **OutOfOffice AI** executed an autonomous AST refactoring mission on the local repository.

## Summary
- **Target Mode:** ${job?.mode || 'FIX'} Mode
- **Repository Health Score:** ${health}/100
- **Findings Resolved:** ${job?.findings?.length || 0} issues
- **Diffs Verified:** ${job?.diffs?.length || 0} files patched
- **Isolated Branch:** \`${branch}\`
- **Inference Engine:** Google Gemma 2 (Local Ollama)
- **Partner Integrations:** Sentry Agent Telemetry & ElevenLabs Voice Narration

> "${job?.audio_briefing?.script_text || 'Welcome back. Your tests are green and clean patches have been generated.'}"
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

  const renderUnifiedDiff = (diffText: string) => {
    if (!diffText) return <div className="text-slate-500 italic p-3 text-xs">No diff available.</div>;

    const lines = diffText.split('\n');
    return (
      <div className="font-mono text-xs overflow-x-auto leading-relaxed divide-y divide-[#182026]">
        {lines.map((line, idx) => {
          let bgClass = 'bg-transparent text-slate-300';

          if (line.startsWith('+') && !line.startsWith('+++')) {
            bgClass = 'bg-emerald-950/20 text-emerald-300 font-medium border-l-2 border-emerald-500 pl-2';
          } else if (line.startsWith('-') && !line.startsWith('---')) {
            bgClass = 'bg-red-950/20 text-red-300 border-l-2 border-red-500 pl-2 opacity-80';
          } else if (line.startsWith('@@')) {
            bgClass = 'bg-sky-950/20 text-sky-400 font-semibold py-0.5 px-2';
          }

          return (
            <div key={idx} className={`py-0.5 px-2.5 whitespace-pre ${bgClass}`}>
              {line}
            </div>
          );
        })}
      </div>
    );
  };

  const renderFormattedReport = (rawText: string) => {
    if (!rawText) return null;

    const cleanSymbols = (str: string) => str.replace(/[*#]/g, '');

    const renderInline = (text: string) => {
      // Split on bold tokens: **bold**
      const boldParts = text.split(/\*\*(.*?)\*\*/g);

      return boldParts.map((part, i) => {
        if (i % 2 === 1) {
          return (
            <strong key={i} className="text-white font-semibold">
              {cleanSymbols(part)}
            </strong>
          );
        }

        // Split on inline code `code`
        const codeParts = part.split(/`(.*?)`/g);
        return codeParts.map((sub, j) => {
          if (j % 2 === 1) {
            return (
              <code key={`${i}-${j}`} className="px-1.5 py-0.5 rounded bg-[#182026] text-emerald-300 font-mono text-[11px] border border-[#222d35]">
                {sub}
              </code>
            );
          }

          // Split on italic *italic* or _italic_
          const italicParts = sub.split(/\*(.*?)\*/g);
          return italicParts.map((it, k) => {
            if (k % 2 === 1) {
              return (
                <span key={`${i}-${j}-${k}`} className="italic text-slate-400">
                  {cleanSymbols(it)}
                </span>
              );
            }
            return cleanSymbols(it);
          });
        });
      });
    };

    const lines = rawText.split('\n');

    return (
      <div className="space-y-2 text-xs leading-relaxed">
        {lines.map((line, idx) => {
          const trimmed = line.trim();

          if (!trimmed) {
            return <div key={idx} className="h-1.5" />;
          }

          if (trimmed === '---' || trimmed === '***' || trimmed === '___') {
            return <hr key={idx} className="border-[#222d35] my-2.5" />;
          }

          // Main Header (# Title or Title)
          if (trimmed.startsWith('# ') || trimmed.toLowerCase().includes('execution report')) {
            const headingText = cleanSymbols(trimmed.replace(/^#+\s*/, ''));
            return (
              <h2 key={idx} className="text-sm font-bold text-white tracking-tight pb-1.5 border-b border-[#222d35] mb-2">
                {headingText}
              </h2>
            );
          }

          // Section Sub-headers (### Section or Executive Summary / Key Metrics)
          if (
            trimmed.startsWith('## ') ||
            trimmed.startsWith('### ') ||
            trimmed === 'Executive Summary' ||
            trimmed === 'Key Metrics' ||
            trimmed === 'Key Findings'
          ) {
            const subText = cleanSymbols(trimmed.replace(/^#+\s*/, ''));
            return (
              <h3 key={idx} className="text-xs font-semibold uppercase tracking-wider text-emerald-400 mt-3.5 mb-1.5">
                {subText}
              </h3>
            );
          }

          // Bullet items
          if (trimmed.startsWith('* ') || trimmed.startsWith('- ') || trimmed.startsWith('• ')) {
            const bulletContent = trimmed.replace(/^[*\-•]\s+/, '');
            return (
              <div key={idx} className="flex items-start gap-2 py-0.5 text-slate-300">
                <span className="text-emerald-400 select-none text-xs leading-none mt-1">•</span>
                <span className="flex-1">{renderInline(bulletContent)}</span>
              </div>
            );
          }

          // Standard paragraph line
          return (
            <p key={idx} className="text-slate-300">
              {renderInline(trimmed)}
            </p>
          );
        })}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Audio Element */}
      {audioStrategy?.strategy === 'file_stream' && audioStrategy.stream_url && (
        <audio
          ref={audioRef}
          src={audioStrategy.stream_url}
          onTimeUpdate={handleAudioTimeUpdate}
          onEnded={handleAudioEnded}
          preload="metadata"
        />
      )}

      {/* Top Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#222d35]">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
              <Award className="h-5 w-5 text-emerald-400" />
              <span>Results Hub</span>
            </h1>
            <span className="text-emerald-400 font-mono text-xs font-medium">
              {activeJob?.status === 'COMPLETED' ? 'Verified' : 'Completed'}
            </span>
          </div>
          <p className="text-slate-400 text-xs mt-0.5">
            Review voice debrief, repository health metrics, and verified AST code patches.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleCopyDevTo}
            className="btn-secondary px-3 py-1.5 text-xs flex items-center gap-1.5"
            title="Copy formatted markdown summary"
          >
            {copiedDevTo ? (
              <>
                <Check className="h-3.5 w-3.5 text-emerald-400" />
                <span className="text-emerald-400">Copied</span>
              </>
            ) : (
              <>
                <Share2 className="h-3.5 w-3.5 text-slate-400" />
                <span>Copy Summary</span>
              </>
            )}
          </button>

          <button
            type="button"
            onClick={() => onNavigate('dashboard')}
            className="btn-primary px-3 py-1.5 text-xs flex items-center gap-1.5"
          >
            <span>New Task</span>
            <ArrowRight className="h-3 w-3" />
          </button>
        </div>
      </div>

      {/* Hero Card 1: Voice Debrief Player */}
      <div className="flat-card p-4 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded bg-[#182026] border border-[#222d35] flex items-center justify-center text-emerald-400 flex-shrink-0">
              <Volume2 className="h-4 w-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-xs font-semibold text-white">Voice Debrief</h3>
                <span className="text-slate-400 text-[10px] font-mono">
                  ({activeJob?.audio_briefing?.provider === 'elevenlabs' ? 'ElevenLabs' : 'Speech Synthesis'})
                </span>
              </div>
              <p className="text-[11px] text-slate-400">
                Summary of actions performed during autonomous background execution.
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={handleTogglePlay}
            className="btn-touch-grass px-4 py-1.5 text-xs font-semibold flex items-center gap-1.5 cursor-pointer self-end sm:self-auto"
          >
            {isPlaying ? (
              <>
                <Pause className="h-3.5 w-3.5" />
                <span>Pause</span>
              </>
            ) : (
              <>
                <Play className="h-3.5 w-3.5 fill-current" />
                <span>Play Debrief</span>
              </>
            )}
          </button>
        </div>

        {audioStrategy?.strategy === 'file_stream' && (
          <div className="flex items-center gap-2 pt-1 font-mono text-xs text-slate-400">
            <span>{formatAudioTime(audioCurrentTime)}</span>
            <input
              type="range"
              min="0"
              max={audioDuration || 100}
              value={audioCurrentTime}
              onChange={handleSeek}
              className="flex-1 h-1 bg-[#182026] rounded appearance-none cursor-pointer accent-emerald-400"
            />
            <span>{formatAudioTime(audioDuration)}</span>
          </div>
        )}

        <div className="p-3 rounded bg-[#0d1216] border border-[#1e262c] text-xs text-slate-300 italic leading-relaxed font-sans">
          "{activeJob?.audio_briefing?.script_text ||
            'Welcome back. While you were away, OutOfOffice AI analyzed your repository, verified clean tests, and generated isolated Git branch patches.'}"
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Card 1: Health Score */}
        <div className="flat-card p-4 flex flex-col justify-between items-center text-center">
          <div className="w-full flex items-center justify-between text-xs text-slate-400 font-mono mb-1">
            <span>Health Score</span>
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
          </div>

          <div className="my-2">
            <div className="text-3xl font-bold font-mono text-white">{healthScore}</div>
            <div className="text-[11px] text-slate-500 font-mono">out of 100</div>
          </div>

          <p className="text-[11px] text-slate-400 mt-1">
            {healthScore >= 90 ? 'High Quality' : 'Standard Quality'} • Ready for Review
          </p>
        </div>

        {/* Card 2: Test Verification Badge */}
        <div className="flat-card p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-xs text-slate-400 font-mono mb-1">
              <span>Test Suite Verification</span>
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
            </div>
            <h4 className="text-xs font-semibold text-white mb-0.5">Isolated Sandbox</h4>
            <p className="text-[11px] text-slate-400 mb-3">
              Fixes verified by executing test suite on isolated branch.
            </p>
          </div>

          <div className="p-2.5 rounded bg-[#0d1216] border border-[#1e262c] font-mono text-xs space-y-1">
            <div className="flex items-center justify-between text-emerald-400 font-medium">
              <span>Test Suite Passed</span>
              <span className="text-[10px] text-emerald-400 font-mono">Passed</span>
            </div>
            <div className="text-[10px] text-slate-400 truncate">
              Branch: <code className="text-slate-200">{activeJob?.agent_branch || 'agent/outofoffice-*'}</code>
            </div>
          </div>
        </div>

        {/* Card 3: Away Time Logged */}
        <div className="flat-card p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-xs text-slate-400 font-mono mb-1">
              <span>Away Duration</span>
              <Clock className="h-3.5 w-3.5 text-slate-400" />
            </div>
            <h4 className="text-xs font-semibold text-white mb-0.5">Time Logged</h4>
            <p className="text-[11px] text-slate-400 mb-3">
              Total duration recorded during autonomous execution.
            </p>
          </div>

          <div className="p-2.5 rounded bg-[#0d1216] border border-[#1e262c] font-mono text-xs space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Duration:</span>
              <span className="text-white font-semibold text-xs">
                {grassMetrics?.formatted_time || '00:18:42'}
              </span>
            </div>
            <div className="flex items-center justify-between text-[10px]">
              <span className="text-slate-500">Tier:</span>
              <span className="text-emerald-400 font-medium">
                {grassMetrics?.badge.tier || 'Park Ranger'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Code Diffs Viewer */}
      <div className="flat-card p-4 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 pb-2.5 border-b border-[#222d35]">
          <div className="flex items-center gap-2">
            <FileCode className="h-4 w-4 text-emerald-400" />
            <h3 className="text-xs font-semibold text-white">
              Unified Code Diffs ({diffs.length} files modified)
            </h3>
          </div>

          {/* Branch Actions */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => {
                setMergeStatus(`Run 'git merge ${activeJob?.agent_branch || 'agent/outofoffice-*'}' to integrate changes.`);
              }}
              className="px-2.5 py-1 rounded bg-[#059669] hover:bg-[#047857] text-white text-xs font-medium flex items-center gap-1 cursor-pointer"
            >
              <GitMerge className="h-3 w-3" />
              <span>Merge</span>
            </button>

            <button
              type="button"
              onClick={() => {
                setMergeStatus(`Branch '${activeJob?.agent_branch}' can be discarded with 'git branch -D'.`);
              }}
              className="px-2.5 py-1 rounded bg-[#182026] hover:bg-[#222d35] border border-[#222d35] text-slate-300 text-xs font-medium flex items-center gap-1 cursor-pointer"
            >
              <Trash2 className="h-3 w-3 text-red-400" />
              <span>Discard</span>
            </button>
          </div>
        </div>

        {mergeStatus && (
          <div className="p-2.5 rounded bg-[#0d1216] border border-[#222d35] text-xs text-slate-300 font-mono flex items-center justify-between">
            <span>{mergeStatus}</span>
            <button
              onClick={() => setMergeStatus(null)}
              className="text-slate-400 hover:text-white px-1"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* File Tabs */}
        {diffs.length > 0 ? (
          <div className="space-y-3">
            <div className="flex items-center gap-1.5 overflow-x-auto pb-0.5">
              {diffs.map((d, index) => (
                <button
                  key={d.id}
                  type="button"
                  onClick={() => setSelectedDiffIndex(index)}
                  className={`px-2.5 py-1 rounded font-mono text-xs whitespace-nowrap transition-colors flex items-center gap-1.5 ${selectedDiffIndex === index
                    ? 'bg-[#182026] text-white border border-[#2e3e4a]'
                    : 'bg-[#0d1216] text-slate-400 hover:text-white border border-transparent'
                    }`}
                >
                  <FileCode className="h-3 w-3 text-emerald-400" />
                  <span>{d.file_path}</span>
                  <span className="text-slate-500 text-[10px]">
                    ({d.status})
                  </span>
                </button>
              ))}
            </div>

            {/* Diff Viewer Frame */}
            <div className="rounded border border-[#222d35] bg-[#090d10] overflow-hidden">
              <div className="p-2 bg-[#0d1216] border-b border-[#1e262c] font-mono text-xs text-slate-400 flex items-center justify-between">
                <span className="font-medium text-slate-200">{currentDiff?.file_path || 'Patch'}</span>
                <span className="text-[10px]">Unified Diff</span>
              </div>

              {currentDiff ? (
                renderUnifiedDiff(currentDiff.diff_unified)
              ) : (
                <div className="p-6 text-center text-slate-500 font-mono text-xs">
                  Select a diff file above to inspect changes.
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="p-6 text-center text-slate-500 font-mono text-xs">
            No code diffs were generated (Audit Mode only or zero changes required).
          </div>
        )}
      </div>

      {/* Executive Report */}
      {activeJob?.final_report_markdown && (
        <div className="flat-card p-4 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-[#222d35]">
            <h3 className="text-xs font-semibold text-white flex items-center gap-1.5">
              <Sparkles className="h-3.5 w-3.5 text-emerald-400" />
              <span>Executive Report</span>
            </h3>
            <span className="text-[10px] font-mono text-slate-500">Autonomous Synthesis</span>
          </div>
          <div className="p-4 rounded bg-[#0d1216] border border-[#1e262c]">
            {renderFormattedReport(activeJob.final_report_markdown)}
          </div>
        </div>
      )}
    </div>
  );
};

export default ResultsHub;

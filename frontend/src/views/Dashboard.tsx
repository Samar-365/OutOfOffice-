/**
 * Screen 1: Mission Control Dashboard
 * Flat, minimalist, professional developer UI with zero emojis.
 */

import React, { useState, useEffect } from 'react';
import { useJob } from '../context/JobContext';
import { JobMode } from '../types';
import {
  FolderGit2,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  Wrench,
  ShieldCheck,
  GitBranch,
  FileCode,
  Clock,
  ArrowRight,
  RefreshCw,
  Search,
  Zap,
  Play,
} from 'lucide-react';

interface DashboardProps {
  onNavigate: (screen: 'dashboard' | 'trace' | 'results') => void;
}

interface PresetPrompt {
  id: string;
  title: string;
  subtitle: string;
  prompt: string;
  icon: React.ReactNode;
  recommendedMode: JobMode;
}

const PRESETS: PresetPrompt[] = [
  {
    id: 'dead-code',
    title: 'Find Dead Code & Prune',
    subtitle: 'Unused imports, unreachable functions & dead exports',
    prompt: 'Scan the repository for unused imports, dead functions, unreferenced exports, and unused local variables. Verify with AST analysis and safely report or remove them.',
    icon: <Sparkles className="h-3.5 w-3.5 text-emerald-400" />,
    recommendedMode: 'AUDIT',
  },
  {
    id: 'fix-tests',
    title: 'Fix Failing Tests',
    subtitle: 'Run test suite, find AST bugs & generate green fixes',
    prompt: 'Execute the project test suite, locate failing assertions or unhandled exceptions, investigate root causes in the codebase AST, and synthesize minimal green patches.',
    icon: <Wrench className="h-3.5 w-3.5 text-amber-400" />,
    recommendedMode: 'FIX',
  },
  {
    id: 'full-audit',
    title: 'Full Repository Audit',
    subtitle: 'Security checks, linter diagnostics & test coverage',
    prompt: 'Run comprehensive security, lint, test, and dead code audits across all project modules, generating an executive health score and action plan.',
    icon: <ShieldCheck className="h-3.5 w-3.5 text-sky-400" />,
    recommendedMode: 'AUDIT',
  },
  {
    id: 'modernize',
    title: 'Modernize & Optimize',
    subtitle: 'Refactor legacy code & apply modern idioms',
    prompt: 'Analyze legacy code patterns, modernize deprecated syntax, optimize slow loops or synchronous bottlenecks, and ensure standard coding practices.',
    icon: <Zap className="h-3.5 w-3.5 text-purple-400" />,
    recommendedMode: 'FIX',
  },
];

export const Dashboard: React.FC<DashboardProps> = ({ onNavigate }) => {
  const {
    validateRepo,
    launchJob,
    isValidatingRepo,
    repoMetadata,
    recentJobs,
    isLaunching,
    error: storeError,
    selectJob,
  } = useJob();

  // Local form state
  const [repoPath, setRepoPath] = useState<string>('');
  const [taskPrompt, setTaskPrompt] = useState<string>(PRESETS[0].prompt);
  const [activePresetId, setActivePresetId] = useState<string>(PRESETS[0].id);
  const [selectedMode, setSelectedMode] = useState<JobMode>('AUDIT');
  const [validationSuccess, setValidationSuccess] = useState<boolean | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    if (!repoPath) {
      const defaultPath = '.';
      setRepoPath(defaultPath);
      handleValidation(defaultPath);
    }
  }, []);

  const handleValidation = async (path: string) => {
    setLocalError(null);
    if (!path.trim()) {
      setValidationSuccess(null);
      return;
    }
    const isValid = await validateRepo(path.trim());
    setValidationSuccess(isValid);
  };

  const handleSelectPreset = (preset: PresetPrompt) => {
    setActivePresetId(preset.id);
    setTaskPrompt(preset.prompt);
    setSelectedMode(preset.recommendedMode);
  };

  const handleGoTouchGrass = async () => {
    setLocalError(null);
    if (!repoPath.trim()) {
      setLocalError('Please enter a repository directory path.');
      return;
    }
    if (!taskPrompt.trim()) {
      setLocalError('Please enter or select a task prompt.');
      return;
    }

    const job = await launchJob(repoPath.trim(), taskPrompt.trim(), selectedMode);
    if (job) {
      onNavigate('trace');
    }
  };

  const handleSelectRecentJob = async (jobId: string) => {
    await selectJob(jobId);
    onNavigate('trace');
  };

  return (
    <div className="space-y-6">
      {/* Top Bar: Mission Control Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#222d35]">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <span>Mission Control</span>
          </h1>
          <p className="text-slate-400 text-xs mt-0.5">
            Dispatch autonomous tasks and step away from your workstation.
          </p>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          {/* Section 1: Repository Path Input */}
          <div className="flat-card p-5 space-y-3">
            <div className="flex items-center justify-between">
              <label htmlFor="repo-path-input" className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                <FolderGit2 className="h-3.5 w-3.5 text-emerald-400" />
                Target Repository
              </label>
            </div>

            <div className="flex items-center gap-2">
              <div className="relative flex-1">
                <input
                  id="repo-path-input"
                  type="text"
                  value={repoPath}
                  onChange={(e) => {
                    setRepoPath(e.target.value);
                    setValidationSuccess(null);
                  }}
                  onBlur={() => handleValidation(repoPath)}
                  onKeyDown={(e) => e.key === 'Enter' && handleValidation(repoPath)}
                  placeholder="e.g. . or /path/to/project"
                  className="w-full flat-input px-3 py-2 text-xs font-mono"
                />
                {isValidatingRepo && (
                  <div className="absolute right-3 top-2.5">
                    <RefreshCw className="h-3.5 w-3.5 text-emerald-400 animate-spin" />
                  </div>
                )}
              </div>

              <button
                type="button"
                onClick={() => handleValidation(repoPath)}
                disabled={isValidatingRepo}
                className="btn-secondary px-3 py-2 text-xs whitespace-nowrap"
              >
                <Search className="h-3 w-3 text-slate-400" />
                Validate
              </button>
            </div>

            {/* Validation Feedback */}
            {validationSuccess === true && repoMetadata && (
              <div className="p-3 rounded bg-[#0d1216] border border-[#222d35] text-xs space-y-1.5">
                <div className="flex items-center justify-between font-mono">
                  <div className="flex items-center gap-1.5 text-emerald-400 font-medium">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    <span>Valid Repository: {repoMetadata.repo_path.split(/[\\/]/).pop() || repoMetadata.repo_path}</span>
                  </div>
                  <div className="flex items-center gap-1 text-slate-400">
                    <GitBranch className="h-3 w-3 text-slate-400" />
                    <span>{repoMetadata.current_branch || 'main'}</span>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-3 text-slate-400 pt-1 border-t border-[#182026] text-[11px]">
                  <div className="flex items-center gap-1">
                    <FileCode className="h-3 w-3 text-slate-500" />
                    <span>{repoMetadata.total_files} files</span>
                  </div>
                  {repoMetadata.languages && repoMetadata.languages.length > 0 && (
                    <div>
                      <span>Languages: </span>
                      <span className="text-slate-300 font-medium">
                        {repoMetadata.languages.join(', ')}
                      </span>
                    </div>
                  )}
                  {repoMetadata.test_framework && (
                    <div>
                      <span>Test Suite: </span>
                      <span className="text-slate-300 font-medium">
                        {repoMetadata.test_framework}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {validationSuccess === false && (
              <div className="p-2.5 rounded bg-red-950/20 border border-red-500/20 text-xs text-red-300 flex items-center gap-2">
                <AlertCircle className="h-3.5 w-3.5 text-red-400 flex-shrink-0" />
                <span>{storeError || 'Directory does not exist or is not a valid git repository.'}</span>
              </div>
            )}
          </div>

          {/* Section 2: Task Prompt Input & Presets */}
          <div className="flat-card p-5 space-y-3">
            <div className="flex items-center justify-between">
              <label htmlFor="task-prompt-textarea" className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                <Sparkles className="h-3.5 w-3.5 text-emerald-400" />
                Task Directive
              </label>
            </div>

            {/* Presets Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {PRESETS.map((preset) => (
                <button
                  key={preset.id}
                  type="button"
                  onClick={() => handleSelectPreset(preset)}
                  className={`p-3 rounded border text-left transition-colors flex flex-col justify-between ${activePresetId === preset.id
                    ? 'bg-[#182026] border-emerald-500/50'
                    : 'bg-[#0d1216] border-[#222d35] hover:border-[#33434f]'
                    }`}
                >
                  <div className="flex items-center gap-1.5 mb-1">
                    {preset.icon}
                    <span className="text-xs font-semibold text-white">{preset.title}</span>
                  </div>
                  <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">
                    {preset.subtitle}
                  </p>
                </button>
              ))}
            </div>

            {/* Custom Task Textarea */}
            <textarea
              id="task-prompt-textarea"
              rows={3}
              value={taskPrompt}
              onChange={(e) => {
                setTaskPrompt(e.target.value);
                setActivePresetId('custom');
              }}
              placeholder="Describe your coding task or AST investigation in detail..."
              className="w-full flat-input p-3 text-xs leading-relaxed font-sans resize-none"
            />
          </div>
        </div>

        {/* Right Column (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          {/* Section 3: Mode Switcher */}
          <div className="flat-card p-5 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                Execution Mode
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setSelectedMode('AUDIT')}
                className={`p-3 rounded border flex flex-col items-center justify-center gap-1 text-center transition-colors ${selectedMode === 'AUDIT'
                  ? 'bg-[#182026] border-emerald-500/60 text-white'
                  : 'bg-[#0d1216] border-[#222d35] text-slate-400 hover:text-slate-200'
                  }`}
              >
                <ShieldCheck className={`h-4 w-4 ${selectedMode === 'AUDIT' ? 'text-emerald-400' : 'text-slate-400'}`} />
                <div>
                  <div className="text-xs font-medium">Audit Mode</div>
                  <div className="text-[10px] text-slate-400">Read-Only Scan</div>
                </div>
              </button>

              <button
                type="button"
                onClick={() => setSelectedMode('FIX')}
                className={`p-3 rounded border flex flex-col items-center justify-center gap-1 text-center transition-colors ${selectedMode === 'FIX'
                  ? 'bg-[#182026] border-amber-500/60 text-amber-200'
                  : 'bg-[#0d1216] border-[#222d35] text-slate-400 hover:text-slate-200'
                  }`}
              >
                <Wrench className={`h-4 w-4 ${selectedMode === 'FIX' ? 'text-amber-400' : 'text-slate-400'}`} />
                <div>
                  <div className="text-xs font-medium">Fix Mode</div>
                  <div className="text-[10px] text-slate-400">Isolated Branch</div>
                </div>
              </button>
            </div>

            <p className="text-[11px] text-slate-400 leading-relaxed bg-[#0d1216] p-2.5 rounded border border-[#1e262c]">
              {selectedMode === 'AUDIT' ? (
                <span>
                  <strong>Audit Mode:</strong> Analyzes AST, scans dependencies, and runs diagnostics with zero file modifications.
                </span>
              ) : (
                <span>
                  <strong>Fix Mode:</strong> Creates isolated <code className="text-amber-300 font-mono">agent/outofoffice-*</code> Git branch, applies verified AST patches, and runs test validation.
                </span>
              )}
            </p>
          </div>

          {/* Section 4: Primary Action */}
          <div className="flat-card p-5 space-y-3 text-center">
            {localError && (
              <div className="p-2.5 rounded bg-red-950/30 border border-red-500/30 text-xs text-red-300 text-left flex items-center gap-2">
                <AlertCircle className="h-3.5 w-3.5 text-red-400 flex-shrink-0" />
                <span>{localError}</span>
              </div>
            )}

            <div className="space-y-1">
              <h3 className="text-sm font-semibold text-white">Start Background Execution</h3>
              <p className="text-[11px] text-slate-400">
                Initiates background runner and opens real-time telemetry.
              </p>
            </div>

            <button
              type="button"
              onClick={handleGoTouchGrass}
              disabled={isLaunching}
              className="w-full btn-touch-grass py-2.5 text-xs font-semibold cursor-pointer disabled:opacity-50"
            >
              {isLaunching ? (
                <>
                  <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                  <span>Launching Agent...</span>
                </>
              ) : (
                <>
                  <Play className="h-3.5 w-3.5 fill-current" />
                  <span>Launch Task & View Telemetry</span>
                </>
              )}
            </button>

            <div className="flex items-center justify-center gap-1.5 text-[11px] text-slate-500 font-mono">
              <CheckCircle2 className="h-3 w-3 text-emerald-400" />
              <span>Safe to close browser after starting</span>
            </div>
          </div>

          {/* Section 5: Recent Missions */}
          {recentJobs.length > 0 && (
            <div className="flat-card p-4 space-y-2.5">
              <div className="flex items-center justify-between">
                <h4 className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                  <Clock className="h-3 w-3 text-slate-400" />
                  Recent Jobs
                </h4>
                <span className="text-[10px] text-slate-500 font-mono">{recentJobs.length} logged</span>
              </div>

              <div className="space-y-1.5 max-h-44 overflow-y-auto pr-1">
                {recentJobs.slice(0, 4).map((job) => (
                  <button
                    key={job.id}
                    type="button"
                    onClick={() => handleSelectRecentJob(job.id)}
                    className="w-full text-left p-2 rounded bg-[#0d1216] hover:bg-[#182026] border border-[#222d35] transition-colors flex items-center justify-between group"
                  >
                    <div className="truncate pr-2">
                      <div className="text-xs font-medium text-slate-200 truncate group-hover:text-emerald-400 transition-colors">
                        {job.task_prompt}
                      </div>
                      <div className="text-[10px] text-slate-500 font-mono truncate flex items-center gap-1.5 mt-0.5">
                        <span className={`inline-block w-1.5 h-1.5 rounded-full ${job.status === 'COMPLETED' ? 'bg-emerald-400' : job.status === 'RUNNING' ? 'bg-amber-400' : 'bg-slate-400'
                          }`}></span>
                        <span>{job.mode}</span>
                        <span>•</span>
                        <span>{job.created_at ? new Date(job.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Recent'}</span>
                      </div>
                    </div>
                    <ArrowRight className="h-3.5 w-3.5 text-slate-500 group-hover:text-emerald-400 group-hover:translate-x-0.5 transition-all flex-shrink-0" />
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;

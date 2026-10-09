/**
 * Screen 1: Mission Control Dashboard
 * Provides repository path validation, prompt presets, execution mode toggle,
 * and the hero "[ GO TOUCH GRASS ]" execution trigger.
 */

import React, { useState, useEffect } from 'react';
import { useJob } from '../context/JobContext';
import { JobMode } from '../types';
import {
  Trees,
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
  Cpu,
  RefreshCw,
  Search,
  Zap,
} from 'lucide-react';

interface DashboardProps {
  onNavigate: (screen: 'dashboard' | 'away' | 'trace' | 'results') => void;
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
    icon: <Sparkles className="h-4 w-4 text-emerald-400" />,
    recommendedMode: 'AUDIT',
  },
  {
    id: 'fix-tests',
    title: 'Fix Failing Tests',
    subtitle: 'Run test suite, find AST bugs & generate green fixes',
    prompt: 'Execute the project test suite, locate failing assertions or unhandled exceptions, investigate root causes in the codebase AST, and synthesize minimal green patches.',
    icon: <Wrench className="h-4 w-4 text-amber-400" />,
    recommendedMode: 'FIX',
  },
  {
    id: 'full-audit',
    title: 'Full Repository Audit',
    subtitle: 'Security checks, linter diagnostics & test coverage',
    prompt: 'Run comprehensive security, lint, test, and dead code audits across all project modules, generating an executive health score and action plan.',
    icon: <ShieldCheck className="h-4 w-4 text-sky-400" />,
    recommendedMode: 'AUDIT',
  },
  {
    id: 'modernize',
    title: 'Modernize & Optimize',
    subtitle: 'Refactor legacy code & apply modern idioms',
    prompt: 'Analyze legacy code patterns, modernize deprecated syntax, optimize slow loops or synchronous bottlenecks, and ensure standard coding practices.',
    icon: <Zap className="h-4 w-4 text-purple-400" />,
    recommendedMode: 'FIX',
  },
];

export const Dashboard: React.FC<DashboardProps> = ({ onNavigate }) => {
  const {
    validateRepo,
    launchJob,
    isValidatingRepo,
    repoMetadata,
    modelsStatus,
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

  // Set default repo path from window location or current workspace default if available
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
      // Transition immediately to the Away screen so user can step away from keyboard
      onNavigate('away');
    }
  };

  const handleSelectRecentJob = async (jobId: string) => {
    await selectJob(jobId);
    onNavigate('trace');
  };

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Top Bar: Mission Control Status */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-forest-800/40">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight flex items-center gap-3">
            <Trees className="h-7 w-7 text-grass-neon animate-pulse" />
            <span>Mission Control</span>
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Dispatch autonomous agent tasks and step away from your keyboard.
          </p>
        </div>

        {/* Ollama & Model Status Pill */}
        <div className="flex items-center gap-3 self-start sm:self-auto">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-forest-950/80 border border-forest-800/60 font-mono text-xs shadow-inner">
            <Cpu className="h-3.5 w-3.5 text-grass-neon" />
            <span className="text-slate-300">Model:</span>
            <span className="text-grass-neon font-bold">
              {modelsStatus?.default_model || 'gemma2:9b'}
            </span>
            <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
          </div>
        </div>
      </div>

      {/* Main Grid: Left Setup Pane, Right Config & CTA Pane */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column (7 cols): Repo Selection & Task Presets */}
        <div className="lg:col-span-7 space-y-6">
          {/* Section 1: Repository Path Input */}
          <div className="glass-card p-6 border border-forest-700/40 space-y-4">
            <div className="flex items-center justify-between">
              <label htmlFor="repo-path-input" className="text-sm font-bold text-white flex items-center gap-2">
                <FolderGit2 className="h-4 w-4 text-grass-neon" />
                Target Repository Path
              </label>
              <span className="text-xs text-slate-400 font-mono">Local Filesystem</span>
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
                  placeholder="e.g. . or /path/to/project or C:\Users\..."
                  className="w-full bg-dark-input/90 border border-forest-800/80 focus:border-grass-neon focus:ring-1 focus:ring-grass-neon rounded-xl px-4 py-2.5 text-sm text-slate-100 font-mono placeholder:text-slate-500 transition-all"
                />
                {isValidatingRepo && (
                  <div className="absolute right-3 top-3">
                    <RefreshCw className="h-4 w-4 text-grass-neon animate-spin" />
                  </div>
                )}
              </div>

              <button
                type="button"
                onClick={() => handleValidation(repoPath)}
                disabled={isValidatingRepo}
                className="btn-secondary px-4 py-2.5 text-xs font-semibold whitespace-nowrap"
              >
                <Search className="h-3.5 w-3.5 text-grass-neon" />
                Validate
              </button>
            </div>

            {/* Validation Feedback & Repo Metadata Card */}
            {validationSuccess === true && repoMetadata && (
              <div className="p-3.5 rounded-xl bg-forest-950/70 border border-emerald-500/30 text-xs space-y-2 animate-fade-in">
                <div className="flex items-center justify-between font-mono">
                  <div className="flex items-center gap-2 text-emerald-400 font-bold">
                    <CheckCircle2 className="h-4 w-4" />
                    <span>Valid Repository: {repoMetadata.repo_path.split(/[\\/]/).pop() || repoMetadata.repo_path}</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-slate-300">
                    <GitBranch className="h-3.5 w-3.5 text-grass-neon" />
                    <span>{repoMetadata.current_branch || 'main'}</span>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-3 text-slate-400 pt-1 border-t border-forest-800/40">
                  <div className="flex items-center gap-1">
                    <FileCode className="h-3 w-3 text-slate-400" />
                    <span>{repoMetadata.total_files} files</span>
                  </div>
                  {repoMetadata.languages && repoMetadata.languages.length > 0 && (
                    <div className="flex items-center gap-1">
                      <span>Languages:</span>
                      <span className="text-slate-200 font-semibold">
                        {repoMetadata.languages.join(', ')}
                      </span>
                    </div>
                  )}
                  {repoMetadata.test_framework && (
                    <div className="badge-grass text-[10px]">
                      Test Suite: {repoMetadata.test_framework}
                    </div>
                  )}
                </div>
              </div>
            )}

            {validationSuccess === false && (
              <div className="p-3 rounded-xl bg-red-950/40 border border-red-500/30 text-xs text-red-300 flex items-center gap-2">
                <AlertCircle className="h-4 w-4 text-red-400 flex-shrink-0" />
                <span>{storeError || 'Directory does not exist or is not a valid git repository.'}</span>
              </div>
            )}
          </div>

          {/* Section 2: Task Prompt Input & Presets */}
          <div className="glass-card p-6 border border-forest-700/40 space-y-4">
            <div className="flex items-center justify-between">
              <label htmlFor="task-prompt-textarea" className="text-sm font-bold text-white flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-grass-neon" />
                Task Instruction
              </label>
              <span className="text-xs text-slate-400 font-mono">Autonomous Directive</span>
            </div>

            {/* Presets Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {PRESETS.map((preset) => (
                <button
                  key={preset.id}
                  type="button"
                  onClick={() => handleSelectPreset(preset)}
                  className={`p-3 rounded-xl border text-left transition-all duration-200 cursor-pointer flex flex-col justify-between ${
                    activePresetId === preset.id
                      ? 'bg-forest-800/80 border-grass-neon/60 shadow-lg shadow-grass-neon/5 ring-1 ring-grass-neon/30'
                      : 'bg-dark-card/60 border-forest-800/60 hover:border-forest-700 hover:bg-forest-900/40'
                  }`}
                >
                  <div className="flex items-center gap-2 mb-1.5">
                    {preset.icon}
                    <span className="text-xs font-bold text-white">{preset.title}</span>
                  </div>
                  <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">
                    {preset.subtitle}
                  </p>
                </button>
              ))}
            </div>

            {/* Custom Task Textarea */}
            <div className="relative">
              <textarea
                id="task-prompt-textarea"
                rows={4}
                value={taskPrompt}
                onChange={(e) => {
                  setTaskPrompt(e.target.value);
                  setActivePresetId('custom');
                }}
                placeholder="Describe your coding task or AST investigation in detail..."
                className="w-full bg-dark-input/90 border border-forest-800/80 focus:border-grass-neon focus:ring-1 focus:ring-grass-neon rounded-xl p-3.5 text-sm text-slate-100 placeholder:text-slate-500 font-sans transition-all resize-none"
              />
            </div>
          </div>
        </div>

        {/* Right Column (5 cols): Mode Switcher, CTA, Recent Jobs */}
        <div className="lg:col-span-5 space-y-6">
          {/* Section 3: Mode Switcher */}
          <div className="glass-card p-6 border border-forest-700/40 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-bold text-white flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-grass-neon" />
                Execution Mode
              </span>
              <span className="badge-grass">Deterministic</span>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setSelectedMode('AUDIT')}
                className={`p-3.5 rounded-xl border flex flex-col items-center justify-center gap-2 text-center transition-all cursor-pointer ${
                  selectedMode === 'AUDIT'
                    ? 'bg-forest-800/90 border-grass-neon text-white shadow-md ring-1 ring-grass-neon/30'
                    : 'bg-dark-card/50 border-forest-800/60 text-slate-400 hover:text-slate-200 hover:border-forest-700'
                }`}
              >
                <ShieldCheck className={`h-5 w-5 ${selectedMode === 'AUDIT' ? 'text-grass-neon' : 'text-slate-400'}`} />
                <div>
                  <div className="text-xs font-bold">Audit Mode</div>
                  <div className="text-[10px] text-slate-400 mt-0.5">Read-Only Scan</div>
                </div>
              </button>

              <button
                type="button"
                onClick={() => setSelectedMode('FIX')}
                className={`p-3.5 rounded-xl border flex flex-col items-center justify-center gap-2 text-center transition-all cursor-pointer ${
                  selectedMode === 'FIX'
                    ? 'bg-amber-950/40 border-amber-500/80 text-amber-200 shadow-md ring-1 ring-amber-500/30'
                    : 'bg-dark-card/50 border-forest-800/60 text-slate-400 hover:text-slate-200 hover:border-forest-700'
                }`}
              >
                <Wrench className={`h-5 w-5 ${selectedMode === 'FIX' ? 'text-amber-400' : 'text-slate-400'}`} />
                <div>
                  <div className="text-xs font-bold">Fix Mode</div>
                  <div className="text-[10px] text-slate-400 mt-0.5">Isolated Branch</div>
                </div>
              </button>
            </div>

            <p className="text-[11px] text-slate-400 leading-relaxed bg-forest-950/50 p-2.5 rounded-lg border border-forest-900/60">
              {selectedMode === 'AUDIT' ? (
                <span>
                  🛡️ <strong>Audit Mode:</strong> LangGraph searches AST, audits dependencies, runs linters, and outputs diagnostic findings with zero repo modifications.
                </span>
              ) : (
                <span>
                  ⚡ <strong>Fix Mode:</strong> LangGraph creates an isolated <code className="text-amber-300 font-mono">agent/outofoffice-*</code> Git branch, writes verified diffs, runs test suites, and synthesizes an audio debrief.
                </span>
              )}
            </p>
          </div>

          {/* Section 4: Hero CTA - GO TOUCH GRASS */}
          <div className="glass-panel p-6 border border-forest-600/40 space-y-4 text-center relative overflow-hidden">
            <div className="absolute inset-0 bg-grass-neon/5 blur-2xl pointer-events-none"></div>

            {localError && (
              <div className="p-3 rounded-xl bg-red-950/60 border border-red-500/40 text-xs text-red-300 text-left flex items-center gap-2">
                <AlertCircle className="h-4 w-4 text-red-400 flex-shrink-0" />
                <span>{localError}</span>
              </div>
            )}

            <div className="space-y-1">
              <h3 className="text-lg font-bold text-white">Ready for Outdoor Freedom?</h3>
              <p className="text-xs text-slate-400">
                Clicking below initiates the background orchestrator and launches your away timer.
              </p>
            </div>

            <button
              type="button"
              onClick={handleGoTouchGrass}
              disabled={isLaunching}
              className="w-full btn-touch-grass py-4 text-base font-black tracking-wide flex items-center justify-center gap-3 animate-grass-pulse cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed shadow-xl shadow-grass-neon/20"
            >
              {isLaunching ? (
                <>
                  <RefreshCw className="h-5 w-5 animate-spin" />
                  <span>Launching Agent...</span>
                </>
              ) : (
                <>
                  <Trees className="h-6 w-6" />
                  <span>[ 🌳 GO TOUCH GRASS ]</span>
                </>
              )}
            </button>

            <div className="flex items-center justify-center gap-2 text-[11px] text-slate-500 font-mono">
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
              <span>Safe to close browser or lock screen once started</span>
            </div>
          </div>

          {/* Section 5: Recent Missions Drawer */}
          {recentJobs.length > 0 && (
            <div className="glass-card p-5 border border-forest-800/50 space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                  <Clock className="h-3.5 w-3.5 text-grass-neon" />
                  Recent Missions
                </h4>
                <span className="text-[10px] text-slate-500 font-mono">{recentJobs.length} logged</span>
              </div>

              <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                {recentJobs.slice(0, 4).map((job) => (
                  <button
                    key={job.id}
                    type="button"
                    onClick={() => handleSelectRecentJob(job.id)}
                    className="w-full text-left p-2.5 rounded-lg bg-dark-input/60 hover:bg-forest-900/40 border border-forest-800/40 hover:border-forest-700/80 transition-all flex items-center justify-between group cursor-pointer"
                  >
                    <div className="truncate pr-2">
                      <div className="text-xs font-bold text-slate-200 truncate group-hover:text-grass-neon transition-colors">
                        {job.task_prompt}
                      </div>
                      <div className="text-[10px] text-slate-500 font-mono truncate flex items-center gap-1.5 mt-0.5">
                        <span className={`inline-block w-1.5 h-1.5 rounded-full ${
                          job.status === 'COMPLETED' ? 'bg-emerald-400' : job.status === 'RUNNING' ? 'bg-amber-400 animate-pulse' : 'bg-slate-400'
                        }`}></span>
                        <span>{job.mode}</span>
                        <span>•</span>
                        <span>{job.created_at ? new Date(job.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Recent'}</span>
                      </div>
                    </div>
                    <ArrowRight className="h-3.5 w-3.5 text-slate-500 group-hover:text-grass-neon group-hover:translate-x-0.5 transition-all flex-shrink-0" />
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

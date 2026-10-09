/**
 * Screen 3: Live Agent Trace & Telemetry Visualizer
 * Real-time LangGraph execution timeline, Sentry waterfall spans, and expandable stdout/stderr terminal drawers.
 */

import React, { useState } from 'react';
import { useJob } from '../context/JobContext';
import { JobStep } from '../types';
import {
  Terminal,
  Activity,
  CheckCircle2,
  XCircle,
  Clock,
  Cpu,
  Wrench,
  Layers,
  ChevronDown,
  ChevronRight,
  Copy,
  Check,
  RefreshCw,
  AlertCircle,
  FileCode,
  Sparkles,
} from 'lucide-react';

interface TraceViewProps {
  onNavigate: (screen: 'dashboard' | 'away' | 'trace' | 'results') => void;
}

export const TraceView: React.FC<TraceViewProps> = ({ onNavigate }) => {
  const { activeJob, traces, refreshActiveJob } = useJob();

  const [expandedStepId, setExpandedStepId] = useState<string | null>(null);
  const [copiedStepId, setCopiedStepId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'timeline' | 'waterfall' | 'findings'>('timeline');
  const [filterQuery, setFilterQuery] = useState<string>('');
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);

  const handleManualRefresh = async () => {
    setIsRefreshing(true);
    await refreshActiveJob();
    setTimeout(() => setIsRefreshing(false), 400);
  };

  const handleCopyLogs = (step: JobStep) => {
    const text = `--- Step: ${step.step_name} (${step.tool_name || 'node'}) ---
Status: ${step.status}
Latency: ${step.latency_ms || 0}ms

[STDOUT]
${step.stdout || '(no stdout)'}

[STDERR]
${step.stderr || '(no stderr)'}
`;
    navigator.clipboard.writeText(text);
    setCopiedStepId(step.id);
    setTimeout(() => setCopiedStepId(null), 2000);
  };

  const steps = activeJob?.steps || [];
  const findings = activeJob?.findings || [];
  const spans = traces?.spans || [];

  // Filter steps by query
  const filteredSteps = steps.filter((s) => {
    if (!filterQuery) return true;
    const q = filterQuery.toLowerCase();
    return (
      s.step_name.toLowerCase().includes(q) ||
      (s.tool_name && s.tool_name.toLowerCase().includes(q)) ||
      (s.stdout && s.stdout.toLowerCase().includes(q)) ||
      (s.stderr && s.stderr.toLowerCase().includes(q))
    );
  });

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'SUCCESS':
        return <CheckCircle2 className="h-4 w-4 text-emerald-400" />;
      case 'RUNNING':
        return <RefreshCw className="h-4 w-4 text-amber-400 animate-spin" />;
      case 'FAILED':
        return <XCircle className="h-4 w-4 text-red-400" />;
      default:
        return <Clock className="h-4 w-4 text-slate-500" />;
    }
  };

  const getSpanColor = (op: string) => {
    if (op.startsWith('ai.model')) return 'bg-purple-500/80 border-purple-400';
    if (op.startsWith('ai.tool')) return 'bg-emerald-500/80 border-emerald-400';
    if (op.startsWith('langgraph')) return 'bg-cyan-500/80 border-cyan-400';
    return 'bg-slate-500/80 border-slate-400';
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Top Header & Metrics Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-forest-800/40">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight flex items-center gap-3">
              <Terminal className="h-7 w-7 text-grass-neon" />
              <span>Agent Telemetry Visualizer</span>
            </h1>
            <span
              className={`px-2.5 py-0.5 rounded-full text-xs font-mono font-bold uppercase tracking-wider ${
                activeJob?.status === 'RUNNING'
                  ? 'bg-amber-950/80 border border-amber-500/40 text-amber-400 animate-pulse'
                  : activeJob?.status === 'COMPLETED'
                  ? 'bg-forest-950/80 border border-emerald-500/40 text-emerald-400'
                  : 'bg-dark-card border border-forest-800 text-slate-400'
              }`}
            >
              {activeJob?.status || 'IDLE'}
            </span>
          </div>
          <p className="text-slate-400 text-sm mt-1 font-mono truncate max-w-2xl">
            {activeJob?.task_prompt || 'No active task selected.'}
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleManualRefresh}
            disabled={isRefreshing}
            className="btn-secondary px-3 py-2 text-xs flex items-center gap-1.5"
            title="Refresh Trace Data"
          >
            <RefreshCw className={`h-3.5 w-3.5 text-grass-neon ${isRefreshing ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>

          <button
            type="button"
            onClick={() => onNavigate('results')}
            className="btn-primary px-3.5 py-2 text-xs flex items-center gap-1.5"
          >
            <Sparkles className="h-3.5 w-3.5" />
            <span>View Results Hub</span>
          </button>
        </div>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="glass-card p-4 border border-forest-800/50">
          <div className="text-xs text-slate-400 flex items-center gap-1.5 mb-1 font-mono">
            <Clock className="h-3.5 w-3.5 text-grass-neon" />
            <span>Total Latency</span>
          </div>
          <div className="text-xl font-bold font-mono text-white">
            {traces ? `${(traces.total_execution_ms / 1000).toFixed(2)}s` : '0.00s'}
          </div>
          <div className="text-[10px] text-slate-500 font-mono mt-0.5">
            Model: {traces ? `${(traces.model_inference_ms / 1000).toFixed(2)}s` : '0s'}
          </div>
        </div>

        <div className="glass-card p-4 border border-forest-800/50">
          <div className="text-xs text-slate-400 flex items-center gap-1.5 mb-1 font-mono">
            <Cpu className="h-3.5 w-3.5 text-purple-400" />
            <span>LLM Inferences</span>
          </div>
          <div className="text-xl font-bold font-mono text-white">
            {traces?.inferences_count || 0}
          </div>
          <div className="text-[10px] text-slate-500 font-mono mt-0.5">
            Gemma 2 9B Local
          </div>
        </div>

        <div className="glass-card p-4 border border-forest-800/50">
          <div className="text-xs text-slate-400 flex items-center gap-1.5 mb-1 font-mono">
            <Wrench className="h-3.5 w-3.5 text-emerald-400" />
            <span>Tool Calls</span>
          </div>
          <div className="text-xl font-bold font-mono text-white">
            {traces?.tool_calls_count || steps.length}
          </div>
          <div className="text-[10px] text-slate-500 font-mono mt-0.5">
            AST, Linters & Tests
          </div>
        </div>

        <div className="glass-card p-4 border border-forest-800/50">
          <div className="text-xs text-slate-400 flex items-center gap-1.5 mb-1 font-mono">
            <AlertCircle className="h-3.5 w-3.5 text-amber-400" />
            <span>Findings Logged</span>
          </div>
          <div className="text-xl font-bold font-mono text-white">
            {findings.length}
          </div>
          <div className="text-[10px] text-slate-500 font-mono mt-0.5">
            {activeJob?.diffs?.length || 0} Diffs Synthesized
          </div>
        </div>
      </div>

      {/* Tabs Switcher: Timeline vs Waterfall vs Findings */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        <div className="inline-flex p-1 bg-dark-input/80 rounded-xl border border-forest-800/60 font-mono text-xs">
          <button
            type="button"
            onClick={() => setViewMode('timeline')}
            className={`px-4 py-2 rounded-lg font-bold transition-all flex items-center gap-2 cursor-pointer ${
              viewMode === 'timeline'
                ? 'bg-forest-800 text-white shadow-sm ring-1 ring-grass-neon/30'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Layers className="h-3.5 w-3.5 text-grass-neon" />
            <span>Step Timeline ({steps.length})</span>
          </button>

          <button
            type="button"
            onClick={() => setViewMode('waterfall')}
            className={`px-4 py-2 rounded-lg font-bold transition-all flex items-center gap-2 cursor-pointer ${
              viewMode === 'waterfall'
                ? 'bg-forest-800 text-white shadow-sm ring-1 ring-grass-neon/30'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Activity className="h-3.5 w-3.5 text-purple-400" />
            <span>Sentry Waterfall ({spans.length})</span>
          </button>

          <button
            type="button"
            onClick={() => setViewMode('findings')}
            className={`px-4 py-2 rounded-lg font-bold transition-all flex items-center gap-2 cursor-pointer ${
              viewMode === 'findings'
                ? 'bg-forest-800 text-white shadow-sm ring-1 ring-grass-neon/30'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <FileCode className="h-3.5 w-3.5 text-amber-400" />
            <span>Findings ({findings.length})</span>
          </button>
        </div>

        {/* Filter / Search input */}
        <div className="relative w-full sm:w-64">
          <input
            type="text"
            value={filterQuery}
            onChange={(e) => setFilterQuery(e.target.value)}
            placeholder="Filter logs or tools..."
            className="w-full bg-dark-input/90 border border-forest-800/80 focus:border-grass-neon rounded-xl pl-8 pr-3 py-1.5 text-xs text-slate-100 font-mono placeholder:text-slate-500"
          />
          <Terminal className="h-3.5 w-3.5 text-slate-500 absolute left-2.5 top-2.5" />
        </div>
      </div>

      {/* TAB 1: Step Timeline with Expandable Drawers */}
      {viewMode === 'timeline' && (
        <div className="space-y-3">
          {filteredSteps.length === 0 ? (
            <div className="glass-card p-12 text-center border border-forest-800/50 space-y-3">
              <Terminal className="h-10 w-10 text-slate-600 mx-auto" />
              <div className="text-sm text-slate-300 font-bold">No telemetry steps logged yet</div>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Once the agent begins executing AST discovery, testing, or patching, live step telemetry will stream here in real time.
              </p>
            </div>
          ) : (
            filteredSteps.map((step, idx) => {
              const isExpanded = expandedStepId === step.id;
              return (
                <div
                  key={step.id}
                  className="glass-card border border-forest-800/60 overflow-hidden transition-all duration-200"
                >
                  {/* Step Header Row */}
                  <div
                    onClick={() => setExpandedStepId(isExpanded ? null : step.id)}
                    className="p-3.5 flex items-center justify-between gap-3 cursor-pointer hover:bg-forest-900/30 transition-colors"
                  >
                    <div className="flex items-center gap-3 truncate">
                      <div className="flex items-center gap-1.5 font-mono text-xs text-slate-500">
                        <span className="w-5 text-right font-bold text-grass-neon">#{idx + 1}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        {getStatusIcon(step.status)}
                        <span className="text-xs font-bold text-white truncate">
                          {step.step_name}
                        </span>
                      </div>
                      {step.tool_name && (
                        <span className="badge-grass text-[10px] font-mono">
                          {step.tool_name}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-3 font-mono text-xs text-slate-400 flex-shrink-0">
                      {step.latency_ms !== null && step.latency_ms !== undefined && (
                        <span className="text-slate-500">
                          {step.latency_ms}ms
                        </span>
                      )}
                      {isExpanded ? (
                        <ChevronDown className="h-4 w-4 text-grass-neon" />
                      ) : (
                        <ChevronRight className="h-4 w-4 text-slate-500" />
                      )}
                    </div>
                  </div>

                  {/* Expandable Terminal Logs Drawer */}
                  {isExpanded && (
                    <div className="border-t border-forest-900/80 bg-dark-bg/95 p-4 space-y-3 font-mono text-xs animate-fade-in">
                      <div className="flex items-center justify-between text-slate-400 pb-1 border-b border-forest-900">
                        <span className="font-bold flex items-center gap-1.5 text-slate-300">
                          <Terminal className="h-3.5 w-3.5 text-grass-neon" />
                          Execution Output & Telemetry
                        </span>
                        <button
                          type="button"
                          onClick={() => handleCopyLogs(step)}
                          className="hover:text-white flex items-center gap-1 text-[11px] px-2 py-0.5 rounded bg-forest-900/60 border border-forest-800"
                        >
                          {copiedStepId === step.id ? (
                            <>
                              <Check className="h-3 w-3 text-emerald-400" />
                              <span className="text-emerald-400">Copied!</span>
                            </>
                          ) : (
                            <>
                              <Copy className="h-3 w-3 text-slate-400" />
                              <span>Copy Raw</span>
                            </>
                          )}
                        </button>
                      </div>

                      {/* STDOUT Block */}
                      {step.stdout && (
                        <div className="space-y-1">
                          <div className="text-[10px] uppercase font-bold text-emerald-400 tracking-wider">
                            Stdout
                          </div>
                          <pre className="p-3 rounded-lg bg-forest-950/90 border border-forest-900/60 text-slate-200 overflow-x-auto text-[11px] leading-relaxed max-h-60 overflow-y-auto whitespace-pre-wrap">
                            {step.stdout}
                          </pre>
                        </div>
                      )}

                      {/* STDERR Block */}
                      {step.stderr && (
                        <div className="space-y-1">
                          <div className="text-[10px] uppercase font-bold text-red-400 tracking-wider">
                            Stderr / Diagnostics
                          </div>
                          <pre className="p-3 rounded-lg bg-red-950/40 border border-red-900/60 text-red-200 overflow-x-auto text-[11px] leading-relaxed max-h-60 overflow-y-auto whitespace-pre-wrap">
                            {step.stderr}
                          </pre>
                        </div>
                      )}

                      {!step.stdout && !step.stderr && (
                        <div className="text-slate-500 italic text-[11px] py-2">
                          (No output was produced by this node execution)
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      )}

      {/* TAB 2: Sentry Waterfall Visualizer */}
      {viewMode === 'waterfall' && (
        <div className="glass-card p-5 border border-forest-800/60 space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-forest-900/80">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Activity className="h-4 w-4 text-purple-400" />
                Sentry Agent Spans & Waterfall Breakdown
              </h3>
              <p className="text-[11px] text-slate-400 font-mono mt-0.5">
                Latency profiling for AI agent nodes, model inferences, and tool executions.
              </p>
            </div>
            <div className="flex items-center gap-3 text-[11px] font-mono">
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded-full bg-cyan-400"></span> Node
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded-full bg-purple-400"></span> Model
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400"></span> Tool
              </span>
            </div>
          </div>

          {spans.length === 0 ? (
            <div className="p-8 text-center text-slate-500 font-mono text-xs">
              No Sentry spans captured yet for this job.
            </div>
          ) : (
            <div className="space-y-2 font-mono text-xs">
              {spans.map((span) => {
                const duration = span.duration_ms || 10;
                const totalMs = traces?.total_execution_ms || 1000;
                const widthPercent = Math.max(4, Math.min(100, (duration / totalMs) * 100));

                return (
                  <div
                    key={span.span_id}
                    className="p-2.5 rounded-lg bg-dark-input/60 border border-forest-900/70 hover:border-forest-700/80 space-y-1.5 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 truncate">
                        <span className="text-[11px] text-slate-400 font-bold">
                          [{span.op}]
                        </span>
                        <span className="text-xs text-white truncate">
                          {span.description}
                        </span>
                      </div>
                      <span className="text-xs text-grass-neon font-bold flex-shrink-0">
                        {duration}ms
                      </span>
                    </div>

                    {/* Visual Gantt Bar */}
                    <div className="w-full bg-forest-950 rounded-full h-2 overflow-hidden">
                      <div
                        className={`h-full rounded-full ${getSpanColor(span.op)}`}
                        style={{ width: `${widthPercent}%` }}
                      ></div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: Findings List */}
      {viewMode === 'findings' && (
        <div className="space-y-3">
          {findings.length === 0 ? (
            <div className="glass-card p-12 text-center border border-forest-800/50 space-y-2">
              <CheckCircle2 className="h-10 w-10 text-emerald-400 mx-auto" />
              <div className="text-sm font-bold text-white">Zero issues or dead code found!</div>
              <p className="text-xs text-slate-400">
                The codebase passed all static inspections and linter rules cleanly.
              </p>
            </div>
          ) : (
            findings.map((f) => (
              <div
                key={f.id}
                className="glass-card p-4 border border-forest-800/60 space-y-2 hover:border-forest-700 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${
                        f.severity === 'HIGH'
                          ? 'bg-red-950/80 text-red-400 border border-red-500/40'
                          : f.severity === 'MEDIUM'
                          ? 'bg-amber-950/80 text-amber-400 border border-amber-500/40'
                          : 'bg-forest-950/80 text-emerald-400 border border-emerald-500/40'
                      }`}
                    >
                      {f.severity}
                    </span>
                    <span className="badge-grass text-[10px] font-mono">
                      {f.category}
                    </span>
                    {f.is_fixed && (
                      <span className="badge-grass bg-emerald-950/90 text-emerald-300 text-[10px]">
                        ✓ Fix Applied
                      </span>
                    )}
                  </div>

                  <span className="text-[11px] font-mono text-slate-500 truncate max-w-xs">
                    {f.file_path}{f.line_number ? `:${f.line_number}` : ''}
                  </span>
                </div>

                <p className="text-xs text-slate-200 leading-relaxed font-sans">
                  {f.description}
                </p>

                {f.evidence && (
                  <pre className="p-2 rounded bg-forest-950/80 border border-forest-900/60 font-mono text-[11px] text-slate-400 overflow-x-auto whitespace-pre-wrap">
                    {f.evidence}
                  </pre>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};

export default TraceView;

/**
 * Screen 3: Live Agent Trace & Telemetry Visualizer
 * Flat, minimalist, professional developer UI with zero emojis.
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
  ArrowRight,
} from 'lucide-react';

interface TraceViewProps {
  onNavigate: (screen: 'dashboard' | 'trace' | 'results') => void;
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
        return <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />;
      case 'RUNNING':
        return <RefreshCw className="h-3.5 w-3.5 text-amber-400 animate-spin" />;
      case 'FAILED':
        return <XCircle className="h-3.5 w-3.5 text-red-400" />;
      default:
        return <Clock className="h-3.5 w-3.5 text-slate-500" />;
    }
  };

  const getSpanColor = (op: string) => {
    if (op.startsWith('ai.model')) return 'bg-purple-500/80';
    if (op.startsWith('ai.tool')) return 'bg-emerald-500/80';
    if (op.startsWith('langgraph')) return 'bg-sky-500/80';
    return 'bg-slate-500/80';
  };

  return (
    <div className="space-y-5">
      {/* Top Header & Metrics Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#222d35]">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
              <Terminal className="h-5 w-5 text-emerald-400" />
              <span>Telemetry Visualizer</span>
            </h1>
            <span
              className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold uppercase tracking-wider ${activeJob?.status === 'RUNNING'
                ? 'bg-amber-950/40 border border-amber-500/30 text-amber-400'
                : activeJob?.status === 'COMPLETED'
                  ? 'bg-emerald-950/40 border border-emerald-500/30 text-emerald-400'
                  : 'bg-[#12181c] border border-[#222d35] text-slate-400'
                }`}
            >
              {activeJob?.status || 'IDLE'}
            </span>
          </div>
          <p className="text-slate-400 text-xs mt-0.5 font-mono truncate max-w-2xl">
            {activeJob?.task_prompt || 'No active task selected.'}
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleManualRefresh}
            disabled={isRefreshing}
            className="btn-secondary px-3 py-1.5 text-xs flex items-center gap-1.5"
            title="Refresh Trace Data"
          >
            <RefreshCw className={`h-3 w-3 text-slate-400 ${isRefreshing ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>

          <button
            type="button"
            onClick={() => onNavigate('results')}
            className="btn-primary px-3 py-1.5 text-xs flex items-center gap-1.5"
          >
            <span>Results Hub</span>
            <ArrowRight className="h-3 w-3" />
          </button>
        </div>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="flat-card p-3">
          <div className="text-[11px] text-slate-400 flex items-center gap-1 mb-0.5 font-mono">
            <Clock className="h-3 w-3 text-emerald-400" />
            <span>Total Latency</span>
          </div>
          <div className="text-base font-semibold font-mono text-white">
            {traces ? `${(traces.total_execution_ms / 1000).toFixed(2)}s` : '0.00s'}
          </div>
          <div className="text-[10px] text-slate-500 font-mono mt-0.5">
            Model: {traces ? `${(traces.model_inference_ms / 1000).toFixed(2)}s` : '0s'}
          </div>
        </div>

        <div className="flat-card p-3">
          <div className="text-[11px] text-slate-400 flex items-center gap-1 mb-0.5 font-mono">
            <Cpu className="h-3 w-3 text-purple-400" />
            <span>LLM Inferences</span>
          </div>
          <div className="text-base font-semibold font-mono text-white">
            {traces?.inferences_count || 0}
          </div>
          <div className="text-[10px] text-slate-500 font-mono mt-0.5">
            Gemma 2 9B Local
          </div>
        </div>

        <div className="flat-card p-3">
          <div className="text-[11px] text-slate-400 flex items-center gap-1 mb-0.5 font-mono">
            <Wrench className="h-3 w-3 text-emerald-400" />
            <span>Tool Calls</span>
          </div>
          <div className="text-base font-semibold font-mono text-white">
            {traces?.tool_calls_count || steps.length}
          </div>
          <div className="text-[10px] text-slate-500 font-mono mt-0.5">
            AST & Test Tools
          </div>
        </div>

        <div className="flat-card p-3">
          <div className="text-[11px] text-slate-400 flex items-center gap-1 mb-0.5 font-mono">
            <AlertCircle className="h-3.5 w-3.5 text-amber-400" />
            <span>Findings</span>
          </div>
          <div className="text-base font-semibold font-mono text-white">
            {findings.length}
          </div>
          <div className="text-[10px] text-slate-500 font-mono mt-0.5">
            {activeJob?.diffs?.length || 0} Diffs Generated
          </div>
        </div>
      </div>

      {/* Tabs Switcher */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="inline-flex p-1 bg-[#0d1216] rounded border border-[#222d35] font-mono text-xs">
          <button
            type="button"
            onClick={() => setViewMode('timeline')}
            className={`px-3 py-1 rounded transition-colors flex items-center gap-1.5 ${viewMode === 'timeline'
              ? 'bg-[#182026] text-white border border-[#2e3e4a]'
              : 'text-slate-400 hover:text-white'
              }`}
          >
            <Layers className="h-3 w-3 text-slate-400" />
            <span>Timeline ({steps.length})</span>
          </button>

          <button
            type="button"
            onClick={() => setViewMode('waterfall')}
            className={`px-3 py-1 rounded transition-colors flex items-center gap-1.5 ${viewMode === 'waterfall'
              ? 'bg-[#182026] text-white border border-[#2e3e4a]'
              : 'text-slate-400 hover:text-white'
              }`}
          >
            <Activity className="h-3 w-3 text-slate-400" />
            <span>Waterfall ({spans.length})</span>
          </button>

          <button
            type="button"
            onClick={() => setViewMode('findings')}
            className={`px-3 py-1 rounded transition-colors flex items-center gap-1.5 ${viewMode === 'findings'
              ? 'bg-[#182026] text-white border border-[#2e3e4a]'
              : 'text-slate-400 hover:text-white'
              }`}
          >
            <FileCode className="h-3 w-3 text-slate-400" />
            <span>Findings ({findings.length})</span>
          </button>
        </div>

        {/* Filter input */}
        <div className="relative w-full sm:w-56">
          <input
            type="text"
            value={filterQuery}
            onChange={(e) => setFilterQuery(e.target.value)}
            placeholder="Filter logs..."
            className="w-full flat-input pl-7 pr-3 py-1 text-xs font-mono"
          />
          <Terminal className="h-3 w-3 text-slate-500 absolute left-2.5 top-2.5" />
        </div>
      </div>

      {/* TAB 1: Step Timeline with Expandable Drawers */}
      {viewMode === 'timeline' && (
        <div className="space-y-2">
          {filteredSteps.length === 0 ? (
            <div className="flat-card p-10 text-center space-y-2">
              <Terminal className="h-8 w-8 text-slate-600 mx-auto" />
              <div className="text-xs text-slate-300 font-semibold">No telemetry steps logged yet</div>
              <p className="text-[11px] text-slate-500 max-w-xs mx-auto">
                Step telemetry will appear here once the agent begins execution.
              </p>
            </div>
          ) : (
            filteredSteps.map((step, idx) => {
              const isExpanded = expandedStepId === step.id;
              return (
                <div
                  key={step.id}
                  className="flat-card overflow-hidden"
                >
                  {/* Step Header Row */}
                  <div
                    onClick={() => setExpandedStepId(isExpanded ? null : step.id)}
                    className="p-3 flex items-center justify-between gap-3 cursor-pointer hover:bg-[#151d22] transition-colors"
                  >
                    <div className="flex items-center gap-2.5 truncate">
                      <span className="font-mono text-xs text-slate-500 w-4 text-right">
                        {idx + 1}
                      </span>
                      <div className="flex items-center gap-1.5">
                        {getStatusIcon(step.status)}
                        <span className="text-xs font-medium text-white truncate">
                          {step.step_name}
                        </span>
                      </div>
                      {step.tool_name && (
                        <span className="text-slate-400 text-[10px] font-mono">
                          ({step.tool_name})
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2.5 font-mono text-xs text-slate-400 flex-shrink-0">
                      {step.latency_ms !== null && step.latency_ms !== undefined && (
                        <span className="text-slate-500 text-[11px]">
                          {step.latency_ms}ms
                        </span>
                      )}
                      {isExpanded ? (
                        <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
                      ) : (
                        <ChevronRight className="h-3.5 w-3.5 text-slate-600" />
                      )}
                    </div>
                  </div>

                  {/* Expandable Terminal Logs Drawer */}
                  {isExpanded && (
                    <div className="border-t border-[#222d35] bg-[#090d10] p-3 space-y-2 font-mono text-xs">
                      <div className="flex items-center justify-between text-slate-400 pb-1 border-b border-[#182026]">
                        <span className="font-medium text-slate-300 text-[11px] flex items-center gap-1">
                          <Terminal className="h-3 w-3 text-emerald-400" />
                          Output Log
                        </span>
                        <button
                          type="button"
                          onClick={() => handleCopyLogs(step)}
                          className="hover:text-white flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-[#182026] border border-[#222d35]"
                        >
                          {copiedStepId === step.id ? (
                            <>
                              <Check className="h-3 w-3 text-emerald-400" />
                              <span className="text-emerald-400">Copied</span>
                            </>
                          ) : (
                            <>
                              <Copy className="h-3 w-3 text-slate-400" />
                              <span>Copy</span>
                            </>
                          )}
                        </button>
                      </div>

                      {/* STDOUT Block */}
                      {step.stdout && (
                        <div className="space-y-0.5">
                          <div className="text-[9px] uppercase font-semibold text-emerald-400 tracking-wider">
                            stdout
                          </div>
                          <pre className="p-2.5 rounded bg-[#0d1216] border border-[#1e262c] text-slate-200 overflow-x-auto text-[11px] leading-relaxed max-h-52 overflow-y-auto whitespace-pre-wrap">
                            {step.stdout}
                          </pre>
                        </div>
                      )}

                      {/* STDERR Block */}
                      {step.stderr && (
                        <div className="space-y-0.5">
                          <div className="text-[9px] uppercase font-semibold text-red-400 tracking-wider">
                            stderr
                          </div>
                          <pre className="p-2.5 rounded bg-red-950/20 border border-red-900/30 text-red-200 overflow-x-auto text-[11px] leading-relaxed max-h-52 overflow-y-auto whitespace-pre-wrap">
                            {step.stderr}
                          </pre>
                        </div>
                      )}

                      {!step.stdout && !step.stderr && (
                        <div className="text-slate-500 italic text-[11px] py-1">
                          (No output produced by this step)
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

      {/* TAB 2: Waterfall Visualizer */}
      {viewMode === 'waterfall' && (
        <div className="flat-card p-4 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-[#222d35]">
            <div>
              <h3 className="text-xs font-semibold text-white flex items-center gap-1.5">
                <Activity className="h-3.5 w-3.5 text-purple-400" />
                Execution Spans & Waterfall
              </h3>
            </div>
            <div className="flex items-center gap-3 text-[10px] font-mono text-slate-400">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded bg-sky-400"></span> Node
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded bg-purple-400"></span> Model
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded bg-emerald-400"></span> Tool
              </span>
            </div>
          </div>

          {spans.length === 0 ? (
            <div className="p-6 text-center text-slate-500 font-mono text-xs">
              No spans recorded yet.
            </div>
          ) : (
            <div className="space-y-1.5 font-mono text-xs">
              {spans.map((span) => {
                const duration = span.duration_ms || 10;
                const totalMs = traces?.total_execution_ms || 1000;
                const widthPercent = Math.max(4, Math.min(100, (duration / totalMs) * 100));

                return (
                  <div
                    key={span.span_id}
                    className="p-2 rounded bg-[#0d1216] border border-[#1e262c] space-y-1"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5 truncate">
                        <span className="text-[10px] text-slate-400 font-semibold">
                          [{span.op}]
                        </span>
                        <span className="text-xs text-white truncate">
                          {span.description}
                        </span>
                      </div>
                      <span className="text-xs text-emerald-400 font-semibold flex-shrink-0">
                        {duration}ms
                      </span>
                    </div>

                    <div className="w-full bg-[#182026] rounded-sm h-1.5 overflow-hidden">
                      <div
                        className={`h-full rounded-sm ${getSpanColor(span.op)}`}
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
        <div className="space-y-2">
          {findings.length === 0 ? (
            <div className="flat-card p-10 text-center space-y-1.5">
              <CheckCircle2 className="h-8 w-8 text-emerald-400 mx-auto" />
              <div className="text-xs font-semibold text-white">No issues detected</div>
              <p className="text-[11px] text-slate-400">
                The codebase passed all static inspections and linter rules cleanly.
              </p>
            </div>
          ) : (
            findings.map((f) => (
              <div
                key={f.id}
                className="flat-card p-3 space-y-1.5"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <span
                      className={`px-1.5 py-0.5 rounded text-[9px] font-mono font-semibold uppercase ${f.severity === 'HIGH'
                        ? 'bg-red-950/40 text-red-400 border border-red-500/30'
                        : f.severity === 'MEDIUM'
                          ? 'bg-amber-950/40 text-amber-400 border border-amber-500/30'
                          : 'bg-emerald-950/40 text-emerald-400 border border-emerald-500/30'
                        }`}
                    >
                      {f.severity}
                    </span>
                    <span className="text-slate-400 text-[10px] font-mono">
                      {f.category}
                    </span>
                    {f.is_fixed && (
                      <span className="text-emerald-400 text-[10px] font-mono">
                        (Fixed)
                      </span>
                    )}
                  </div>

                  <span className="text-[10px] font-mono text-slate-500 truncate max-w-xs">
                    {f.file_path}{f.line_number ? `:${f.line_number}` : ''}
                  </span>
                </div>

                <p className="text-xs text-slate-200 leading-relaxed font-sans">
                  {f.description}
                </p>

                {f.evidence && (
                  <pre className="p-2 rounded bg-[#0d1216] border border-[#1e262c] font-mono text-[10px] text-slate-400 overflow-x-auto whitespace-pre-wrap">
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

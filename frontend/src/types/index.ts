/**
 * OutOfOffice AI — TypeScript Type Definitions
 */

export type JobMode = 'AUDIT' | 'FIX';
export type JobStatus = 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
export type StepStatus = 'PENDING' | 'RUNNING' | 'SUCCESS' | 'FAILED' | 'SKIPPED';
export type FindingSeverity = 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';
export type FindingCategory =
  | 'DEAD_CODE'
  | 'TEST_FAILURE'
  | 'LINT_ERROR'
  | 'TYPE_ERROR'
  | 'UNUSED_DEPENDENCY'
  | 'SYNTAX_ERROR'
  | 'SECURITY_WARNING';

export interface JobStep {
  id: string;
  job_id: string;
  step_index: number;
  step_name: string;
  tool_name?: string | null;
  status: StepStatus;
  stdout?: string | null;
  stderr?: string | null;
  latency_ms?: number | null;
  created_at?: string | null;
}

export interface Finding {
  id: string;
  job_id: string;
  severity: FindingSeverity;
  category: FindingCategory;
  file_path: string;
  line_number?: number | null;
  description: string;
  evidence?: string | null;
  confidence: 'HIGH' | 'MEDIUM' | 'LOW';
  is_fixed: boolean;
  created_at?: string | null;
}

export interface CodeDiff {
  id: string;
  job_id: string;
  file_path: string;
  diff_unified: string;
  status: 'PROPOSED' | 'APPLIED' | 'VALIDATED' | 'ROLLED_BACK';
  created_at?: string | null;
}

export interface AudioBriefing {
  id: string;
  job_id: string;
  audio_path: string;
  script_text: string;
  duration_seconds?: number | null;
  provider: string;
  created_at?: string | null;
}

export interface Job {
  id: string;
  repo_path: string;
  task_prompt: string;
  mode: JobMode;
  status: JobStatus;
  base_branch?: string | null;
  agent_branch?: string | null;
  health_score?: number | null;
  final_report_markdown?: string | null;
  error_message?: string | null;
  created_at?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  away_duration_seconds?: number | null;
  steps?: JobStep[];
  findings?: Finding[];
  diffs?: CodeDiff[];
  audio_briefing?: AudioBriefing | null;
  step_count?: number;
  finding_count?: number;
  diff_count?: number;
  has_audio?: boolean;
}

export interface RepoMetadata {
  repo_path: string;
  is_git_repo: boolean;
  current_branch?: string | null;
  total_files: number;
  languages: string[];
  primary_language?: string | null;
  test_framework?: string | null;
  has_uncommitted_changes: boolean;
  untracked_files_count: number;
}

export interface RepoValidationResponse {
  valid?: boolean;
  is_valid?: boolean;
  message?: string;
  repo_path?: string;
  is_git_repo?: boolean;
  current_branch?: string | null;
  has_uncommitted_changes?: boolean;
  detected_languages?: string[];
  project_type?: string | null;
  manifest_files?: string[];
  test_framework?: string | null;
  file_count?: number;
  metadata?: RepoMetadata | null;
}

export interface GrassBadge {
  tier: string;
  icon: string;
  description: string;
}

export interface GrassMetrics {
  job_id: string;
  duration_seconds: number;
  minutes_away: number;
  formatted_time: string;
  human_readable: string;
  badge: GrassBadge;
  estimated_steps: number;
  screen_time_saved_minutes: number;
}

export interface CommunityGrassStats {
  total_completed_jobs: number;
  total_grass_touched_seconds: number;
  total_grass_touched_minutes: number;
  total_grass_touched_hours: number;
  formatted_total_time: string;
  longest_away_session_formatted: string;
  average_away_session_formatted: string;
  all_time_badge: GrassBadge;
}

export interface TraceSpan {
  span_id: string;
  job_id: string;
  op: string;
  description: string;
  status: string;
  duration_ms?: number | null;
  start_time?: string | null;
  end_time?: string | null;
  data?: Record<string, any>;
  tags?: Record<string, string>;
}

export interface TraceWaterfall {
  job_id: string;
  total_spans: number;
  total_execution_ms: number;
  tool_execution_ms: number;
  model_inference_ms: number;
  tool_calls_count: number;
  inferences_count: number;
  errors_count: number;
  spans: TraceSpan[];
}

export interface AudioStrategy {
  strategy: 'file_stream' | 'web_speech';
  stream_url?: string;
  audio_path?: string;
  file_size_bytes?: number;
  mime_type?: string;
  payload?: {
    job_id: string;
    type: string;
    text: string;
    voice_name?: string;
    rate?: number;
    pitch?: number;
    estimated_duration_seconds?: number;
  };
}

export interface ModelsStatus {
  ollama_running: boolean;
  default_model: string;
  installed_models: string[];
  has_default_model: boolean;
}

export interface HealthResponse {
  status: string;
  app_name: string;
  app_version: string;
  environment: string;
  default_model: string;
  timestamp: string;
}

export interface WebSocketEvent {
  type: string;
  job_id: string;
  timestamp: string;
  data: Record<string, any>;
}

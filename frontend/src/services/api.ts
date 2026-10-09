/**
 * REST API Client for OutOfOffice AI
 */

import {
  AudioStrategy,
  CommunityGrassStats,
  GrassMetrics,
  HealthResponse,
  Job,
  JobMode,
  ModelsStatus,
  RepoValidationResponse,
  TraceWaterfall,
} from '../types';

const API_BASE = '/api';

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = `Request failed with status ${res.status}`;
    try {
      const errJson = await res.json();
      if (errJson && errJson.detail) {
        errorDetail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // Ignore JSON parse failure on non-JSON error pages
    }
    throw new Error(errorDetail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  /** Health check */
  async getHealth(): Promise<HealthResponse> {
    const res = await fetch(`${API_BASE}/health`);
    return handleResponse<HealthResponse>(res);
  },

  /** Local Ollama status and models */
  async getModelsStatus(): Promise<ModelsStatus> {
    const res = await fetch(`${API_BASE}/jobs/models/status`);
    return handleResponse<ModelsStatus>(res);
  },

  /** Validate repository path */
  async validateRepo(repoPath: string): Promise<RepoValidationResponse> {
    const res = await fetch(`${API_BASE}/repo/validate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ repo_path: repoPath }),
    });
    return handleResponse<RepoValidationResponse>(res);
  },

  /** Create and start background job */
  async createJob(repoPath: string, taskPrompt: string, mode: JobMode = 'AUDIT'): Promise<Job> {
    const res = await fetch(`${API_BASE}/jobs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        repo_path: repoPath,
        task_prompt: taskPrompt,
        mode,
      }),
    });
    return handleResponse<Job>(res);
  },

  /** Get specific job details */
  async getJob(jobId: string): Promise<Job> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}`);
    return handleResponse<Job>(res);
  },

  /** List recent jobs */
  async listJobs(limit = 20, offset = 0): Promise<Job[]> {
    const res = await fetch(`${API_BASE}/jobs?limit=${limit}&offset=${offset}`);
    return handleResponse<Job[]>(res);
  },

  /** Rehydrate complete job state across browser restart */
  async rehydrateJob(jobId: string): Promise<Job> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/rehydrate`);
    return handleResponse<Job>(res);
  },

  /** Get unified diffs produced for job */
  async getJobDiffs(jobId: string): Promise<{ job_id: string; diffs: any[] }> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/diff`);
    return handleResponse<{ job_id: string; diffs: any[] }>(res);
  },

  /** Get step execution timeline */
  async getJobTimeline(jobId: string): Promise<{ job_id: string; timeline: any[] }> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/timeline`);
    return handleResponse<{ job_id: string; timeline: any[] }>(res);
  },

  /** Get Sentry tracing waterfall telemetry */
  async getJobTraces(jobId: string): Promise<TraceWaterfall> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/traces`);
    return handleResponse<TraceWaterfall>(res);
  },

  /** Get Touch Grass outdoor away metrics & badges */
  async getJobGrassMetrics(jobId: string): Promise<GrassMetrics> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/grass-metrics`);
    return handleResponse<GrassMetrics>(res);
  },

  /** Get community all-time screen-freedom stats */
  async getCommunityGrassStats(): Promise<CommunityGrassStats> {
    const res = await fetch(`${API_BASE}/jobs/community/grass-stats`);
    return handleResponse<CommunityGrassStats>(res);
  },

  /** Resolve audio playback strategy (file stream vs Web Speech API) */
  async getAudioStrategy(jobId: string): Promise<AudioStrategy> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/audio/strategy`);
    return handleResponse<AudioStrategy>(res);
  },

  /** Cancel active job */
  async cancelJob(jobId: string): Promise<Job> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/cancel`, {
      method: 'POST',
    });
    return handleResponse<Job>(res);
  },
};

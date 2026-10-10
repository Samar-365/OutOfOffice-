/**
 * Global Autonomous Job State Store & Context Provider
 */

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { api } from '../services/api';
import { wsClient } from '../services/websocket';
import {
  GrassMetrics,
  Job,
  JobMode,
  ModelsStatus,
  RepoMetadata,
  TraceWaterfall,
  WebSocketEvent,
} from '../types';

interface JobContextType {
  // Active State
  activeJob: Job | null;
  activeJobId: string | null;
  isLaunching: boolean;
  isValidatingRepo: boolean;
  repoMetadata: RepoMetadata | null;
  modelsStatus: ModelsStatus | null;
  recentJobs: Job[];
  grassMetrics: GrassMetrics | null;
  traces: TraceWaterfall | null;
  error: string | null;

  // Actions
  validateRepo: (path: string) => Promise<boolean>;
  launchJob: (repoPath: string, taskPrompt: string, mode: JobMode) => Promise<Job | null>;
  cancelActiveJob: () => Promise<void>;
  selectJob: (jobId: string) => Promise<void>;
  clearActiveJob: () => void;
  refreshActiveJob: () => Promise<void>;
}

const JobContext = createContext<JobContextType | undefined>(undefined);

const ACTIVE_JOB_KEY = 'outofoffice_active_job_id';

export const JobProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [activeJobId, setActiveJobId] = useState<string | null>(() => {
    return localStorage.getItem(ACTIVE_JOB_KEY);
  });
  const [activeJob, setActiveJob] = useState<Job | null>(null);
  const [recentJobs, setRecentJobs] = useState<Job[]>([]);
  const [repoMetadata, setRepoMetadata] = useState<RepoMetadata | null>(null);
  const [modelsStatus, setModelsStatus] = useState<ModelsStatus | null>(null);
  const [grassMetrics, setGrassMetrics] = useState<GrassMetrics | null>(null);
  const [traces, setTraces] = useState<TraceWaterfall | null>(null);
  const [isLaunching, setIsLaunching] = useState(false);
  const [isValidatingRepo, setIsValidatingRepo] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch models status & recent jobs on mount
  useEffect(() => {
    api.getModelsStatus()
      .then(setModelsStatus)
      .catch((e) => console.warn('Could not fetch models status:', e));

    api.listJobs(10, 0)
      .then(setRecentJobs)
      .catch((e) => console.warn('Could not fetch recent jobs:', e));
  }, []);

  // Fetch & Rehydrate active job if ID is present
  const loadJobData = useCallback(async (jobId: string) => {
    try {
      const jobData = await api.getJob(jobId);
      setActiveJob(jobData);

      // Fetch accompanying metrics
      api.getJobGrassMetrics(jobId)
        .then(setGrassMetrics)
        .catch(() => {});

      api.getJobTraces(jobId)
        .then(setTraces)
        .catch(() => {});
    } catch (err: any) {
      console.warn(`Could not load job ${jobId}:`, err);
    }
  }, []);

  useEffect(() => {
    if (activeJobId) {
      loadJobData(activeJobId);
      wsClient.connectJob(activeJobId);
    } else {
      setActiveJob(null);
      setGrassMetrics(null);
      setTraces(null);
      wsClient.connectGlobal();
    }
  }, [activeJobId, loadJobData]);

  // Handle live WebSocket telemetry events
  useEffect(() => {
    const unsubscribe = wsClient.subscribe((event: WebSocketEvent) => {
      // If event belongs to active job or is a lifecycle update
      if (activeJobId && event.job_id === activeJobId) {
        if (event.type === 'STEP_COMPLETED' || event.type === 'JOB_STARTED') {
          // Re-fetch updated job state
          loadJobData(activeJobId);
        } else if (event.type === 'JOB_COMPLETED' || event.type === 'JOB_FAILED' || event.type === 'JOB_CANCELLED') {
          loadJobData(activeJobId);
          api.listJobs(10, 0).then(setRecentJobs).catch(() => {});
        }
      }

      // If a new job was created or completed globally
      if (event.type === 'JOB_CREATED' || event.type === 'JOB_COMPLETED') {
        api.listJobs(10, 0).then(setRecentJobs).catch(() => {});
      }
    });

    return () => {
      unsubscribe();
    };
  }, [activeJobId, loadJobData]);

  const validateRepo = async (path: string): Promise<boolean> => {
    if (!path.trim()) {
      setRepoMetadata(null);
      return false;
    }
    setIsValidatingRepo(true);
    setError(null);
    try {
      const res = await api.validateRepo(path.trim());
      const isValid = Boolean(res.is_valid ?? res.valid);
      if (isValid) {
        const metadata: RepoMetadata = res.metadata || {
          repo_path: res.repo_path || path.trim(),
          is_git_repo: res.is_git_repo ?? true,
          current_branch: res.current_branch || 'main',
          total_files: res.file_count ?? 0,
          languages: res.detected_languages || [],
          primary_language: res.detected_languages?.[0] || null,
          test_framework: res.test_framework || null,
          has_uncommitted_changes: res.has_uncommitted_changes ?? false,
          untracked_files_count: 0,
        };
        setRepoMetadata(metadata);
        setError(null);
        return true;
      } else {
        setRepoMetadata(null);
        setError(res.message || 'Invalid repository path.');
        return false;
      }
    } catch (err: any) {
      setRepoMetadata(null);
      setError(err.message || 'Repository validation failed.');
      return false;
    } finally {
      setIsValidatingRepo(false);
    }
  };

  const launchJob = async (repoPath: string, taskPrompt: string, mode: JobMode): Promise<Job | null> => {
    setIsLaunching(true);
    setError(null);
    try {
      const created = await api.createJob(repoPath, taskPrompt, mode);
      setActiveJobId(created.id);
      localStorage.setItem(ACTIVE_JOB_KEY, created.id);
      setActiveJob(created);
      setRecentJobs((prev) => [created, ...prev]);
      return created;
    } catch (err: any) {
      setError(err.message || 'Failed to start autonomous job.');
      return null;
    } finally {
      setIsLaunching(false);
    }
  };

  const cancelActiveJob = async () => {
    if (!activeJobId) return;
    try {
      const updated = await api.cancelJob(activeJobId);
      setActiveJob(updated);
    } catch (err: any) {
      setError(err.message || 'Failed to cancel job.');
    }
  };

  const selectJob = async (jobId: string) => {
    setActiveJobId(jobId);
    localStorage.setItem(ACTIVE_JOB_KEY, jobId);
    await loadJobData(jobId);
  };

  const clearActiveJob = () => {
    setActiveJobId(null);
    localStorage.removeItem(ACTIVE_JOB_KEY);
    setActiveJob(null);
    setGrassMetrics(null);
    setTraces(null);
  };

  const refreshActiveJob = async () => {
    if (activeJobId) {
      await loadJobData(activeJobId);
    }
  };

  return (
    <JobContext.Provider
      value={{
        activeJob,
        activeJobId,
        isLaunching,
        isValidatingRepo,
        repoMetadata,
        modelsStatus,
        recentJobs,
        grassMetrics,
        traces,
        error,
        validateRepo,
        launchJob,
        cancelActiveJob,
        selectJob,
        clearActiveJob,
        refreshActiveJob,
      }}
    >
      {children}
    </JobContext.Provider>
  );
};

export const useJob = () => {
  const context = useContext(JobContext);
  if (!context) {
    throw new Error('useJob must be used within a JobProvider');
  }
  return context;
};

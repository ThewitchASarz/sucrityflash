import apiClient, { setAuthToken } from './client';
import {
  Evidence,
  HealthStatus,
  PendingApproval,
  Project,
  Run,
  RunStats,
  Scope,
  TimelineEvent
} from '../types';

export { setAuthToken };

export const getHealth = async (): Promise<HealthStatus> => {
  const response = await apiClient.get('/health');
  return response.data;
};

export const getProjects = async (): Promise<Project[]> => {
  const response = await apiClient.get('/api/v1/projects');
  return Array.isArray(response.data) ? response.data : [];
};

export const createProject = async (project: {
  name: string;
  customer_id: string;
  description?: string;
}): Promise<void> => {
  await apiClient.post('/api/v1/projects', project);
};

export const deleteProject = async (projectId: string): Promise<void> => {
  await apiClient.delete(`/api/v1/projects/${projectId}`);
};

export const updateProject = async (projectId: string, updates: Partial<Project>): Promise<void> => {
  await apiClient.patch(`/api/v1/projects/${projectId}`, updates);
};

export const getProjectRuns = async (projectId: string): Promise<Run[]> => {
  const response = await apiClient.get(`/api/v1/projects/${projectId}/runs`);
  return Array.isArray(response.data) ? response.data : [];
};

export const createScope = async (
  projectId: string,
  scopeData: Record<string, unknown>
): Promise<Scope> => {
  const response = await apiClient.post(`/api/v1/projects/${projectId}/scopes`, scopeData);
  return response.data;
};

const lockScope = async (projectId: string, scopeId: string) => {
  await apiClient.post(`/api/v1/projects/${projectId}/scopes/${scopeId}/lock`, {
    locked_by: 'demo-user',
    signature: 'demo-signature-' + Date.now()
  });
};

const createRunForScope = async (projectId: string, scopeId: string) => {
  const response = await apiClient.post(`/api/v1/projects/${projectId}/runs`, {
    scope_id: scopeId
  });
  return response.data as Run;
};

const startRun = async (runId: string) => {
  await apiClient.post(`/api/v1/runs/${runId}/start`, {});
};

export const createAndStartRun = async (projectId: string, scopeId: string): Promise<Run> => {
  await lockScope(projectId, scopeId);
  const run = await createRunForScope(projectId, scopeId);
  await startRun(run.id);
  return run;
};

export const getRun = async (runId: string): Promise<Run> => {
  const response = await apiClient.get(`/api/v1/runs/${runId}`);
  return response.data;
};

export const getRunStats = async (runId: string): Promise<RunStats> => {
  const response = await apiClient.get(`/api/v1/runs/${runId}/stats`);
  return response.data;
};

export const getRunTimeline = async (runId: string): Promise<TimelineEvent[]> => {
  const response = await apiClient.get(`/api/v1/runs/${runId}/timeline`);
  return Array.isArray(response.data) ? response.data : [];
};

export const getRunEvidence = async (runId: string): Promise<Evidence[]> => {
  const response = await apiClient.get(`/api/v1/runs/${runId}/evidence`);
  return Array.isArray(response.data) ? response.data : [];
};

export const getPendingApprovals = async (runId: string): Promise<PendingApproval[]> => {
  const response = await apiClient.get(`/api/v1/runs/${runId}/approvals/pending`);
  return Array.isArray(response.data) ? response.data : [];
};

export const approveAction = async (runId: string, actionId: string): Promise<void> => {
  await apiClient.post(`/api/v1/runs/${runId}/approvals/${actionId}/approve`, {
    approved_by: 'security-lead',
    signature: `approved-${actionId.substring(0, 8)}`
  });
};

export const generateReport = async (runId: string) => {
  const response = await apiClient.post('/api/v1/reports', { run_id: runId });
  return response.data;
};

export const getJob = async (jobId: string) => {
  const response = await apiClient.get(`/api/v1/jobs/${jobId}`);
  return response.data;
};

export const downloadReport = async (reportId: string) => {
  const response = await apiClient.get(`/api/v1/reports/${reportId}`, {
    responseType: 'blob'
  });
  return response.data;
};

export const generateAuditBundle = async (runId: string) => {
  const response = await apiClient.post(
    '/api/v1/audit/bundle',
    { run_id: runId },
    { responseType: 'blob' }
  );
  return response.data;
};

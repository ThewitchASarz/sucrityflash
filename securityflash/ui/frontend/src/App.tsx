import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const API_BASE = 'http://localhost:3001';
const FINDINGS_PAGE_SIZE = 10;

interface HealthStatus {
  status: string;
  app: string;
  version: string;
  environment: string;
}

interface Project {
  id: string;
  name: string;
  customer_id: string;
  description?: string;
  status: string;
  created_at: string;
}

interface Scope {
  id: string;
  project_id: string;
  scope_json: {
    scope_type?: string;
    targets?: Array<{ type: string; value: string; criticality: string }>;
    excluded_targets?: Array<{ type: string; value: string; criticality: string }>;
    attack_vectors_allowed?: string[];
    attack_vectors_prohibited?: string[];
    approved_tools?: string[];
  };
  locked_at?: string;
  status: string;
  created_at: string;
}

interface Run {
  id: string;
  plan_id: string;
  status: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
}

interface RunStats {
  action_specs_count: number;
  pending_approvals_count: number;
  approved_count: number;
  executed_count: number;
  evidence_count: number;
  last_activity_at?: string;
}

interface TimelineEvent {
  timestamp: string;
  agent_type: string;
  action: string;
  details: string;
}

interface Finding {
  id: string;
  run_id: string;
  title: string;
  description: string;
  severity: string;
  cvss_score?: number;
  exploitability?: string;
  validated: boolean;
  created_at: string;
}

type View = 'projects' | 'project-detail' | 'run-detail' | 'findings';

function App() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [token, setToken] = useState<string | null>('demo-token');
  const [currentView, setCurrentView] = useState<View>('projects');

  // Projects
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [showNewProjectForm, setShowNewProjectForm] = useState(false);
  const [newProject, setNewProject] = useState({
    name: '',
    customer_id: '',
    description: ''
  });

  // Scopes
  const [scopes, setScopes] = useState<Scope[]>([]);
  const [showNewScopeForm, setShowNewScopeForm] = useState(false);
  const [newScope, setNewScope] = useState({
    target_systems: '',
    excluded_systems: '',
    forbidden_methods: ''
  });

  // Runs
  const [runs, setRuns] = useState<Run[]>([]);
  const [selectedRun, setSelectedRun] = useState<Run | null>(null);

  // Findings
  const [findings, setFindings] = useState<Finding[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [toolFilter, setToolFilter] = useState<string>('all');
  const [validationFilter, setValidationFilter] = useState<string>('all');
  const [sortField, setSortField] = useState<'created_at' | 'generated_at' | 'severity'>('created_at');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

  // Run activity
  const [runStats, setRunStats] = useState<RunStats | null>(null);
  const [timeline, setTimeline] = useState<any[]>([]);
  const [pendingApprovals, setPendingApprovals] = useState<any[]>([]);

  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [reportStatus, setReportStatus] = useState<'idle' | 'queued' | 'running' | 'completed' | 'error' | 'timeout'>('idle');
  const [auditStatus, setAuditStatus] = useState<'idle' | 'running' | 'completed' | 'error'>('idle');

  useEffect(() => {
    checkHealth();
    loadProjects();
  }, []);

  const checkHealth = async () => {
    try {
      const response = await axios.get(`${API_BASE}/health`);
      setHealth(response.data);
    } catch (err) {
      setError('Backend is not responding');
    }
  };

  const loadProjects = async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/v1/projects`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setProjects(Array.isArray(response.data) ? response.data : []);
    } catch (err: any) {
      console.error('Error loading projects:', err);
      setProjects([]);
    }
  };

  const createProject = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      await axios.post(
        `${API_BASE}/api/v1/projects`,
        newProject,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      await loadProjects();
      setShowNewProjectForm(false);
      setNewProject({ name: '', customer_id: '', description: '' });
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create project');
    } finally {
      setLoading(false);
    }
  };

  const loadProjectDetails = async (project: Project) => {
    setSelectedProject(project);
    setCurrentView('project-detail');

    // Note: V1 API doesn't have a list scopes endpoint, so we don't load scopes here
    // Scopes will be created and then shown individually
    setScopes([]);

    try {
      // Load runs for this project (nested under project ID)
      const runsResponse = await axios.get(`${API_BASE}/api/v1/projects/${project.id}/runs`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setRuns(Array.isArray(runsResponse.data) ? runsResponse.data : []);
    } catch (err) {
      console.error('Error loading project details:', err);
      setRuns([]);
    }
  };

  const createScope = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProject) return;

    setLoading(true);
    setError('');

    try {
      // Transform simple URL list to V1 API format with Target objects
      const targets = newScope.target_systems
        .split('\n')
        .map(s => s.trim())
        .filter(Boolean)
        .map(url => ({
          type: url.includes('/') ? 'domain' : 'ip',
          value: url,
          criticality: 'HIGH'
        }));

      const excludedTargets = newScope.excluded_systems
        .split('\n')
        .map(s => s.trim())
        .filter(Boolean)
        .map(url => ({
          type: url.includes('/') ? 'domain' : 'ip',
          value: url,
          criticality: 'LOW'
        }));

      const scopeData = {
        scope_type: 'web_app',
        targets: targets,
        excluded_targets: excludedTargets,
        attack_vectors_allowed: ['reconnaissance', 'vulnerability_scanning', 'exploitation'],
        attack_vectors_prohibited: newScope.forbidden_methods.split(',').map(s => s.trim()).filter(Boolean),
        approved_tools: ['nmap', 'burpsuite', 'sqlmap', 'metasploit'],
        time_restrictions: null
      };

      const response = await axios.post(
        `${API_BASE}/api/v1/projects/${selectedProject.id}/scopes`,
        scopeData,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      // Add the created scope to state (V1 API doesn't have list endpoint)
      setScopes([...scopes, response.data]);
      setShowNewScopeForm(false);
      setNewScope({ target_systems: '', excluded_systems: '', forbidden_methods: '' });
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create scope');
    } finally {
      setLoading(false);
    }
  };

  const deleteProject = async (projectId: string) => {
    if (!window.confirm('Are you sure you want to delete this project?')) return;

    setLoading(true);
    try {
      await axios.delete(`${API_BASE}/api/v1/projects/${projectId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      await loadProjects();
      if (selectedProject?.id === projectId) {
        setSelectedProject(null);
        setCurrentView('projects');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete project');
    } finally {
      setLoading(false);
    }
  };

  const updateProject = async (projectId: string, updates: Partial<Project>) => {
    setLoading(true);
    try {
      await axios.patch(`${API_BASE}/api/v1/projects/${projectId}`, updates, {
        headers: { Authorization: `Bearer ${token}` }
      });
      await loadProjects();
      if (selectedProject?.id === projectId) {
        const updatedProject = { ...selectedProject, ...updates };
        setSelectedProject(updatedProject as Project);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update project');
    } finally {
      setLoading(false);
    }
  };

  const createRun = async (scopeId: string) => {
    if (!selectedProject) return;

    setLoading(true);
    setError('');

    try {
      // Step 1: Lock the scope (required before creating run)
      await axios.post(
        `${API_BASE}/api/v1/projects/${selectedProject.id}/scopes/${scopeId}/lock`,
        {
          locked_by: 'demo-user',
          signature: 'demo-signature-' + Date.now()
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      // Step 2: Create the run (V1 API creates run with scope_id directly)
      const runResponse = await axios.post(
        `${API_BASE}/api/v1/projects/${selectedProject.id}/runs`,
        { scope_id: scopeId },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      // Step 3: Start the run (V1 API requires explicit start call)
      await axios.post(
        `${API_BASE}/api/v1/runs/${runResponse.data.id}/start`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );

      setSelectedRun(runResponse.data);
      setCurrentView('run-detail');

      // Start polling for updates
      pollRunStatus(runResponse.data.id);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to start pentest run');
    } finally {
      setLoading(false);
    }
  };

  const pollRunStatus = async (runId: string) => {
    try {
      // Load run details
      const response = await axios.get(`${API_BASE}/api/v1/runs/${runId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSelectedRun(response.data);

      // Load run stats (shows proof of work)
      try {
        const statsResponse = await axios.get(`${API_BASE}/api/v1/runs/${runId}/stats`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setRunStats(statsResponse.data);
      } catch (err) {
        console.error('Error loading run stats:', err);
      }

      // Load timeline (shows real agent activity)
      try {
        const timelineResponse = await axios.get(`${API_BASE}/api/v1/runs/${runId}/timeline`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setTimeline(Array.isArray(timelineResponse.data) ? timelineResponse.data : []);
      } catch (err) {
        console.error('Error loading timeline:', err);
      }

      // Load evidence (findings) for this run
      const findingsResponse = await axios.get(`${API_BASE}/api/v1/runs/${runId}/evidence`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setFindings(Array.isArray(findingsResponse.data) ? findingsResponse.data : []);
      setCurrentPage(1);

      // Load pending approvals (CRITICAL FOR MONITORING)
      try {
        const approvalsResponse = await axios.get(`${API_BASE}/api/v1/runs/${runId}/approvals/pending`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setPendingApprovals(Array.isArray(approvalsResponse.data) ? approvalsResponse.data : []);
      } catch (err) {
        console.error('Error loading pending approvals:', err);
      }

      // Continue polling every 5 seconds if still running
      if (response.data.status === 'RUNNING' || response.data.status === 'PENDING') {
        setTimeout(() => pollRunStatus(runId), 5000);
      }
    } catch (err) {
      console.error('Error polling run status:', err);
    }
  };

  const generateReport = async (runId: string) => {
    setLoading(true);
    setError('');
    setReportStatus('queued');

    try {
      // V1 API returns a job_id for async report generation
      const response = await axios.post(
        `${API_BASE}/api/v1/reports`,
        { run_id: runId },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      if (response.data.job_id) {
        // Poll for report completion
        setReportStatus('running');
        const reportId = await pollReportJob(response.data.job_id);
        if (reportId) {
          // Download the completed report
          await downloadReport(reportId, runId);
        }
      } else if (response.data.report_id) {
        // Report generated immediately
        await downloadReport(response.data.report_id, runId);
        setReportStatus('completed');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to generate report');
      setReportStatus('error');
    } finally {
      setLoading(false);
    }
  };

  const pollReportJob = async (jobId: string): Promise<string | null> => {
    for (let i = 0; i < 30; i++) {  // Poll for up to 5 minutes
      try {
        const response = await axios.get(`${API_BASE}/api/v1/jobs/${jobId}`, {
          headers: { Authorization: `Bearer ${token}` }
        });

        if (response.data.status === 'COMPLETED') {
          setReportStatus('completed');
          return response.data.result.report_id;
        } else if (response.data.status === 'FAILED') {
          setError('Report generation failed');
          setReportStatus('error');
          return null;
        }

        // Wait 10 seconds before next poll
        await new Promise(resolve => setTimeout(resolve, 10000));
      } catch (err) {
        console.error('Error polling report job:', err);
        setReportStatus('error');
        return null;
      }
    }
    setError('Report generation timed out');
    setReportStatus('timeout');
    return null;
  };

  const downloadReport = async (reportId: string, runId: string) => {
    try {
      const response = await axios.get(
        `${API_BASE}/api/v1/reports/${reportId}`,
        {
          headers: { Authorization: `Bearer ${token}` },
          responseType: 'blob'
        }
      );

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `pentest-report-${runId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      setError('Failed to download report');
      setReportStatus('error');
    }
  };

  const generateAuditBundle = async (runId: string) => {
    setLoading(true);
    setError('');
    setAuditStatus('running');

    try {
      const response = await axios.post(
        `${API_BASE}/api/v1/audit/bundle`,
        { run_id: runId },
        {
          headers: { Authorization: `Bearer ${token}` },
          responseType: 'blob'
        }
      );

      // Download the audit bundle
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `audit-bundle-${runId}.zip`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      setAuditStatus('completed');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to generate audit bundle');
      setAuditStatus('error');
    } finally {
      setLoading(false);
    }
  };

  const downloadArtifact = async (artifactUri: string, evidenceId: string) => {
    try {
      const response = await axios.get(
        artifactUri,
        {
          headers: { Authorization: `Bearer ${token}` },
          responseType: 'blob'
        }
      );

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `artifact-${evidenceId}.bin`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      setError('Failed to download artifact');
    }
  };

  const openArtifact = (artifactUri: string) => {
    window.open(artifactUri, '_blank', 'noopener,noreferrer');
  };

  const getSeverity = (evidence: any) =>
    (evidence.severity || evidence.evidence_metadata?.severity || 'info').toLowerCase();

  const getToolUsed = (evidence: any) =>
    evidence.evidence_metadata?.tool_used || evidence.tool || evidence.generated_by || 'unknown';

  useEffect(() => {
    setCurrentPage(1);
  }, [severityFilter, toolFilter, validationFilter, sortField, sortDirection]);

  useEffect(() => {
    setReportStatus('idle');
    setAuditStatus('idle');
  }, [selectedRun?.id]);

  const renderProjects = () => (
    <div className="main-content">
      <div className="user-actions">
        <button onClick={() => setShowNewProjectForm(!showNewProjectForm)}>
          {showNewProjectForm ? 'Cancel' : '+ New Project'}
        </button>
      </div>

      {showNewProjectForm && (
        <div className="new-project-form">
          <h2>Create New Pentest Project</h2>
          <form onSubmit={createProject}>
            <div className="form-group">
              <label>Project Name *</label>
              <input
                type="text"
                placeholder="e.g., Dealwyzer.com Security Assessment"
                value={newProject.name}
                onChange={(e) => setNewProject({...newProject, name: e.target.value})}
                required
              />
            </div>
            <div className="form-group">
              <label>Customer ID *</label>
              <input
                type="text"
                placeholder="e.g., cust_123abc"
                value={newProject.customer_id}
                onChange={(e) => setNewProject({...newProject, customer_id: e.target.value})}
                required
              />
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea
                placeholder="Brief description of the engagement..."
                value={newProject.description}
                onChange={(e) => setNewProject({...newProject, description: e.target.value})}
                rows={3}
              />
            </div>
            <div className="form-actions">
              <button type="submit" disabled={loading}>
                {loading ? 'Creating...' : 'Create Project'}
              </button>
              <button type="button" onClick={() => setShowNewProjectForm(false)}>
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="projects-section">
        <h2>Projects ({projects.length})</h2>
        {projects.length === 0 ? (
          <p className="empty-state">No projects yet. Create one to get started!</p>
        ) : (
          <div className="projects-grid">
            {projects.map(project => (
              <div key={project.id} className="project-card">
                <div className="card-actions">
                  <button
                    className="icon-button delete-button"
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteProject(project.id);
                    }}
                    title="Delete project"
                  >
                    🗑️
                  </button>
                </div>
                <div onClick={() => loadProjectDetails(project)} style={{ cursor: 'pointer' }}>
                  <h3>{project.name}</h3>
                  <p><strong>Customer ID:</strong> {project.customer_id}</p>
                  <p><strong>Status:</strong> <span className={`status-${project.status.toLowerCase()}`}>{project.status}</span></p>
                  {project.description && <p className="description">{project.description}</p>}
                  <p className="date">Created: {new Date(project.created_at).toLocaleDateString()}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="api-info">
        <h3>API Access & Documentation</h3>
        <p>📚 <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer">V1 API Docs (SecurityFlash)</a></p>
        <p>🔵 <a href="http://localhost:3001/docs" target="_blank" rel="noopener noreferrer">V2 BFF Docs (Proxy Layer)</a></p>
        <p>🔍 <a href="http://localhost:8000/redoc" target="_blank" rel="noopener noreferrer">ReDoc Documentation</a></p>
        <p>💚 <a href="http://localhost:3001/health" target="_blank" rel="noopener noreferrer">V2 BFF Health Check</a></p>
      </div>
    </div>
  );

  const renderProjectDetail = () => {
    if (!selectedProject) return null;

    return (
      <div className="main-content">
        <button className="back-button" onClick={() => setCurrentView('projects')}>← Back to Projects</button>

        <div className="project-header">
          <div>
            <h2>{selectedProject.name}</h2>
            <p><strong>Customer ID:</strong> {selectedProject.customer_id}</p>
            {selectedProject.description && <p>{selectedProject.description}</p>}
          </div>
          <div className="header-actions">
            <button
              className="icon-button"
              onClick={() => {
                const newName = prompt('New project name:', selectedProject.name);
                if (newName) updateProject(selectedProject.id, { name: newName });
              }}
              title="Edit project name"
            >
              ✏️ Edit
            </button>
            <button
              className="icon-button delete-button"
              onClick={() => deleteProject(selectedProject.id)}
              title="Delete project"
            >
              🗑️ Delete
            </button>
          </div>
        </div>

        <div className="section">
          <div className="section-header">
            <h3>Scopes & Targets</h3>
            <button onClick={() => setShowNewScopeForm(!showNewScopeForm)}>
              {showNewScopeForm ? 'Cancel' : '+ Define Scope'}
            </button>
          </div>

          {showNewScopeForm && (
            <div className="scope-form">
              <form onSubmit={createScope}>
                <div className="form-group">
                  <label>Target Systems (one per line) *</label>
                  <textarea
                    placeholder="https://example.com&#10;192.168.1.0/24&#10;api.example.com"
                    value={newScope.target_systems}
                    onChange={(e) => setNewScope({...newScope, target_systems: e.target.value})}
                    rows={4}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Excluded Systems (one per line)</label>
                  <textarea
                    placeholder="192.168.1.1&#10;admin.example.com"
                    value={newScope.excluded_systems}
                    onChange={(e) => setNewScope({...newScope, excluded_systems: e.target.value})}
                    rows={2}
                  />
                </div>
                <div className="form-group">
                  <label>Forbidden Methods (comma-separated)</label>
                  <input
                    type="text"
                    placeholder="social_engineering, dos, data_destruction"
                    value={newScope.forbidden_methods}
                    onChange={(e) => setNewScope({...newScope, forbidden_methods: e.target.value})}
                  />
                </div>
                <button type="submit" disabled={loading}>
                  {loading ? 'Creating...' : 'Create Scope'}
                </button>
              </form>
            </div>
          )}

          {scopes.length === 0 ? (
            <p className="empty-state">No scopes defined. Define a scope to start testing.</p>
          ) : (
            <div className="scopes-list">
              {scopes.map(scope => (
                <div key={scope.id} className="scope-card">
                  <h4>Scope {scope.id.substring(0, 8)} - {scope.scope_json?.scope_type || 'web_app'}</h4>
                  <div className="scope-details">
                    {scope.scope_json?.targets && scope.scope_json.targets.length > 0 && (
                      <div>
                        <strong>Targets:</strong>
                        <ul>
                          {scope.scope_json.targets.map((target, i) => (
                            <li key={i}>{target.value} ({target.criticality})</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {scope.scope_json?.excluded_targets && scope.scope_json.excluded_targets.length > 0 && (
                      <div>
                        <strong>Excluded:</strong>
                        <ul>
                          {scope.scope_json.excluded_targets.map((exc, i) => (
                            <li key={i}>{exc.value}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    <p><strong>Status:</strong> <span className={`status-${scope.status.toLowerCase()}`}>{scope.status}</span></p>
                  </div>
                  <button
                    onClick={() => createRun(scope.id)}
                    disabled={loading}
                    className="start-button"
                  >
                    🚀 Start Pentest
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="section">
          <h3>Test Runs</h3>
          {runs.length === 0 ? (
            <p className="empty-state">No test runs yet.</p>
          ) : (
            <div className="runs-list">
              {runs.map(run => (
                <div
                  key={run.id}
                  className="run-card clickable"
                  onClick={() => {
                    setSelectedRun(run);
                    pollRunStatus(run.id);
                  }}
                >
                  <h4>Run {run.id.substring(0, 8)}</h4>
                  <p><strong>Status:</strong> <span className={`status-${run.status.toLowerCase()}`}>{run.status}</span></p>
                  <p className="date">Started: {run.started_at ? new Date(run.started_at).toLocaleString() : 'Not started'}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderRunDetail = () => {
    if (!selectedRun) return null;

    const severityOrder: Record<string, number> = {
      critical: 4,
      high: 3,
      medium: 2,
      low: 1,
      info: 0
    };

    const filteredFindings = findings.filter((item) => {
      const severity = getSeverity(item);
      const toolUsed = getToolUsed(item).toLowerCase();
      const validationStatus = (item.validation_status || (item.validated ? 'validated' : 'unvalidated')).toLowerCase();

      const matchesSeverity = severityFilter === 'all' || severity === severityFilter;
      const matchesTool = toolFilter === 'all' || toolUsed === toolFilter;
      const matchesValidation = validationFilter === 'all' || validationStatus === validationFilter;

      return matchesSeverity && matchesTool && matchesValidation;
    });

    const sortedFindings = [...filteredFindings].sort((a, b) => {
      if (sortField === 'severity') {
        const severityA = severityOrder[getSeverity(a)] ?? 0;
        const severityB = severityOrder[getSeverity(b)] ?? 0;
        return sortDirection === 'asc'
          ? severityA - severityB
          : severityB - severityA;
      }
      const first = new Date(a[sortField]).getTime();
      const second = new Date(b[sortField]).getTime();
      return sortDirection === 'asc' ? first - second : second - first;
    });

    const totalPages = Math.max(1, Math.ceil(sortedFindings.length / FINDINGS_PAGE_SIZE));
    const safePage = Math.min(currentPage, totalPages);
    const startIndex = (safePage - 1) * FINDINGS_PAGE_SIZE;
    const paginatedFindings = sortedFindings.slice(startIndex, startIndex + FINDINGS_PAGE_SIZE);

    const availableTools = Array.from(
      new Set(
        findings
          .map((item) => getToolUsed(item)?.toLowerCase())
          .filter(Boolean)
      )
    );

    return (
      <div className="main-content">
        <button className="back-button" onClick={() => setCurrentView('project-detail')}>← Back to Project</button>

        <div className="run-header">
          <h2>Pentest Run {selectedRun.id.substring(0, 8)}</h2>
          <div className={`status-badge status-${selectedRun.status.toLowerCase()}`}>
            {selectedRun.status}
          </div>
        </div>

        {/* Real-time Stats from V1 */}
        {runStats && (
          <div className="section">
            <h3>📊 Live Stats (Proof of Work)</h3>
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-value">{runStats.action_specs_count}</div>
                <div className="stat-label">Actions Proposed</div>
              </div>
              <div className="stat-card" style={{backgroundColor: runStats.pending_approvals_count > 0 ? '#fff3cd' : undefined}}>
                <div className="stat-value">{runStats.pending_approvals_count}</div>
                <div className="stat-label">⏳ Pending Approvals</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{runStats.executed_count}</div>
                <div className="stat-label">✅ Executed</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{runStats.evidence_count}</div>
                <div className="stat-label">📊 Evidence Collected</div>
              </div>
            </div>
            {runStats.last_activity_at && (
              <p className="last-activity">⏰ Last activity: {new Date(runStats.last_activity_at).toLocaleString()}</p>
            )}
          </div>
        )}

        {/* PENDING APPROVALS - CRITICAL FOR HUMAN MONITORING */}
        {pendingApprovals.length > 0 && (
          <div className="section" style={{backgroundColor: '#fff3cd', border: '2px solid #ffc107', padding: '20px'}}>
            <h3>⏳ PENDING APPROVALS - ACTION REQUIRED</h3>
            <p style={{marginBottom: '15px', fontWeight: 'bold'}}>The following actions need your approval before agents can proceed:</p>
            {pendingApprovals.map((approval) => (
              <div key={approval.action_id} className="approval-card" style={{
                backgroundColor: 'white',
                padding: '15px',
                marginBottom: '15px',
                borderRadius: '8px',
                border: '1px solid #ffc107'
              }}>
                <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start'}}>
                  <div style={{flex: 1}}>
                    <h4 style={{margin: '0 0 10px 0'}}>
                      🔧 {approval.tool.toUpperCase()} → {approval.target}
                    </h4>
                    <p style={{margin: '5px 0'}}><strong>Arguments:</strong> {approval.arguments.join(' ')}</p>
                    <p style={{margin: '5px 0'}}><strong>Justification:</strong> {approval.justification}</p>
                    <p style={{margin: '5px 0'}}><strong>Proposed by:</strong> {approval.proposed_by}</p>
                    <p style={{margin: '5px 0'}}>
                      <span style={{color: '#dc3545', fontWeight: 'bold'}}>Risk Score: {approval.risk_score}</span>
                      {' | '}
                      <span>Approval Tier: {approval.approval_tier}</span>
                    </p>
                    <p style={{fontSize: '12px', color: '#666', marginTop: '10px'}}>
                      Action ID: {approval.action_id}
                    </p>
                  </div>
                  <div style={{marginLeft: '20px'}}>
                    <button
                      onClick={async () => {
                        try {
                          await axios.post(
                            `${API_BASE}/api/v1/runs/${selectedRun.id}/approvals/${approval.action_id}/approve`,
                            {
                              approved_by: 'security-lead',
                              signature: `approved-${approval.action_id.substring(0, 8)}`
                            },
                            { headers: { Authorization: `Bearer ${token}` } }
                          );
                          // Refresh approvals
                          pollRunStatus(selectedRun.id);
                        } catch (err: any) {
                          setError(err.response?.data?.detail || 'Failed to approve action');
                        }
                      }}
                      style={{
                        padding: '10px 20px',
                        backgroundColor: '#28a745',
                        color: 'white',
                        border: 'none',
                        borderRadius: '5px',
                        cursor: 'pointer',
                        fontWeight: 'bold'
                      }}
                    >
                      ✅ APPROVE
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="section">
          <h3>🤖 AI Agent Activity Timeline</h3>
          <div className="agent-activity">
            {timeline.length === 0 ? (
              <>
                {selectedRun.status === 'PENDING' && (
                  <div className="activity-item">
                    <span className="agent-icon">⏳</span>
                    <div>
                      <strong>Pentest Queued</strong>
                      <p>Waiting for worker to pick up the job...</p>
                    </div>
                  </div>
                )}
                {selectedRun.status === 'EXECUTING' && (
                  <div className="activity-item">
                    <span className="agent-icon">🔄</span>
                    <div>
                      <strong>Agents Executing</strong>
                      <p>Waiting for activity from V1 API...</p>
                    </div>
                  </div>
                )}
                {selectedRun.status === 'COMPLETED' && (
                  <div className="activity-item">
                    <span className="agent-icon">✅</span>
                    <div>
                      <strong>Pentest Completed</strong>
                      <p>All agents have finished execution. Review findings below.</p>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <>
                {timeline.map((event, index) => (
                  <div key={index} className="activity-item">
                    <span className="agent-icon">
                      {event.event_type === 'ACTION_PROPOSED' && '📝'}
                      {event.event_type === 'ACTION_APPROVED' && '✅'}
                      {event.event_type === 'ACTION_EXECUTED' && '⚡'}
                      {event.event_type === 'EVIDENCE_STORED' && '📊'}
                      {event.event_type === 'RUN_STARTED' && '🚀'}
                      {event.event_type === 'RUN_CREATED' && '📋'}
                      {!['ACTION_PROPOSED', 'ACTION_APPROVED', 'ACTION_EXECUTED', 'EVIDENCE_STORED', 'RUN_STARTED', 'RUN_CREATED'].includes(event.event_type) && '🤖'}
                    </span>
                    <div>
                      <strong>{event.event_type.replace(/_/g, ' ')}</strong>
                      <p><em>By:</em> {event.actor}</p>
                      {event.details && event.details.tool && (
                        <p><strong>Tool:</strong> {event.details.tool} → {event.details.target}</p>
                      )}
                      <small className="timestamp">{new Date(event.timestamp).toLocaleString()}</small>
                    </div>
                  </div>
                ))}
              </>
            )}
          </div>
        </div>

        <div className="section">
          <div className="section-header">
            <div>
              <h3>📊 Evidence Collected ({filteredFindings.length}/{findings.length})</h3>
              <p className="section-subtitle">Paginate, filter, and sort by severity, tool, and timestamps.</p>
            </div>
            <div className="report-actions">
              <button
                onClick={() => generateReport(selectedRun.id)}
                disabled={loading || selectedRun.status !== 'COMPLETED' || reportStatus === 'running'}
                title={selectedRun.status !== 'COMPLETED' ? 'Available after run completion' : 'Generate pentest report'}
              >
                {reportStatus === 'running' ? '⏳ Generating...' : '📄 Generate Report'}
              </button>
              <button
                onClick={() => generateAuditBundle(selectedRun.id)}
                disabled={loading || selectedRun.status !== 'COMPLETED' || auditStatus === 'running'}
                title={selectedRun.status !== 'COMPLETED' ? 'Available after run completion' : 'Download audit bundle'}
              >
                {auditStatus === 'running' ? '⏳ Preparing...' : '📦 Download Audit Bundle'}
              </button>
              <div className="job-chips">
                <span className={`chip job-chip status-${reportStatus}`}>Report: {reportStatus}</span>
                <span className={`chip job-chip status-${auditStatus}`}>Audit bundle: {auditStatus}</span>
              </div>
            </div>
          </div>

          {findings.length > 0 && (
            <div className="filters-row">
              <div className="filter-group">
                <span className="chip-label">Severity</span>
                {['all', 'critical', 'high', 'medium', 'low', 'info'].map((sev) => (
                  <button
                    key={sev}
                    className={`chip ${severityFilter === sev ? 'chip-active' : ''}`}
                    onClick={() => setSeverityFilter(sev)}
                  >
                    {sev === 'all' ? 'All' : sev.toUpperCase()}
                  </button>
                ))}
              </div>
              <div className="filter-group">
                <span className="chip-label">Validation</span>
                {['all', 'validated', 'unvalidated', 'rejected'].map((status) => (
                  <button
                    key={status}
                    className={`chip ${validationFilter === status ? 'chip-active' : ''}`}
                    onClick={() => setValidationFilter(status)}
                  >
                    {status === 'all' ? 'All' : status.toUpperCase()}
                  </button>
                ))}
              </div>
              <div className="filter-group">
                <span className="chip-label">Tool</span>
                <button
                  className={`chip ${toolFilter === 'all' ? 'chip-active' : ''}`}
                  onClick={() => setToolFilter('all')}
                >
                  All tools
                </button>
                {availableTools.map((tool) => (
                  <button
                    key={tool}
                    className={`chip ${toolFilter === tool ? 'chip-active' : ''}`}
                    onClick={() => setToolFilter(tool)}
                  >
                    {tool}
                  </button>
                ))}
              </div>
              <div className="filter-group">
                <span className="chip-label">Sort</span>
                {(['created_at', 'generated_at', 'severity'] as const).map((field) => (
                  <button
                    key={field}
                    className={`chip ${sortField === field ? 'chip-active' : ''}`}
                    onClick={() => setSortField(field)}
                  >
                    {field === 'severity' ? 'Severity' : field === 'created_at' ? 'Created' : 'Generated'}
                  </button>
                ))}
                <button
                  className="chip"
                  onClick={() => setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')}
                >
                  {sortDirection === 'asc' ? '⬆️ Asc' : '⬇️ Desc'}
                </button>
              </div>
            </div>
          )}

          {findings.length === 0 ? (
            <p className="empty-state">
              {selectedRun.status === 'RUNNING' ? 'Waiting for evidence from worker...' : 'No evidence collected yet.'}
            </p>
          ) : (
            <div className="findings-list">
              {paginatedFindings.map((evidence: any) => {
                const severity = getSeverity(evidence);
                const toolUsed = getToolUsed(evidence);
                const validationStatus = evidence.validation_status || (evidence.validated ? 'validated' : 'unvalidated');

                return (
                  <div key={evidence.id} className={`finding-card severity-${severity}`}>
                    <div className="finding-header">
                      <div>
                        <h4>{evidence.evidence_type.replace(/_/g, ' ').toUpperCase()}</h4>
                        <div className="chip-stack">
                          <span className={`chip severity-chip severity-${severity}`}>{severity.toUpperCase()}</span>
                          <span className={`chip validation-chip status-${validationStatus.toLowerCase()}`}>
                            {validationStatus.toUpperCase()}
                          </span>
                        </div>
                      </div>
                      <div className="chip tool-chip">🛠️ {toolUsed}</div>
                    </div>
                    <p><strong>Generated by:</strong> {evidence.generated_by}</p>
                    {evidence.evidence_metadata && evidence.evidence_metadata.returncode !== undefined && (
                      <p><strong>Return code:</strong> {evidence.evidence_metadata.returncode}</p>
                    )}
                    <div className="artifact-row">
                      <div>
                        <p><strong>Artifact:</strong> {evidence.artifact_uri}</p>
                        <p className="hash-text">
                          <strong>Hash:</strong> {evidence.artifact_hash.substring(0, 16)}...
                        </p>
                      </div>
                      <div className="artifact-actions">
                        <button className="icon-button" onClick={() => openArtifact(evidence.artifact_uri)}>👁️ View</button>
                        <button className="icon-button" onClick={() => downloadArtifact(evidence.artifact_uri, evidence.id)}>⬇️ Download</button>
                      </div>
                    </div>
                    <div className="finding-meta">
                      <span>Created: {new Date(evidence.created_at).toLocaleString()}</span>
                      <span>Generated: {new Date(evidence.generated_at).toLocaleString()}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {findings.length > 0 && (
            <div className="pagination">
              <button
                onClick={() => setCurrentPage(Math.max(1, safePage - 1))}
                disabled={safePage === 1}
              >
                ← Previous
              </button>
              <span className="pagination-status">Page {safePage} of {totalPages}</span>
              <button
                onClick={() => setCurrentPage(Math.min(totalPages, safePage + 1))}
                disabled={safePage === totalPages}
              >
                Next →
              </button>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>🔒 Pentest AI Platform</h1>

        {health && (
          <div className="health-status">
            <span className="status-indicator">●</span> {health.app} v{health.version}
            <span className="env-badge">{health.environment}</span>
          </div>
        )}

        {error && <div className="error">{error}</div>}

        {currentView === 'projects' && renderProjects()}
        {currentView === 'project-detail' && renderProjectDetail()}
        {currentView === 'run-detail' && renderRunDetail()}
      </header>
    </div>
  );
}

export default App;

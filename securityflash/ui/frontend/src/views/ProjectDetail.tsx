import React, { useEffect, useState } from 'react';
import {
  createAndStartRun,
  createScope as createScopeRequest,
  deleteProject,
  getProjectRuns,
  getProjects,
  updateProject
} from '../api';
import { useToast } from '../components/ToastProvider';
import { Project, Run, Scope } from '../types';

interface ProjectDetailProps {
  projectId: string;
  onBack: () => void;
  onNavigateRun: (runId: string) => void;
}

export const ProjectDetail: React.FC<ProjectDetailProps> = ({ projectId, onBack, onNavigateRun }) => {
  const [project, setProject] = useState<Project | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [scopes, setScopes] = useState<Scope[]>([]);
  const [showNewScopeForm, setShowNewScopeForm] = useState(false);
  const [newScope, setNewScope] = useState({
    target_systems: '',
    excluded_systems: '',
    forbidden_methods: ''
  });
  const [loading, setLoading] = useState(false);
  const { addToast, dismissToast } = useToast();

  useEffect(() => {
    loadProjectAndRuns();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  const loadProjectAndRuns = async () => {
    setLoading(true);
    try {
      const allProjects = await getProjects();
      const match = allProjects.find((p) => p.id === projectId) || null;
      setProject(match);
      setScopes([]);
      if (match) {
        const runData = await getProjectRuns(projectId);
        setRuns(runData);
      } else {
        addToast('Project not found', 'error');
      }
    } catch (err) {
      addToast('Failed to load project details', 'error');
    } finally {
      setLoading(false);
    }
  };

  const createScope = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!project) return;

    setLoading(true);
    const loadingToast = addToast('Creating scope...', 'loading', 8000);

    try {
      const targets = newScope.target_systems
        .split('\n')
        .map((s) => s.trim())
        .filter(Boolean)
        .map((url) => ({
          type: url.includes('/') ? 'domain' : 'ip',
          value: url,
          criticality: 'HIGH'
        }));

      const excludedTargets = newScope.excluded_systems
        .split('\n')
        .map((s) => s.trim())
        .filter(Boolean)
        .map((url) => ({
          type: url.includes('/') ? 'domain' : 'ip',
          value: url,
          criticality: 'LOW'
        }));

      const scopeData = {
        scope_type: 'web_app',
        targets,
        excluded_targets: excludedTargets,
        attack_vectors_allowed: ['reconnaissance', 'vulnerability_scanning', 'exploitation'],
        attack_vectors_prohibited: newScope.forbidden_methods
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean),
        approved_tools: ['nmap', 'burpsuite', 'sqlmap', 'metasploit'],
        time_restrictions: null
      };

      const scope = await createScopeRequest(project.id, scopeData);
      setScopes((prev) => [...prev, scope]);
      setShowNewScopeForm(false);
      setNewScope({ target_systems: '', excluded_systems: '', forbidden_methods: '' });
      addToast('Scope created', 'success');
    } catch (err: any) {
      addToast(err.response?.data?.detail || 'Failed to create scope', 'error', 6000);
    } finally {
      dismissToast(loadingToast);
      setLoading(false);
    }
  };

  const handleDeleteProject = async () => {
    if (!project) return;
    if (!window.confirm('Are you sure you want to delete this project?')) return;

    setLoading(true);
    const loadingToast = addToast('Deleting project...', 'loading', 8000);
    try {
      await deleteProject(project.id);
      addToast('Project deleted', 'success');
      onBack();
    } catch (err: any) {
      addToast(err.response?.data?.detail || 'Failed to delete project', 'error', 6000);
    } finally {
      dismissToast(loadingToast);
      setLoading(false);
    }
  };

  const handleUpdateProject = async () => {
    if (!project) return;
    const newName = prompt('New project name:', project.name);
    if (!newName) return;

    const loadingToast = addToast('Updating project...', 'loading', 6000);
    try {
      await updateProject(project.id, { name: newName });
      addToast('Project updated', 'success');
      setProject({ ...project, name: newName });
      await loadProjectAndRuns();
    } catch (err: any) {
      addToast(err.response?.data?.detail || 'Failed to update project', 'error', 6000);
    } finally {
      dismissToast(loadingToast);
    }
  };

  const handleCreateRun = async (scopeId: string) => {
    if (!project) return;
    setLoading(true);
    const loadingToast = addToast('Starting pentest run...', 'loading', 10000);
    try {
      const run = await createAndStartRun(project.id, scopeId);
      addToast('Run started', 'success');
      onNavigateRun(run.id);
    } catch (err: any) {
      addToast(err.response?.data?.detail || 'Failed to start pentest run', 'error', 6000);
    } finally {
      dismissToast(loadingToast);
      setLoading(false);
    }
  };

  if (!project) {
    return (
      <div className="main-content">
        <button className="back-button" onClick={onBack}>
          ← Back to Projects
        </button>
        <p className="empty-state">Project not found.</p>
      </div>
    );
  }

  return (
    <div className="main-content">
      <button className="back-button" onClick={onBack}>
        ← Back to Projects
      </button>

      <div className="project-header">
        <div>
          <h2>{project.name}</h2>
          <p>
            <strong>Customer ID:</strong> {project.customer_id}
          </p>
          {project.description && <p>{project.description}</p>}
        </div>
        <div className="header-actions">
          <button className="icon-button" onClick={handleUpdateProject} title="Edit project name">
            ✏️ Edit
          </button>
          <button className="icon-button delete-button" onClick={handleDeleteProject} title="Delete project">
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
                  onChange={(e) => setNewScope({ ...newScope, target_systems: e.target.value })}
                  rows={4}
                  required
                />
              </div>
              <div className="form-group">
                <label>Excluded Systems (one per line)</label>
                <textarea
                  placeholder="192.168.1.1&#10;admin.example.com"
                  value={newScope.excluded_systems}
                  onChange={(e) => setNewScope({ ...newScope, excluded_systems: e.target.value })}
                  rows={2}
                />
              </div>
              <div className="form-group">
                <label>Forbidden Methods (comma-separated)</label>
                <input
                  type="text"
                  placeholder="social_engineering, dos, data_destruction"
                  value={newScope.forbidden_methods}
                  onChange={(e) => setNewScope({ ...newScope, forbidden_methods: e.target.value })}
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
            {scopes.map((scope) => (
              <div key={scope.id} className="scope-card">
                <h4>
                  Scope {scope.id.substring(0, 8)} - {scope.scope_json?.scope_type || 'web_app'}
                </h4>
                <div className="scope-details">
                  {scope.scope_json?.targets && scope.scope_json.targets.length > 0 && (
                    <div>
                      <strong>Targets:</strong>
                      <ul>
                        {scope.scope_json.targets.map((target, i) => (
                          <li key={i}>
                            {target.value} ({target.criticality})
                          </li>
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
                  <p>
                    <strong>Status:</strong>{' '}
                    <span className={`status-${scope.status.toLowerCase()}`}>{scope.status}</span>
                  </p>
                </div>
                <button onClick={() => handleCreateRun(scope.id)} disabled={loading} className="start-button">
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
            {runs.map((run) => (
              <div
                key={run.id}
                className="run-card clickable"
                onClick={() => onNavigateRun(run.id)}
              >
                <h4>Run {run.id.substring(0, 8)}</h4>
                <p>
                  <strong>Status:</strong>{' '}
                  <span className={`status-${run.status.toLowerCase()}`}>{run.status}</span>
                </p>
                <p className="date">
                  Started: {run.started_at ? new Date(run.started_at).toLocaleString() : 'Not started'}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

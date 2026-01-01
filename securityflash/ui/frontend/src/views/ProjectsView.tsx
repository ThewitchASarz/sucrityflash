import React, { useEffect, useState } from 'react';
import { createProject, deleteProject, getProjects } from '../api';
import { useToast } from '../components/ToastProvider';
import { Project } from '../types';

interface ProjectsViewProps {
  onSelectProject: (project: Project) => void;
}

export const ProjectsView: React.FC<ProjectsViewProps> = ({ onSelectProject }) => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [showNewProjectForm, setShowNewProjectForm] = useState(false);
  const [newProject, setNewProject] = useState({
    name: '',
    customer_id: '',
    description: ''
  });
  const [loading, setLoading] = useState(false);
  const { addToast, dismissToast } = useToast();

  useEffect(() => {
    loadProjects();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadProjects = async () => {
    setLoading(true);
    try {
      const data = await getProjects();
      setProjects(data);
    } catch (err) {
      addToast('Failed to load projects', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    const loadingToast = addToast('Creating project...', 'loading', 10000);

    try {
      await createProject(newProject);
      addToast('Project created', 'success');
      setShowNewProjectForm(false);
      setNewProject({ name: '', customer_id: '', description: '' });
      await loadProjects();
    } catch (err: any) {
      addToast(err.response?.data?.detail || 'Failed to create project', 'error', 6000);
    } finally {
      setLoading(false);
      dismissToast(loadingToast);
    }
  };

  const handleDeleteProject = async (projectId: string) => {
    if (!window.confirm('Are you sure you want to delete this project?')) return;

    const loadingToast = addToast('Deleting project...', 'loading', 8000);
    setLoading(true);
    try {
      await deleteProject(projectId);
      addToast('Project deleted', 'success');
      await loadProjects();
    } catch (err: any) {
      addToast(err.response?.data?.detail || 'Failed to delete project', 'error', 6000);
    } finally {
      setLoading(false);
      dismissToast(loadingToast);
    }
  };

  return (
    <div className="main-content">
      <div className="user-actions">
        <button onClick={() => setShowNewProjectForm(!showNewProjectForm)}>
          {showNewProjectForm ? 'Cancel' : '+ New Project'}
        </button>
      </div>

      {showNewProjectForm && (
        <div className="new-project-form">
          <h2>Create New Pentest Project</h2>
          <form onSubmit={handleCreateProject}>
            <div className="form-group">
              <label>Project Name *</label>
              <input
                type="text"
                placeholder="e.g., Dealwyzer.com Security Assessment"
                value={newProject.name}
                onChange={(e) => setNewProject({ ...newProject, name: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <label>Customer ID *</label>
              <input
                type="text"
                placeholder="e.g., cust_123abc"
                value={newProject.customer_id}
                onChange={(e) => setNewProject({ ...newProject, customer_id: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea
                placeholder="Brief description of the engagement..."
                value={newProject.description}
                onChange={(e) => setNewProject({ ...newProject, description: e.target.value })}
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
            {projects.map((project) => (
              <div key={project.id} className="project-card">
                <div className="card-actions">
                  <button
                    className="icon-button delete-button"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteProject(project.id);
                    }}
                    title="Delete project"
                  >
                    🗑️
                  </button>
                </div>
                <div onClick={() => onSelectProject(project)} style={{ cursor: 'pointer' }}>
                  <h3>{project.name}</h3>
                  <p>
                    <strong>Customer ID:</strong> {project.customer_id}
                  </p>
                  <p>
                    <strong>Status:</strong>{' '}
                    <span className={`status-${project.status.toLowerCase()}`}>{project.status}</span>
                  </p>
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
        <p>
          📚{' '}
          <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer">
            V1 API Docs (SecurityFlash)
          </a>
        </p>
        <p>
          🔵{' '}
          <a href="http://localhost:3001/docs" target="_blank" rel="noopener noreferrer">
            V2 BFF Docs (Proxy Layer)
          </a>
        </p>
        <p>
          🔍{' '}
          <a href="http://localhost:8000/redoc" target="_blank" rel="noopener noreferrer">
            ReDoc Documentation
          </a>
        </p>
        <p>
          💚{' '}
          <a href="http://localhost:3001/health" target="_blank" rel="noopener noreferrer">
            V2 BFF Health Check
          </a>
        </p>
      </div>
    </div>
  );
};

import React, { useEffect, useMemo, useState } from 'react';
import './App.css';
import { getHealth, setAuthToken } from './api';
import { ErrorBoundary } from './components/ErrorBoundary';
import { ToastProvider, useToast } from './components/ToastProvider';
import { ProjectsView } from './views/ProjectsView';
import { ProjectDetail } from './views/ProjectDetail';
import { RunDetail } from './views/RunDetail';
import { HealthStatus, Project } from './types';

type Route =
  | { name: 'projects' }
  | { name: 'project-detail'; projectId: string }
  | { name: 'run-detail'; runId: string };

const parseRoute = (hash: string): Route => {
  const path = hash.replace(/^#/, '') || '/';
  const projectMatch = path.match(/^\/projects\/([^/]+)/);
  if (projectMatch) {
    return { name: 'project-detail', projectId: projectMatch[1] };
  }

  const runMatch = path.match(/^\/runs\/([^/]+)/);
  if (runMatch) {
    return { name: 'run-detail', runId: runMatch[1] };
  }

  return { name: 'projects' };
};

const useHashRoute = () => {
  const [hash, setHash] = useState(() => window.location.hash || '#/');

  useEffect(() => {
    if (!window.location.hash) {
      window.location.hash = '#/';
      setHash('#/');
    }
    const handler = () => setHash(window.location.hash || '#/');
    window.addEventListener('hashchange', handler);
    return () => window.removeEventListener('hashchange', handler);
  }, []);

  const route = useMemo(() => parseRoute(hash), [hash]);

  const navigate = (path: string) => {
    const normalized = path.startsWith('#') ? path : `#${path}`;
    window.location.hash = normalized;
    setHash(normalized);
  };

  return { route, navigate };
};

const AppShell: React.FC = () => {
  const { route, navigate } = useHashRoute();
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [token] = useState<string>('demo-token');
  const { addToast } = useToast();

  useEffect(() => {
    setAuthToken(token);
  }, [token]);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const data = await getHealth();
        setHealth(data);
      } catch (err) {
        addToast('Backend is not responding', 'error', 6000);
      }
    };
    fetchHealth();
  }, [addToast]);

  const handleSelectProject = (project: Project) => {
    navigate(`/projects/${project.id}`);
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

        {route.name === 'projects' && <ProjectsView onSelectProject={handleSelectProject} />}
        {route.name === 'project-detail' && (
          <ProjectDetail
            projectId={route.projectId}
            onBack={() => navigate('/')}
            onNavigateRun={(runId) => navigate(`/runs/${runId}`)}
          />
        )}
        {route.name === 'run-detail' && (
          <RunDetail runId={route.runId} onBack={() => navigate('/')} />
        )}
      </header>
    </div>
  );
};

function App() {
  return (
    <ErrorBoundary>
      <ToastProvider>
        <AppShell />
      </ToastProvider>
    </ErrorBoundary>
  );
}

export default App;

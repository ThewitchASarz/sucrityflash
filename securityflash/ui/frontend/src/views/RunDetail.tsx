import React, { useEffect, useRef, useState } from 'react';
import {
  approveAction,
  downloadReport as downloadReportBlob,
  generateAuditBundle,
  generateReport,
  getJob,
  getPendingApprovals,
  getRun,
  getRunEvidence,
  getRunStats,
  getRunTimeline
} from '../api';
import { useToast } from '../components/ToastProvider';
import { Evidence, PendingApproval, Run, RunStats, TimelineEvent } from '../types';

interface RunDetailProps {
  runId: string;
  onBack: () => void;
}

export const RunDetail: React.FC<RunDetailProps> = ({ runId, onBack }) => {
  const [run, setRun] = useState<Run | null>(null);
  const [runStats, setRunStats] = useState<RunStats | null>(null);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [findings, setFindings] = useState<Evidence[]>([]);
  const [pendingApprovals, setPendingApprovals] = useState<PendingApproval[]>([]);
  const [loading, setLoading] = useState(false);
  const pollTimeout = useRef<number | null>(null);
  const { addToast, dismissToast } = useToast();

  useEffect(() => {
    fetchRunData();
    return () => {
      if (pollTimeout.current) {
        window.clearTimeout(pollTimeout.current);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId]);

  const fetchRunData = async () => {
    try {
      const runData = await getRun(runId);
      setRun(runData);

      try {
        const stats = await getRunStats(runId);
        setRunStats(stats);
      } catch {
        /* ignore stats errors */
      }

      try {
        const timelineData = await getRunTimeline(runId);
        setTimeline(timelineData);
      } catch {
        /* ignore timeline errors */
      }

      try {
        const evidence = await getRunEvidence(runId);
        setFindings(evidence);
      } catch {
        /* ignore evidence errors */
      }

      try {
        const approvals = await getPendingApprovals(runId);
        setPendingApprovals(approvals);
      } catch {
        /* ignore approvals errors */
      }

      if (['RUNNING', 'PENDING', 'EXECUTING'].includes(runData.status)) {
        pollTimeout.current = window.setTimeout(fetchRunData, 5000);
      }
    } catch (err) {
      addToast('Failed to load run', 'error', 6000);
    }
  };

  const handleApprove = async (actionId: string) => {
    const loadingToast = addToast('Approving action...', 'loading', 6000);
    try {
      await approveAction(runId, actionId);
      addToast('Action approved', 'success');
      await fetchRunData();
    } catch (err: any) {
      addToast(err.response?.data?.detail || 'Failed to approve action', 'error', 6000);
    } finally {
      dismissToast(loadingToast);
    }
  };

  const pollReportJob = async (jobId: string): Promise<string | null> => {
    for (let i = 0; i < 30; i++) {
      const job = await getJob(jobId);
      if (job.status === 'COMPLETED') {
        return job.result.report_id;
      }
      if (job.status === 'FAILED') {
        addToast('Report generation failed', 'error');
        return null;
      }
      await new Promise((resolve) => setTimeout(resolve, 10000));
    }
    addToast('Report generation timed out', 'error');
    return null;
  };

  const downloadFile = (data: Blob, filename: string) => {
    const url = window.URL.createObjectURL(new Blob([data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
  };

  const handleGenerateReport = async () => {
    const loadingToast = addToast('Generating report...', 'loading', 10000);
    setLoading(true);
    try {
      const response = await generateReport(runId);
      if (response.job_id) {
        const reportId = await pollReportJob(response.job_id);
        if (reportId) {
          const blob = await downloadReportBlob(reportId);
          downloadFile(blob, `pentest-report-${runId}.pdf`);
        }
      } else if (response.report_id) {
        const blob = await downloadReportBlob(response.report_id);
        downloadFile(blob, `pentest-report-${runId}.pdf`);
      }
      addToast('Report ready', 'success');
    } catch (err: any) {
      addToast(err.response?.data?.detail || 'Failed to generate report', 'error', 6000);
    } finally {
      dismissToast(loadingToast);
      setLoading(false);
    }
  };

  const handleAuditBundle = async () => {
    const loadingToast = addToast('Generating audit bundle...', 'loading', 12000);
    setLoading(true);
    try {
      const blob = await generateAuditBundle(runId);
      downloadFile(blob, `audit-bundle-${runId}.zip`);
      addToast('Audit bundle downloaded', 'success');
    } catch (err: any) {
      addToast(err.response?.data?.detail || 'Failed to generate audit bundle', 'error', 6000);
    } finally {
      dismissToast(loadingToast);
      setLoading(false);
    }
  };

  if (!run) {
    return (
      <div className="main-content">
        <button className="back-button" onClick={onBack}>
          ← Back
        </button>
        <p className="empty-state">Run not found.</p>
      </div>
    );
  }

  return (
    <div className="main-content">
      <button className="back-button" onClick={onBack}>
        ← Back to Project
      </button>

      <div className="run-header">
        <h2>Pentest Run {run.id.substring(0, 8)}</h2>
        <div className={`status-badge status-${run.status.toLowerCase()}`}>{run.status}</div>
      </div>

      {runStats && (
        <div className="section">
          <h3>📊 Live Stats (Proof of Work)</h3>
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-value">{runStats.action_specs_count}</div>
              <div className="stat-label">Actions Proposed</div>
            </div>
            <div
              className="stat-card"
              style={{ backgroundColor: runStats.pending_approvals_count > 0 ? '#fff3cd' : undefined }}
            >
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
            <p className="last-activity">
              ⏰ Last activity: {new Date(runStats.last_activity_at).toLocaleString()}
            </p>
          )}
        </div>
      )}

      {pendingApprovals.length > 0 && (
        <div
          className="section"
          style={{ backgroundColor: '#fff3cd', border: '2px solid #ffc107', padding: '20px' }}
        >
          <h3>⏳ PENDING APPROVALS - ACTION REQUIRED</h3>
          <p style={{ marginBottom: '15px', fontWeight: 'bold' }}>
            The following actions need your approval before agents can proceed:
          </p>
          {pendingApprovals.map((approval) => (
            <div
              key={approval.action_id}
              className="approval-card"
              style={{
                backgroundColor: 'white',
                padding: '15px',
                marginBottom: '15px',
                borderRadius: '8px',
                border: '1px solid #ffc107'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ flex: 1 }}>
                  <h4 style={{ margin: '0 0 10px 0' }}>
                    🔧 {approval.tool.toUpperCase()} → {approval.target}
                  </h4>
                  <p style={{ margin: '5px 0' }}>
                    <strong>Arguments:</strong> {approval.arguments.join(' ')}
                  </p>
                  <p style={{ margin: '5px 0' }}>
                    <strong>Justification:</strong> {approval.justification}
                  </p>
                  <p style={{ margin: '5px 0' }}>
                    <strong>Proposed by:</strong> {approval.proposed_by}
                  </p>
                  <p style={{ margin: '5px 0' }}>
                    <span style={{ color: '#dc3545', fontWeight: 'bold' }}>Risk Score: {approval.risk_score}</span>
                    {' | '}
                    <span>Approval Tier: {approval.approval_tier}</span>
                  </p>
                  <p style={{ fontSize: '12px', color: '#666', marginTop: '10px' }}>Action ID: {approval.action_id}</p>
                </div>
                <div style={{ marginLeft: '20px' }}>
                  <button
                    onClick={() => handleApprove(approval.action_id)}
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
              {run.status === 'PENDING' && (
                <div className="activity-item">
                  <span className="agent-icon">⏳</span>
                  <div>
                    <strong>Pentest Queued</strong>
                    <p>Waiting for worker to pick up the job...</p>
                  </div>
                </div>
              )}
              {run.status === 'EXECUTING' && (
                <div className="activity-item">
                  <span className="agent-icon">🔄</span>
                  <div>
                    <strong>Agents Executing</strong>
                    <p>Waiting for activity from V1 API...</p>
                  </div>
                </div>
              )}
              {run.status === 'COMPLETED' && (
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
                    {!['ACTION_PROPOSED', 'ACTION_APPROVED', 'ACTION_EXECUTED', 'EVIDENCE_STORED', 'RUN_STARTED', 'RUN_CREATED'].includes(
                      event.event_type
                    ) && '🤖'}
                  </span>
                  <div>
                    <strong>{event.event_type.replace(/_/g, ' ')}</strong>
                    {event.actor && <p><em>By:</em> {event.actor}</p>}
                    {event.details && (event as any).details.tool && (
                      <p>
                        <strong>Tool:</strong> {(event as any).details.tool} → {(event as any).details.target}
                      </p>
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
          <h3>📊 Evidence Collected ({findings.length})</h3>
          {run.status === 'COMPLETED' && findings.length > 0 && (
            <div className="report-actions">
              <button onClick={handleGenerateReport} disabled={loading}>
                {loading ? 'Generating...' : '📄 Generate Report'}
              </button>
              <button onClick={handleAuditBundle} disabled={loading}>
                {loading ? 'Generating...' : '📦 Download Audit Bundle'}
              </button>
            </div>
          )}
        </div>

        {findings.length === 0 ? (
          <p className="empty-state">
            {run.status === 'RUNNING' ? 'Waiting for evidence from worker...' : 'No evidence collected yet.'}
          </p>
        ) : (
          <div className="findings-list">
            {findings.slice(0, 20).map((evidence) => (
              <div
                key={evidence.id}
                className="finding-card"
                style={{ backgroundColor: '#f8f9fa', border: '1px solid #dee2e6' }}
              >
                <div className="finding-header">
                  <h4>{evidence.evidence_type.replace(/_/g, ' ').toUpperCase()}</h4>
                  <span className="severity-badge" style={{ backgroundColor: '#6c757d' }}>
                    {evidence.validation_status}
                  </span>
                </div>
                <p>
                  <strong>Generated by:</strong> {evidence.generated_by}
                </p>
                {evidence.evidence_metadata && evidence.evidence_metadata.tool_used && (
                  <p>
                    <strong>Tool:</strong> {evidence.evidence_metadata.tool_used}
                  </p>
                )}
                {evidence.evidence_metadata && evidence.evidence_metadata.returncode !== undefined && (
                  <p>
                    <strong>Return code:</strong> {evidence.evidence_metadata.returncode}
                  </p>
                )}
                <p>
                  <strong>Artifact:</strong> {evidence.artifact_uri}
                </p>
                <p style={{ fontSize: '12px', color: '#666' }}>
                  <strong>Hash:</strong> {evidence.artifact_hash.substring(0, 16)}...
                </p>
                <div className="finding-meta">
                  <span>Created: {new Date(evidence.created_at).toLocaleDateString()}</span>
                  <span>Generated: {new Date(evidence.generated_at).toLocaleString()}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

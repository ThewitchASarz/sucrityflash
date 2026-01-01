"""
Report Generation Service - V0.

Generates HTML/Markdown reports from run evidence and timeline.
"""
import json
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from apps.api.models.run import Run
from apps.api.models.scope import Scope
from apps.api.models.action_spec import ActionSpec
from apps.api.models.evidence import Evidence
from apps.api.models.audit_log import AuditLog


class ReportGenerator:
    """Generate reports for completed runs."""

    @staticmethod
    def generate_html_report(run_id: str, db: Session) -> str:
        """
        Generate HTML report for a run.

        Args:
            run_id: Run ID
            db: Database session

        Returns:
            HTML report string
        """
        run = db.query(Run).filter(Run.id == run_id).first()
        if not run:
            raise ValueError(f"Run {run_id} not found")

        scope = db.query(Scope).filter(Scope.id == run.scope_id).first()
        action_specs = db.query(ActionSpec).filter(ActionSpec.run_id == run_id).all()
        evidence_list = db.query(Evidence).filter(Evidence.run_id == run_id).all()
        timeline = db.query(AuditLog).filter(AuditLog.run_id == run_id).order_by(AuditLog.timestamp.asc()).all()

        # Compute statistics
        total_actions = len(action_specs)
        executed_actions = len([a for a in action_specs if a.status.value == "EXECUTED"])
        failed_actions = len([a for a in action_specs if a.status.value == "FAILED"])
        evidence_count = len(evidence_list)

        # Generate report HTML
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SecurityFlash Report - Run {run_id[:8]}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            border-radius: 8px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
        }}
        .header p {{
            margin: 5px 0;
            opacity: 0.9;
        }}
        .section {{
            background: white;
            padding: 30px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .section h2 {{
            margin-top: 0;
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .stat-value {{
            font-size: 36px;
            font-weight: bold;
            color: #667eea;
        }}
        .stat-label {{
            font-size: 14px;
            color: #666;
            margin-top: 5px;
        }}
        .target-list {{
            list-style: none;
            padding: 0;
        }}
        .target-list li {{
            padding: 10px;
            margin: 5px 0;
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            border-radius: 4px;
        }}
        .evidence-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .evidence-table th,
        .evidence-table td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        .evidence-table th {{
            background: #f8f9fa;
            font-weight: 600;
        }}
        .evidence-table tr:hover {{
            background: #f8f9fa;
        }}
        .timeline-event {{
            padding: 15px;
            margin: 10px 0;
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            border-radius: 4px;
        }}
        .timeline-event .timestamp {{
            font-size: 12px;
            color: #666;
        }}
        .timeline-event .event-type {{
            font-weight: 600;
            color: #333;
            margin: 5px 0;
        }}
        .finding-box {{
            background: #fff3cd;
            border: 1px solid #ffc107;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .code {{
            font-family: 'Courier New', monospace;
            background: #f8f9fa;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 14px;
        }}
        .footer {{
            text-align: center;
            color: #666;
            margin-top: 40px;
            padding: 20px;
            border-top: 1px solid #ddd;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>SecurityFlash Pentest Report</h1>
        <p>Run ID: <span class="code">{run.id}</span></p>
        <p>Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        <p>Status: <strong>{run.status.value}</strong></p>
    </div>

    <div class="section">
        <h2>Executive Summary</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{len(scope.scope_json.get('targets', []))}</div>
                <div class="stat-label">Targets Scoped</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{executed_actions}</div>
                <div class="stat-label">Actions Executed</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{evidence_count}</div>
                <div class="stat-label">Evidence Collected</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{failed_actions}</div>
                <div class="stat-label">Failed Actions</div>
            </div>
        </div>
        <p><strong>Started:</strong> {run.started_at.strftime('%Y-%m-%d %H:%M:%S UTC') if run.started_at else 'N/A'}</p>
        <p><strong>Policy Version:</strong> {run.policy_version}</p>
        <p><strong>Agent Started:</strong> {'Yes' if run.agent_started_at else 'No'}</p>
    </div>

    <div class="section">
        <h2>Scope</h2>
        <p><strong>Scope Name:</strong> {scope.name}</p>
        <p><strong>Locked:</strong> {scope.locked_at.strftime('%Y-%m-%d %H:%M:%S UTC') if scope.locked_at else 'Not locked'}</p>
        <h3>Targets</h3>
        <ul class="target-list">
            {"".join([f'<li><span class="code">{t["value"]}</span> - Criticality: {t.get("criticality", "MEDIUM")}</li>' for t in scope.scope_json.get('targets', [])])}
        </ul>
    </div>

    <div class="section">
        <h2>Findings</h2>
        <div class="finding-box">
            <strong>⚠️ V0 Limitation:</strong> No validated findings in V0. This report captures reconnaissance data only.
            <br><br>
            Future versions will include:
            <ul>
                <li>Automated vulnerability detection</li>
                <li>LLM-based finding triage</li>
                <li>Severity scoring and prioritization</li>
                <li>Remediation recommendations</li>
            </ul>
        </div>
    </div>

    <div class="section">
        <h2>Evidence Index</h2>
        <p>Total evidence records: <strong>{evidence_count}</strong></p>
        <table class="evidence-table">
            <thead>
                <tr>
                    <th>Timestamp</th>
                    <th>Type</th>
                    <th>Source</th>
                    <th>Artifacts</th>
                    <th>SHA256 (first artifact)</th>
                </tr>
            </thead>
            <tbody>
                {"".join([f'''
                <tr>
                    <td>{e.collected_at.strftime('%Y-%m-%d %H:%M:%S')}</td>
                    <td>{e.evidence_type}</td>
                    <td><span class="code">{e.source_url or 'N/A'}</span></td>
                    <td>{len(e.metadata.get('artifacts', []))}</td>
                    <td><span class="code">{e.metadata.get('artifacts', [{}])[0].get('sha256', 'N/A')[:16] + '...' if e.metadata.get('artifacts') else 'N/A'}</span></td>
                </tr>
                ''' for e in evidence_list])}
            </tbody>
        </table>
    </div>

    <div class="section">
        <h2>Timeline Summary</h2>
        <p>Key events from run execution (showing first 20):</p>
        {"".join([f'''
        <div class="timeline-event">
            <div class="timestamp">{event.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</div>
            <div class="event-type">{event.event_type}</div>
            <div>Actor: {event.actor}</div>
        </div>
        ''' for event in timeline[:20]])}
        {f'<p><em>... and {len(timeline) - 20} more events</em></p>' if len(timeline) > 20 else ''}
    </div>

    <div class="footer">
        <p>Generated by SecurityFlash Control Plane v1.0</p>
        <p>🤖 This report was produced by an automated agentic pentesting platform with governance controls.</p>
    </div>
</body>
</html>
"""
        return html

    @staticmethod
    def generate_markdown_report(run_id: str, db: Session) -> str:
        """
        Generate Markdown report for a run.

        Args:
            run_id: Run ID
            db: Database session

        Returns:
            Markdown report string
        """
        run = db.query(Run).filter(Run.id == run_id).first()
        if not run:
            raise ValueError(f"Run {run_id} not found")

        scope = db.query(Scope).filter(Scope.id == run.scope_id).first()
        action_specs = db.query(ActionSpec).filter(ActionSpec.run_id == run_id).all()
        evidence_list = db.query(Evidence).filter(Evidence.run_id == run_id).all()
        timeline = db.query(AuditLog).filter(AuditLog.run_id == run_id).order_by(AuditLog.timestamp.asc()).all()

        # Compute statistics
        total_actions = len(action_specs)
        executed_actions = len([a for a in action_specs if a.status.value == "EXECUTED"])
        failed_actions = len([a for a in action_specs if a.status.value == "FAILED"])
        evidence_count = len(evidence_list)

        # Generate Markdown
        md = f"""# SecurityFlash Pentest Report

**Run ID:** `{run.id}`
**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
**Status:** {run.status.value}

---

## Executive Summary

| Metric | Count |
|--------|-------|
| Targets Scoped | {len(scope.scope_json.get('targets', []))} |
| Actions Executed | {executed_actions} |
| Evidence Collected | {evidence_count} |
| Failed Actions | {failed_actions} |

**Started:** {run.started_at.strftime('%Y-%m-%d %H:%M:%S UTC') if run.started_at else 'N/A'}
**Policy Version:** {run.policy_version}
**Agent Started:** {'Yes' if run.agent_started_at else 'No'}

---

## Scope

**Scope Name:** {scope.name}
**Locked:** {scope.locked_at.strftime('%Y-%m-%d %H:%M:%S UTC') if scope.locked_at else 'Not locked'}

### Targets

{"".join([f"- `{t['value']}` - Criticality: {t.get('criticality', 'MEDIUM')}\n" for t in scope.scope_json.get('targets', [])])}

---

## Findings

⚠️ **V0 Limitation:** No validated findings in V0. This report captures reconnaissance data only.

Future versions will include:
- Automated vulnerability detection
- LLM-based finding triage
- Severity scoring and prioritization
- Remediation recommendations

---

## Evidence Index

Total evidence records: **{evidence_count}**

| Timestamp | Type | Source | Artifacts | SHA256 (first) |
|-----------|------|--------|-----------|----------------|
{"".join([f"| {e.collected_at.strftime('%Y-%m-%d %H:%M:%S')} | {e.evidence_type} | `{e.source_url or 'N/A'}` | {len(e.metadata.get('artifacts', []))} | `{e.metadata.get('artifacts', [{}])[0].get('sha256', 'N/A')[:16] + '...' if e.metadata.get('artifacts') else 'N/A'}` |\n" for e in evidence_list])}

---

## Timeline Summary

Key events from run execution (showing first 20):

{"".join([f"- **{event.timestamp.strftime('%Y-%m-%d %H:%M:%S')}** - {event.event_type} (Actor: {event.actor})\n" for event in timeline[:20]])}

{f'... and {len(timeline) - 20} more events' if len(timeline) > 20 else ''}

---

*Generated by SecurityFlash Control Plane v1.0*
🤖 This report was produced by an automated agentic pentesting platform with governance controls.
"""
        return md

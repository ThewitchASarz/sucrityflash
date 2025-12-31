"""
Report Generation Service - HTML/PDF Reports with OWASP Mapping (V2 requirement).

Per spec: "Reports include validated findings only, with OWASP Top 10 mapping."
"""
import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jinja2 import Template
import asyncio

from models.run import Run
from models.finding import Finding
from models.evidence import Evidence
from models.project import Project
from models.scope import Scope
from models.test_plan import TestPlan
from models.report_job import ReportJob, ReportFormat, JobStatus


class ReportService:
    """Service for generating HTML/PDF reports."""

    async def create_report_job(
        self,
        db: AsyncSession,
        run_id: uuid.UUID,
        report_format: ReportFormat,
        requested_by: uuid.UUID
    ) -> ReportJob:
        """
        Create report generation job.

        Args:
            db: Database session
            run_id: Run ID
            report_format: HTML or PDF
            requested_by: User ID

        Returns:
            ReportJob: Created job
        """
        job = ReportJob(
            id=uuid.uuid4(),
            run_id=run_id,
            format=report_format,
            status=JobStatus.QUEUED,
            created_at=datetime.utcnow()
        )

        db.add(job)
        await db.commit()
        await db.refresh(job)

        # Start generation in background
        asyncio.create_task(self._generate_report_background(job.id))

        return job

    async def _generate_report_background(self, job_id: uuid.UUID):
        """Generate report in background."""
        from database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            try:
                # Fetch job
                result = await db.execute(
                    select(ReportJob).where(ReportJob.id == job_id)
                )
                job = result.scalar_one_or_none()

                if not job:
                    return

                # Mark as running
                job.status = JobStatus.RUNNING
                await db.commit()

                # Generate report
                html_content = await self.generate_html_report(db, job.run_id)

                # For PDF, would convert HTML to PDF here
                if job.format == ReportFormat.PDF:
                    # TODO: Implement PDF conversion with weasyprint or similar
                    pdf_content = html_content  # Placeholder
                    content = pdf_content
                else:
                    content = html_content

                # Store report (in production, upload to S3)
                artifact_uri = f"file:///tmp/report_{job.id}.{'pdf' if job.format == ReportFormat.PDF else 'html'}"

                with open(artifact_uri.replace("file://", ""), "w") as f:
                    f.write(content)

                # Mark as completed
                job.status = JobStatus.COMPLETED
                job.artifact_uri = artifact_uri
                job.completed_at = datetime.utcnow()
                await db.commit()

                print(f"✅ Report generated: {artifact_uri}")

            except Exception as e:
                # Mark as failed
                if job:
                    job.status = JobStatus.FAILED
                    job.error = str(e)
                    await db.commit()
                print(f"❌ Report generation failed: {e}")

    async def generate_html_report(
        self,
        db: AsyncSession,
        run_id: uuid.UUID
    ) -> str:
        """
        Generate HTML report with OWASP mapping.

        Returns: HTML content
        """
        # Fetch run
        result = await db.execute(
            select(Run).where(Run.id == run_id)
        )
        run = result.scalar_one_or_none()

        if not run:
            raise ValueError(f"Run {run_id} not found")

        # Fetch test plan
        result = await db.execute(
            select(TestPlan).where(TestPlan.id == run.plan_id)
        )
        test_plan = result.scalar_one_or_none()

        # Fetch project
        result = await db.execute(
            select(Project).where(Project.id == test_plan.project_id)
        )
        project = result.scalar_one_or_none()

        # Fetch scope
        result = await db.execute(
            select(Scope).where(Scope.id == test_plan.scope_id)
        )
        scope = result.scalar_one_or_none()

        # Fetch VALIDATED findings only (V2 requirement)
        result = await db.execute(
            select(Finding)
            .where(Finding.run_id == run_id)
            .where(Finding.validated == True)  # Only validated findings
            .order_by(Finding.severity.desc(), Finding.created_at)
        )
        findings = result.scalars().all()

        # Group findings by OWASP category
        findings_by_owasp = self._group_findings_by_owasp(findings)

        # Group findings by severity
        findings_by_severity = {
            "CRITICAL": [],
            "HIGH": [],
            "MEDIUM": [],
            "LOW": [],
            "INFO": []
        }

        for finding in findings:
            if finding.severity in findings_by_severity:
                findings_by_severity[finding.severity].append(finding)

        # Generate HTML
        html = self._render_html_template(
            run=run,
            project=project,
            scope=scope,
            test_plan=test_plan,
            findings=findings,
            findings_by_owasp=findings_by_owasp,
            findings_by_severity=findings_by_severity
        )

        return html

    def _group_findings_by_owasp(self, findings: List[Finding]) -> dict:
        """Group findings by OWASP category."""
        grouped = {}

        for finding in findings:
            # Handle owasp_mappings (list) - use first category or "Uncategorized"
            if finding.owasp_mappings and len(finding.owasp_mappings) > 0:
                category = finding.owasp_mappings[0]
            else:
                category = "Uncategorized"

            if category not in grouped:
                grouped[category] = []
            grouped[category].append(finding)

        return grouped

    def _render_html_template(
        self,
        run,
        project,
        scope,
        test_plan,
        findings,
        findings_by_owasp,
        findings_by_severity
    ) -> str:
        """Render HTML report template."""
        template = Template(HTML_REPORT_TEMPLATE)

        return template.render(
            report_title=f"Security Assessment Report - {project.name if project else 'Unknown'}",
            generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            run=run,
            project=project,
            scope=scope,
            test_plan=test_plan,
            findings=findings,
            findings_by_owasp=findings_by_owasp,
            findings_by_severity=findings_by_severity,
            total_findings=len(findings),
            critical_count=len(findings_by_severity.get("CRITICAL", [])),
            high_count=len(findings_by_severity.get("HIGH", [])),
            medium_count=len(findings_by_severity.get("MEDIUM", [])),
            low_count=len(findings_by_severity.get("LOW", [])),
            info_count=len(findings_by_severity.get("INFO", []))
        )


# HTML Report Template
HTML_REPORT_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ report_title }}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header {
            border-bottom: 3px solid #e74c3c;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        h1 {
            color: #2c3e50;
            font-size: 32px;
            margin-bottom: 10px;
        }
        .meta {
            color: #7f8c8d;
            font-size: 14px;
        }
        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin: 30px 0;
        }
        .summary-card {
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }
        .summary-card.critical { background: #fee; border-left: 4px solid #c0392b; }
        .summary-card.high { background: #ffe; border-left: 4px solid #e67e22; }
        .summary-card.medium { background: #fef; border-left: 4px solid #f39c12; }
        .summary-card.low { background: #eff; border-left: 4px solid #3498db; }
        .summary-card.info { background: #efe; border-left: 4px solid #2ecc71; }
        .summary-card .count {
            font-size: 36px;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .summary-card .label {
            font-size: 12px;
            text-transform: uppercase;
            color: #7f8c8d;
        }
        .section {
            margin: 40px 0;
        }
        h2 {
            color: #2c3e50;
            font-size: 24px;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #ecf0f1;
        }
        h3 {
            color: #34495e;
            font-size: 18px;
            margin: 20px 0 10px 0;
        }
        .finding {
            background: #f8f9fa;
            border-left: 4px solid #bdc3c7;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 4px;
        }
        .finding.critical { border-left-color: #c0392b; }
        .finding.high { border-left-color: #e67e22; }
        .finding.medium { border-left-color: #f39c12; }
        .finding.low { border-left-color: #3498db; }
        .finding.info { border-left-color: #2ecc71; }
        .finding-title {
            font-size: 18px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 10px;
        }
        .finding-meta {
            font-size: 12px;
            color: #7f8c8d;
            margin-bottom: 15px;
        }
        .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 11px;
            font-weight: bold;
            text-transform: uppercase;
            margin-right: 10px;
        }
        .badge.critical { background: #c0392b; color: white; }
        .badge.high { background: #e67e22; color: white; }
        .badge.medium { background: #f39c12; color: white; }
        .badge.low { background: #3498db; color: white; }
        .badge.info { background: #2ecc71; color: white; }
        .finding-description {
            margin-bottom: 15px;
            line-height: 1.8;
        }
        .finding-remediation {
            background: #e8f5e9;
            padding: 15px;
            border-radius: 4px;
            margin-top: 15px;
        }
        .finding-remediation h4 {
            color: #2e7d32;
            margin-bottom: 10px;
        }
        .footer {
            margin-top: 50px;
            padding-top: 20px;
            border-top: 2px solid #ecf0f1;
            text-align: center;
            color: #7f8c8d;
            font-size: 12px;
        }
        .owasp-section {
            background: #f0f7ff;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .owasp-title {
            color: #1565c0;
            font-weight: bold;
            margin-bottom: 15px;
        }
        .validated-badge {
            display: inline-block;
            background: #4caf50;
            color: white;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 10px;
            margin-left: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔒 {{ report_title }}</h1>
            <p class="meta">
                Generated: {{ generated_at }} |
                Run ID: {{ run.id if run else 'N/A' }} |
                Status: {{ run.status if run else 'N/A' }}
            </p>
        </div>

        <div class="section">
            <h2>📊 Executive Summary</h2>
            <div class="summary">
                <div class="summary-card critical">
                    <div class="count">{{ critical_count }}</div>
                    <div class="label">Critical</div>
                </div>
                <div class="summary-card high">
                    <div class="count">{{ high_count }}</div>
                    <div class="label">High</div>
                </div>
                <div class="summary-card medium">
                    <div class="count">{{ medium_count }}</div>
                    <div class="label">Medium</div>
                </div>
                <div class="summary-card low">
                    <div class="count">{{ low_count }}</div>
                    <div class="label">Low</div>
                </div>
                <div class="summary-card info">
                    <div class="count">{{ info_count }}</div>
                    <div class="label">Info</div>
                </div>
            </div>
        </div>

        {% if project %}
        <div class="section">
            <h2>🎯 Scope Information</h2>
            <p><strong>Project:</strong> {{ project.name }}</p>
            {% if scope %}
            <p><strong>Target:</strong> {{ scope.target_type }}: {{ scope.targets[:5]|join(', ') }}{% if scope.targets|length > 5 %} (+{{ scope.targets|length - 5 }} more){% endif %}</p>
            {% endif %}
        </div>
        {% endif %}

        <div class="section">
            <h2>🔍 Validated Findings (OWASP Top 10 Mapping)</h2>
            <p style="margin-bottom: 20px; color: #2e7d32;">
                ✓ All findings in this report have been validated by ValidatorAgent
            </p>

            {% if findings_by_owasp %}
                {% for owasp_cat, cat_findings in findings_by_owasp.items() %}
                <div class="owasp-section">
                    <div class="owasp-title">{{ owasp_cat }} ({{ cat_findings|length }} findings)</div>

                    {% for finding in cat_findings %}
                    <div class="finding {{ finding.severity|lower }}">
                        <div class="finding-title">
                            {{ finding.title }}
                            <span class="validated-badge">✓ VALIDATED</span>
                        </div>
                        <div class="finding-meta">
                            <span class="badge {{ finding.severity|lower }}">{{ finding.severity }}</span>
                            <span>Validated: {{ finding.validated_at.strftime('%Y-%m-%d %H:%M') if finding.validated_at else 'N/A' }}</span>
                        </div>
                        <div class="finding-description">
                            {{ finding.description or 'No description provided.' }}
                        </div>
                        {% if finding.remediation %}
                        <div class="finding-remediation">
                            <h4>💡 Remediation</h4>
                            {{ finding.remediation }}
                        </div>
                        {% endif %}
                    </div>
                    {% endfor %}
                </div>
                {% endfor %}
            {% else %}
                <p>No validated findings.</p>
            {% endif %}
        </div>

        <div class="footer">
            <p><strong>SecurityFlash V2 MVP</strong></p>
            <p>🤖 Generated with AI-powered penetration testing platform</p>
            <p>This report contains only validated findings as per security policy.</p>
        </div>
    </div>
</body>
</html>
"""


# Global instance
report_service = ReportService()

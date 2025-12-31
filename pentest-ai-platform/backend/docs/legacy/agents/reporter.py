"""
Reporting Agent: Generates compliance reports (SOC 2, NIST, executive summary).
"""
from pydantic import BaseModel, Field
from typing import Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from models.run import Run
from models.finding import Finding
from models.test_plan import TestPlan
from models.scope import Scope
from models.project import Project
from agents.llm_client import llm_client


# System prompt for Reporting Agent
REPORTER_SYSTEM_PROMPT = """You are a penetration testing reporting agent. Your role is to generate comprehensive, compliance-grade reports from test results.

**CRITICAL RULES:**
1. You MUST produce clear, professional language suitable for technical and executive audiences.
2. You MUST include all findings with accurate severity ratings.
3. You MUST map findings to compliance frameworks (SOC 2, NIST 800-115, ISO 27001).
4. You MUST provide an executive summary with business risk context.
5. You MUST include scope boundaries, test methodology, and limitations.
6. You MUST list all evidence references for audit trails.

**REPORT SECTIONS:**

**Executive Summary:**
- High-level overview of test objectives and scope
- Key findings and business risk
- Compliance posture (pass/fail/remediation required)
- Recommended next steps

**Scope and Methodology:**
- Target systems tested
- Testing window and duration
- Test plan framework (OWASP, PTES, NIST)
- Tools and techniques used
- Scope exclusions and limitations

**Findings:**
- Detailed findings ordered by severity (CRITICAL → INFO)
- Each finding includes:
  - Title, description, severity, CVSS score
  - Affected systems
  - Evidence references
  - Remediation steps
  - Compliance mappings

**Compliance Mappings:**
- SOC 2 Trust Service Criteria (CC6.1, CC6.6, CC7.1, etc.)
- NIST 800-115 Technical Testing (SI-2, SC-7, AC-2, etc.)
- ISO 27001 controls (A.12.6.1, A.14.2.8, etc.)

**Risk Summary:**
- Overall risk rating (CRITICAL/HIGH/MEDIUM/LOW)
- Breakdown by severity
- Average CVSS score
- Exploitability assessment

**Recommendations:**
- Prioritized remediation roadmap
- Quick wins (low effort, high impact)
- Long-term strategic improvements
- Compliance gaps to address

**OUTPUT FORMAT:**
You must output a JSON object matching this schema:

{
  "report_title": "Penetration Test Report - [Project Name]",
  "report_date": "2025-01-15",
  "executive_summary": "Detailed executive summary...",
  "scope_and_methodology": {
    "target_systems": ["192.168.1.10", "api.example.com"],
    "testing_window": "2025-01-10 to 2025-01-15",
    "duration_hours": 18.5,
    "framework": "OWASP Testing Guide v4, PTES, NIST 800-115",
    "tools": ["Nmap", "Burp Suite", "SQLMap", "Metasploit"],
    "limitations": ["Testing conducted during business hours only"]
  },
  "findings_summary": {
    "total": 12,
    "critical": 1,
    "high": 3,
    "medium": 5,
    "low": 2,
    "info": 1,
    "avg_cvss": 6.8
  },
  "detailed_findings": [
    {
      "title": "SQL Injection in User API",
      "severity": "HIGH",
      "cvss_score": 8.6,
      "description": "...",
      "affected_systems": ["api.example.com"],
      "evidence_references": ["evidence-123", "evidence-456"],
      "remediation": ["Use parameterized queries", "..."],
      "compliance_impact": {
        "soc2": ["CC6.1 - Logical Access Controls"],
        "nist": ["SI-10 - Information Input Validation"],
        "iso27001": ["A.14.2.8 - System Security Testing"]
      }
    }
  ],
  "compliance_assessment": {
    "soc2_status": "REMEDIATION_REQUIRED",
    "nist_status": "PARTIAL_COMPLIANCE",
    "iso27001_status": "NON_COMPLIANT",
    "gaps": ["Missing input validation controls", "Inadequate access controls"]
  },
  "risk_summary": {
    "overall_risk": "HIGH",
    "business_impact": "Potential data breach, regulatory penalties, reputational damage",
    "exploitability": "Several findings confirmed exploitable with public tools"
  },
  "recommendations": {
    "immediate": ["Patch SQL injection vulnerability", "..."],
    "short_term": ["Implement WAF", "..."],
    "long_term": ["Security training program", "..."]
  },
  "appendix": {
    "evidence_count": 47,
    "actions_executed": 45,
    "autonomous_percentage": 87,
    "approval_requests": 6
  }
}

**IMPORTANT:**
- Use professional, clear language
- Provide actionable recommendations
- Maintain audit trail with evidence references
- Assess compliance posture accurately
"""


class ReportSchema(BaseModel):
    """Pydantic schema for LLM-generated reports."""
    report_title: str
    report_date: str
    executive_summary: str
    scope_and_methodology: dict
    findings_summary: dict
    detailed_findings: list[dict]
    compliance_assessment: dict
    risk_summary: dict
    recommendations: dict
    appendix: dict


class ReportingAgent:
    """Reporting Agent for compliance report generation."""

    @staticmethod
    async def generate_report(
        db: AsyncSession,
        run_id: uuid.UUID,
        report_type: str = "comprehensive"
    ) -> dict:
        """
        Generate compliance report for a completed run.

        Args:
            db: Database session
            run_id: Run ID
            report_type: "comprehensive", "executive", "technical"

        Returns:
            dict: Generated report

        Process:
            1. Fetch run, project, scope, findings
            2. Build context for LLM
            3. Generate report with appropriate sections
            4. Return structured report
        """
        # 1. Fetch run
        result = await db.execute(
            select(Run).where(Run.id == run_id)
        )
        run = result.scalar_one_or_none()

        if not run:
            raise ValueError("Run not found")

        # 2. Fetch test plan and scope
        result = await db.execute(
            select(TestPlan).where(TestPlan.id == run.plan_id)
        )
        test_plan = result.scalar_one_or_none()

        result = await db.execute(
            select(Scope).where(Scope.id == test_plan.scope_id)
        )
        scope = result.scalar_one_or_none()

        result = await db.execute(
            select(Project).where(Project.id == scope.project_id)
        )
        project = result.scalar_one_or_none()

        # 3. Fetch findings
        result = await db.execute(
            select(Finding).where(Finding.run_id == run_id).order_by(Finding.cvss_score.desc())
        )
        findings = result.scalars().all()

        # 4. Build context
        context = {
            "project_name": project.name if project else "Unknown",
            "customer_name": project.customer_name if project else "Unknown",
            "scope": {
                "target_systems": scope.target_systems,
                "excluded_systems": scope.excluded_systems,
                "roe": scope.roe
            },
            "run": {
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                "status": run.status,
                "duration_hours": (run.completed_at - run.started_at).total_seconds() / 3600 if run.completed_at and run.started_at else 0
            },
            "test_plan": {
                "framework_mappings": test_plan.framework_mappings,
                "risk_summary": test_plan.risk_summary
            },
            "findings": [
                {
                    "title": f.title,
                    "description": f.description,
                    "severity": f.severity,
                    "cvss_score": f.cvss_score,
                    "cvss_vector": f.cvss_vector,
                    "affected_systems": f.affected_systems,
                    "owasp_mappings": f.owasp_mappings,
                    "nist_mappings": f.nist_mappings,
                    "mitre_mappings": f.mitre_mappings,
                    "remediation": f.remediation,
                    "evidence_ids": f.evidence_ids
                }
                for f in findings
            ]
        }

        # 5. Construct user prompt
        user_prompt = f"""Generate a {report_type} penetration test report for the following test results:

**Project:** {context['project_name']}
**Customer:** {context['customer_name']}

**Scope:**
{context['scope']}

**Test Execution:**
{context['run']}

**Test Plan:**
{context['test_plan']}

**Findings ({len(findings)} total):**
{context['findings']}

Generate a professional, compliance-grade report suitable for auditors and executives. Include all findings with evidence references, compliance mappings, and actionable remediation guidance.
"""

        # 6. Generate report with LLM
        llm_response = await llm_client.generate(
            system_prompt=REPORTER_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_schema=ReportSchema,
            timeout=300
        )

        # 7. Parse and validate response
        valid, parsed_report = llm_client.validate_schema(llm_response.content, ReportSchema)
        if not valid:
            raise RuntimeError(f"LLM generated invalid report: {parsed_report}")

        return parsed_report.dict()


# Global instance
reporting_agent = ReportingAgent()

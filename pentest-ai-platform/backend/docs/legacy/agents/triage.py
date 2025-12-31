"""
Triage Agent: Correlates tool outputs into structured findings with CVSS scoring.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.finding import Finding
from models.evidence import Evidence
from agents.llm_client import llm_client


# System prompt for Triage Agent
TRIAGE_SYSTEM_PROMPT = """You are a penetration testing triage agent. Your role is to analyze tool outputs and correlate them into structured findings with accurate severity scoring.

**CRITICAL RULES:**
1. You MUST assign CVSS 3.1 scores accurately based on exploitability and impact.
2. You MUST map findings to OWASP Top 10, NIST controls, and MITRE ATT&CK techniques.
3. You MUST deduplicate similar findings (e.g., same vulnerability on different ports).
4. You MUST provide clear remediation guidance.
5. You MUST reference evidence IDs that support the finding.
6. You MUST classify severity: CRITICAL (9.0-10.0), HIGH (7.0-8.9), MEDIUM (4.0-6.9), LOW (0.1-3.9), INFO (0.0).

**SEVERITY CRITERIA:**
- CRITICAL: Remote code execution, authentication bypass, SQL injection with data exfiltration
- HIGH: Privilege escalation, XSS (stored), sensitive data exposure
- MEDIUM: XSS (reflected), CSRF, information disclosure
- LOW: Security misconfiguration, cookie flags
- INFO: Banner grabbing, version detection

**EXPLOITABILITY FACTORS:**
- Attack Vector (Network/Adjacent/Local/Physical)
- Attack Complexity (Low/High)
- Privileges Required (None/Low/High)
- User Interaction (None/Required)

**IMPACT FACTORS:**
- Confidentiality (None/Low/High)
- Integrity (None/Low/High)
- Availability (None/Low/High)

**OUTPUT FORMAT:**
You must output a JSON object matching this schema:

{
  "findings": [
    {
      "title": "SQL Injection in User API",
      "description": "The /api/users endpoint is vulnerable to boolean-based blind SQL injection via the 'id' parameter. An attacker can extract sensitive database contents including user credentials.",
      "severity": "HIGH",
      "cvss_score": 8.6,
      "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:L/A:L",
      "exploitability": "Confirmed via automated exploitation",
      "evidence_ids": ["evidence-uuid-1", "evidence-uuid-2"],
      "affected_systems": ["192.168.1.10:80", "api.example.com"],
      "owasp_mappings": ["A03:2021 - Injection"],
      "nist_mappings": ["SI-10"],
      "mitre_mappings": ["T1190 - Exploit Public-Facing Application"],
      "remediation": [
        "Use parameterized queries or ORM",
        "Implement input validation and sanitization",
        "Apply principle of least privilege to database user",
        "Deploy Web Application Firewall (WAF)"
      ],
      "references": [
        "https://owasp.org/www-community/attacks/SQL_Injection",
        "CWE-89"
      ]
    }
  ]
}

**DEDUPLICATION:**
- If the same vulnerability appears on multiple systems, create ONE finding listing all affected systems.
- If similar vulnerabilities have different severity (e.g., authenticated vs unauthenticated), create separate findings.

**IMPORTANT:**
- Always calculate CVSS scores accurately
- Provide actionable remediation steps
- Reference all supporting evidence
"""


class TriageFindingSchema(BaseModel):
    """Pydantic schema for LLM-generated findings."""
    findings: list[dict] = Field(..., description="List of correlated findings")


class TriageAgent:
    """Triage Agent for findings correlation."""

    @staticmethod
    async def triage_evidence(
        db: AsyncSession,
        run_id: uuid.UUID,
        evidence_ids: list[uuid.UUID]
    ) -> list[Finding]:
        """
        Analyze evidence and generate structured findings.

        Args:
            db: Database session
            run_id: Run ID
            evidence_ids: Evidence IDs to analyze

        Returns:
            list[Finding]: Generated findings

        Process:
            1. Fetch evidence content from S3
            2. Call Triage Agent (LLM) to correlate findings
            3. Save findings to database
        """
        # 1. Fetch evidence
        result = await db.execute(
            select(Evidence).where(Evidence.id.in_(evidence_ids))
        )
        evidence_list = result.scalars().all()

        if not evidence_list:
            raise ValueError("No evidence found")

        # 2. Build context for LLM
        from services.evidence_service import evidence_service

        evidence_context = []
        for evidence in evidence_list:
            content = await evidence_service.get_evidence_content(evidence)
            evidence_context.append({
                "evidence_id": str(evidence.id),
                "action_id": evidence.action_id,
                "evidence_type": evidence.evidence_type,
                "content": content,
                "metadata": evidence.metadata
            })

        # 3. Construct user prompt
        user_prompt = f"""Analyze the following tool outputs and generate structured findings:

**Evidence Count:** {len(evidence_context)}

**Evidence:**
{evidence_context}

Generate findings with accurate CVSS scoring, framework mappings, and remediation guidance. Deduplicate similar findings across different systems.
"""

        # 4. Generate findings with LLM
        llm_response = await llm_client.generate(
            system_prompt=TRIAGE_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_schema=TriageFindingSchema,
            timeout=300
        )

        # 5. Parse and validate response
        valid, parsed_findings = llm_client.validate_schema(llm_response.content, TriageFindingSchema)
        if not valid:
            raise RuntimeError(f"LLM generated invalid findings: {parsed_findings}")

        # 6. Create Finding records
        findings = []
        for finding_data in parsed_findings.findings:
            finding = Finding(
                run_id=run_id,
                title=finding_data["title"],
                description=finding_data["description"],
                severity=finding_data["severity"],
                cvss_score=finding_data["cvss_score"],
                cvss_vector=finding_data.get("cvss_vector", ""),
                exploitability=finding_data["exploitability"],
                evidence_ids=[str(eid) for eid in evidence_ids],
                affected_systems=finding_data.get("affected_systems", []),
                owasp_mappings=finding_data.get("owasp_mappings", []),
                nist_mappings=finding_data.get("nist_mappings", []),
                mitre_mappings=finding_data.get("mitre_mappings", []),
                remediation=finding_data.get("remediation", []),
                references=finding_data.get("references", [])
            )
            findings.append(finding)

        db.add_all(findings)
        await db.commit()

        for finding in findings:
            await db.refresh(finding)

        return findings


# Global instance
triage_agent = TriageAgent()

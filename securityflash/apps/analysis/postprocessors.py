"""
Post-Execution Analyzers - Auto-findings from SAFE recon outputs.

NO EXPLOITATION. Only creates INFO/LOW findings from safe reconnaissance data.

Findings are created in DRAFT status for human curation.
"""
import json
import logging
import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from apps.api.models.execution import Execution, ExecutionStatus
from apps.api.models.finding import Finding, FindingSeverity, FindingCategory, FindingStatus
from apps.api.services.audit_service import audit_log

logger = logging.getLogger(__name__)


class PostExecutionAnalyzer:
    """
    Analyzes completed executions and creates auto-findings.

    All findings are DRAFT status for human review.
    """

    @staticmethod
    def analyze_execution(db: Session, execution: Execution) -> List[Finding]:
        """
        Analyze a completed execution and generate auto-findings.

        Args:
            db: Database session
            execution: Completed Execution record

        Returns:
            List of created Finding records
        """
        if execution.status != ExecutionStatus.FINISHED:
            logger.debug(f"Execution {execution.id} not finished, skipping analysis")
            return []

        findings = []

        # Route to appropriate analyzer based on tool
        if execution.tool_name == "httpx":
            findings.extend(PostExecutionAnalyzer._analyze_httpx(db, execution))
        elif execution.tool_name == "nmap":
            findings.extend(PostExecutionAnalyzer._analyze_nmap(db, execution))
        elif execution.tool_name == "subfinder":
            findings.extend(PostExecutionAnalyzer._analyze_subfinder(db, execution))

        logger.info(f"Created {len(findings)} auto-findings from execution {execution.id}")

        return findings

    @staticmethod
    def _analyze_httpx(db: Session, execution: Execution) -> List[Finding]:
        """
        Analyze httpx output for HTTP-related findings.

        Creates INFO findings for:
        - Plain HTTP endpoints (no TLS)
        - Redirect chains/loops
        - Unexpected HTTP methods
        """
        findings = []

        # Get stdout from evidence
        if not execution.stdout_evidence_id:
            return findings

        from apps.api.models.evidence import Evidence
        evidence = db.query(Evidence).filter(Evidence.id == execution.stdout_evidence_id).first()
        if not evidence:
            return findings

        stdout = evidence.metadata.get("stdout", "")
        target = execution.metadata_json.get("target", "unknown")

        # Check for plain HTTP (no TLS)
        if target.startswith("http://"):
            finding = Finding(
                run_id=execution.run_id,
                project_id=execution.project_id,
                scope_id=execution.scope_id,
                title=f"Plain HTTP endpoint discovered: {target}",
                severity=FindingSeverity.INFO,
                category=FindingCategory.EXPOSURE,
                affected_target=target,
                description_md=f"""## Plain HTTP Endpoint

The target `{target}` is accessible over plain HTTP without TLS encryption.

**Impact**: Traffic to this endpoint is transmitted in cleartext and could be intercepted.

**Recommendation**: Enforce HTTPS and implement HTTP to HTTPS redirect.
""",
                reproducibility_md=f"""1. Execute: `curl -I {target}`
2. Observe HTTP response without TLS encryption
""",
                evidence_ids=[str(execution.stdout_evidence_id)],
                status=FindingStatus.DRAFT,
                created_by="auto-analyzer"
            )
            db.add(finding)
            findings.append(finding)

        # Check for redirect chains
        if "redirect" in stdout.lower() or "location:" in stdout.lower():
            finding = Finding(
                run_id=execution.run_id,
                project_id=execution.project_id,
                scope_id=execution.scope_id,
                title=f"HTTP redirect detected: {target}",
                severity=FindingSeverity.INFO,
                category=FindingCategory.CONFIG,
                affected_target=target,
                description_md=f"""## HTTP Redirect

The endpoint `{target}` returns an HTTP redirect response.

**Observation**: Multiple redirects or redirect loops can impact performance and user experience.

**Recommendation**: Review redirect configuration and minimize redirect chains.
""",
                reproducibility_md=f"""1. Execute: `curl -I -L {target}`
2. Observe Location headers and redirect chain
""",
                evidence_ids=[str(execution.stdout_evidence_id)],
                status=FindingStatus.DRAFT,
                created_by="auto-analyzer"
            )
            db.add(finding)
            findings.append(finding)

        db.commit()

        # Audit log
        for finding in findings:
            audit_log(
                db=db,
                run_id=execution.run_id,
                event_type="AUTO_FINDING_CREATED",
                actor="auto-analyzer",
                details={
                    "finding_id": str(finding.id),
                    "execution_id": str(execution.id),
                    "tool": "httpx",
                    "severity": finding.severity.value
                }
            )

        return findings

    @staticmethod
    def _analyze_nmap(db: Session, execution: Execution) -> List[Finding]:
        """
        Analyze nmap output for open ports and services.

        Creates INFO/LOW findings for:
        - Open ports discovered
        - Unexpected services exposed
        """
        findings = []

        # Get stdout from evidence
        if not execution.stdout_evidence_id:
            return findings

        from apps.api.models.evidence import Evidence
        evidence = db.query(Evidence).filter(Evidence.id == execution.stdout_evidence_id).first()
        if not evidence:
            return findings

        stdout = evidence.metadata.get("stdout", "")
        target = execution.metadata_json.get("target", "unknown")

        # Parse open ports from nmap output
        open_ports = []
        for line in stdout.split('\n'):
            # Look for lines like: "80/tcp   open  http"
            match = re.match(r'(\d+)/tcp\s+open\s+(\S+)', line)
            if match:
                port = match.group(1)
                service = match.group(2)
                open_ports.append({"port": port, "service": service})

        if open_ports:
            ports_list = ", ".join([f"{p['port']}/{p['service']}" for p in open_ports])

            # Determine severity based on number of open ports
            severity = FindingSeverity.INFO
            if len(open_ports) > 10:
                severity = FindingSeverity.LOW

            finding = Finding(
                run_id=execution.run_id,
                project_id=execution.project_id,
                scope_id=execution.scope_id,
                title=f"{len(open_ports)} open ports discovered on {target}",
                severity=severity,
                category=FindingCategory.NETWORK,
                affected_target=target,
                description_md=f"""## Open Ports Discovered

Nmap scan discovered {len(open_ports)} open TCP ports on `{target}`:

{chr(10).join([f"- Port {p['port']}: {p['service']}" for p in open_ports])}

**Impact**: Each open port expands the attack surface. Unnecessary services should be disabled.

**Recommendation**: Review each service and disable any that are not required.
""",
                reproducibility_md=f"""1. Execute: `nmap -sV -T3 --top-ports 100 {target}`
2. Observe open ports in scan results
""",
                evidence_ids=[str(execution.stdout_evidence_id)],
                status=FindingStatus.DRAFT,
                created_by="auto-analyzer"
            )
            db.add(finding)
            findings.append(finding)

        db.commit()

        # Audit log
        for finding in findings:
            audit_log(
                db=db,
                run_id=execution.run_id,
                event_type="AUTO_FINDING_CREATED",
                actor="auto-analyzer",
                details={
                    "finding_id": str(finding.id),
                    "execution_id": str(execution.id),
                    "tool": "nmap",
                    "open_ports_count": len(open_ports)
                }
            )

        return findings

    @staticmethod
    def _analyze_subfinder(db: Session, execution: Execution) -> List[Finding]:
        """
        Analyze subfinder output for subdomain discovery.

        Creates INFO findings for:
        - Number of subdomains discovered
        - Potentially sensitive subdomains (dev, staging, admin, etc.)
        """
        findings = []

        # Get stdout from evidence
        if not execution.stdout_evidence_id:
            return findings

        from apps.api.models.evidence import Evidence
        evidence = db.query(Evidence).filter(Evidence.id == execution.stdout_evidence_id).first()
        if not evidence:
            return findings

        stdout = evidence.metadata.get("stdout", "")
        target = execution.metadata_json.get("target", "unknown")

        # Count subdomains (one per line in subfinder output)
        subdomains = [line.strip() for line in stdout.split('\n') if line.strip()]
        subdomain_count = len(subdomains)

        if subdomain_count > 0:
            # Check for potentially sensitive subdomain names
            sensitive_patterns = ['dev', 'staging', 'test', 'admin', 'internal', 'vpn', 'backup']
            sensitive_subdomains = []

            for subdomain in subdomains:
                for pattern in sensitive_patterns:
                    if pattern in subdomain.lower():
                        sensitive_subdomains.append(subdomain)
                        break

            severity = FindingSeverity.INFO
            if sensitive_subdomains:
                severity = FindingSeverity.LOW

            description = f"""## Subdomains Discovered

Subdomain enumeration discovered {subdomain_count} subdomains for `{target}`.
"""

            if sensitive_subdomains:
                description += f"""
**Potentially Sensitive Subdomains** ({len(sensitive_subdomains)}):

{chr(10).join([f"- {s}" for s in sensitive_subdomains[:10]])}
{'...' if len(sensitive_subdomains) > 10 else ''}

These subdomains may expose non-production or administrative interfaces.
"""

            description += """
**Recommendation**: Review each subdomain to ensure it is intentionally exposed and properly secured.
"""

            finding = Finding(
                run_id=execution.run_id,
                project_id=execution.project_id,
                scope_id=execution.scope_id,
                title=f"{subdomain_count} subdomains discovered for {target}",
                severity=severity,
                category=FindingCategory.RECON,
                affected_target=target,
                description_md=description,
                reproducibility_md=f"""1. Execute: `subfinder -d {target} -silent`
2. Observe discovered subdomains
""",
                evidence_ids=[str(execution.stdout_evidence_id)],
                status=FindingStatus.DRAFT,
                created_by="auto-analyzer"
            )
            db.add(finding)
            findings.append(finding)

        db.commit()

        # Audit log
        for finding in findings:
            audit_log(
                db=db,
                run_id=execution.run_id,
                event_type="AUTO_FINDING_CREATED",
                actor="auto-analyzer",
                details={
                    "finding_id": str(finding.id),
                    "execution_id": str(execution.id),
                    "tool": "subfinder",
                    "subdomain_count": subdomain_count
                }
            )

        return findings

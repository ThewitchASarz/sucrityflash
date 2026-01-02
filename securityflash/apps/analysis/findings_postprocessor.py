"""
Findings Postprocessor - Phase 2/3

Converts safe execution outputs into DRAFT findings using validators.
Links evidence and generates reproducibility instructions.
"""
from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from apps.api.models.finding import Finding, FindingSeverity, FindingStatus, FindingCategory
from apps.api.models.evidence import Evidence
from apps.analysis.validators.tls_posture_validator import TLSPostureValidator
from apps.analysis.validators.header_validator import HeaderValidator
from apps.analysis.validators.exposure_validator import ExposureValidator

logger = logging.getLogger(__name__)


class FindingsPostprocessor:
    """
    Postprocessor that generates DRAFT findings from execution evidence.

    Phase 2/3: Higher finding yield through deterministic analysis.
    NO autonomous exploitation - only safe reconnaissance findings.
    """

    def __init__(self):
        self.validators = [
            TLSPostureValidator(),
            HeaderValidator(),
            ExposureValidator(),
        ]

    def process_evidence(
        self,
        evidence: Evidence,
        run_id: UUID,
        project_id: UUID,
        scope_id: UUID,
        db: Session
    ) -> List[Finding]:
        """
        Process evidence and generate DRAFT findings.

        Args:
            evidence: Evidence object from database
            run_id: Run UUID
            project_id: Project UUID
            scope_id: Scope UUID
            db: Database session

        Returns:
            List of created Finding objects
        """
        findings_created = []

        # Prepare evidence data for validators
        evidence_data = {
            "evidence_id": str(evidence.id),
            "tool": evidence.tool_name,
            "target": evidence.target,
            "stdout": evidence.stdout,
            "stderr": evidence.stderr,
            "output": evidence.stdout,  # Alias
            "exit_code": evidence.exit_code,
        }

        # Run all validators
        for validator in self.validators:
            try:
                draft_findings = validator.validate(evidence_data)

                for draft in draft_findings:
                    # Create Finding object
                    finding = Finding(
                        run_id=run_id,
                        project_id=project_id,
                        scope_id=scope_id,
                        title=draft["title"],
                        severity=FindingSeverity[draft["severity"]],
                        category=FindingCategory[draft.get("category", "OTHER")],
                        affected_target=draft["affected_target"],
                        description_md=draft["description_md"],
                        evidence_ids=draft.get("evidence_ids", []),
                        status=FindingStatus.DRAFT,
                        created_by=f"validator-{validator.__class__.__name__}",
                    )

                    # Generate reproducibility instructions
                    finding.reproducibility_md = self._generate_reproducibility(
                        evidence=evidence,
                        finding_title=draft["title"]
                    )

                    db.add(finding)
                    findings_created.append(finding)

                    logger.info(
                        f"Created DRAFT finding: {finding.title} "
                        f"(severity={finding.severity.value}, validator={validator.__class__.__name__})"
                    )

            except Exception as e:
                logger.error(
                    f"Validator {validator.__class__.__name__} failed on evidence {evidence.id}: {e}",
                    exc_info=True
                )

        # Commit findings
        if findings_created:
            db.commit()
            logger.info(f"Created {len(findings_created)} DRAFT findings from evidence {evidence.id}")

        return findings_created

    def _generate_reproducibility(self, evidence: Evidence, finding_title: str) -> str:
        """
        Generate reproducibility instructions for finding.

        Args:
            evidence: Evidence object
            finding_title: Finding title

        Returns:
            Markdown reproducibility instructions
        """
        reproducibility_md = f"""## Reproducibility Steps

This finding was automatically identified from tool execution.

### Tool Executed
- **Tool:** `{evidence.tool_name}`
- **Target:** `{evidence.target}`
- **Command:** `{evidence.command or 'N/A'}`
- **Exit Code:** `{evidence.exit_code}`

### Reproduction
To reproduce this finding:

1. Execute the same tool against the target:
   ```bash
   {evidence.command or f'{evidence.tool_name} {evidence.target}'}
   ```

2. Analyze the output for the identified issue: **{finding_title}**

3. Verify the finding manually by:
   - Reviewing the raw tool output
   - Confirming the security implication
   - Testing if the issue can be exploited (within scope)

### Evidence Reference
- Evidence ID: `{evidence.id}`
- Execution Timestamp: `{evidence.created_at}`

### Next Steps
- Mark finding as **NEEDS_REVIEW** after manual verification
- Attach additional evidence if exploitation was attempted
- Escalate to **CONFIRMED** if reproducible and exploitable
"""
        return reproducibility_md

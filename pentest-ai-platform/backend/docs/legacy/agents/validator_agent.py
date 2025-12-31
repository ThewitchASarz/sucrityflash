"""
ValidatorAgent - Validates findings before report inclusion (V2 requirement).

Per spec: "Findings must be validated by ValidatorAgent before appearing in reports.
Only validated findings appear in final reports."

Responsibilities:
- Review evidence for findings
- Confirm finding is legitimate (not false positive)
- Set validated=True, validator_id, validated_at
- Reject false positives

Run: python -m backend.agents.validator_agent
"""
import asyncio
import sys
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, '/Users/annalealayton/PyCharmMiscProject/pentest-ai-platform/backend')

from database import AsyncSessionLocal
from models.finding import Finding
from models.evidence import Evidence
from models.run import Run


class ValidatorAgent:
    """
    ValidatorAgent: Validates findings to ensure they are legitimate.

    Validation Criteria:
    1. Evidence exists and supports finding
    2. Severity matches evidence
    3. Not a false positive
    4. Meets OWASP criteria (if applicable)
    """

    def __init__(self, agent_id: Optional[uuid.UUID] = None):
        self.agent_id = agent_id or uuid.uuid4()
        self.running = False

    async def start(self):
        """Start ValidatorAgent loop."""
        self.running = True

        print("=" * 70)
        print("🔍 VALIDATOR AGENT - FINDING VALIDATION SERVICE")
        print("=" * 70)
        print(f"Agent ID: {self.agent_id}")
        print("Role: Validate findings before report inclusion")
        print("Criteria: Evidence review, severity check, false positive detection")
        print("=" * 70)
        print()

        while self.running:
            try:
                await self._validation_loop()
            except KeyboardInterrupt:
                print("\n🛑 ValidatorAgent shutting down...")
                self.running = False
            except Exception as e:
                print(f"❌ Error in validation loop: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(5)

    async def _validate_findings_once(self, db: AsyncSession):
        """Run validation once (for testing)."""
        # Find unvalidated findings
        result = await db.execute(
            select(Finding).where(Finding.validated == False)
        )
        unvalidated_findings = result.scalars().all()

        print(f"📋 Found {len(unvalidated_findings)} unvalidated findings")

        for finding in unvalidated_findings:
            try:
                await self._validate_finding(db, finding)
            except Exception as e:
                print(f"   ❌ Error validating finding {finding.id}: {e}")

    async def _validation_loop(self):
        """Main validation loop - validates unvalidated findings."""
        async with AsyncSessionLocal() as db:
            # Find unvalidated findings
            result = await db.execute(
                select(Finding).where(Finding.validated == False)
            )
            unvalidated_findings = result.scalars().all()

            if unvalidated_findings:
                print(f"📋 Found {len(unvalidated_findings)} unvalidated findings")

            for finding in unvalidated_findings:
                try:
                    await self._validate_finding(db, finding)
                except Exception as e:
                    print(f"   ❌ Error validating finding {finding.id}: {e}")

        await asyncio.sleep(10)  # Check every 10 seconds

    async def _validate_finding(self, db: AsyncSession, finding: Finding):
        """
        Validate a single finding.

        Validation Process:
        1. Fetch evidence for finding
        2. Review evidence content
        3. Check severity matches evidence
        4. Detect false positives
        5. Mark as validated if legitimate
        """
        print(f"\n🔍 Validating finding: {finding.id}")
        print(f"   Title: {finding.title}")
        print(f"   Severity: {finding.severity}")

        # Step 1: Fetch evidence
        evidence_list = []
        if finding.evidence_ids:
            for evidence_id_str in finding.evidence_ids:
                try:
                    evidence_uuid = uuid.UUID(evidence_id_str)
                    result = await db.execute(
                        select(Evidence).where(Evidence.id == evidence_uuid)
                    )
                    evidence = result.scalar_one_or_none()
                    if evidence:
                        evidence_list.append(evidence)
                except Exception as e:
                    print(f"   ⚠️  Could not fetch evidence {evidence_id_str}: {e}")

        if not evidence_list:
            print(f"   ⚠️  No evidence found, marking as unvalidated")
            return

        print(f"   ✓ Found {len(evidence_list)} evidence items")

        # Step 2: Validate based on finding type
        is_valid, reason = await self._validate_finding_logic(finding, evidence_list)

        if is_valid:
            # Mark as validated
            finding.validated = True
            finding.validator_id = self.agent_id
            finding.validated_at = datetime.utcnow()
            await db.commit()

            print(f"   ✅ VALIDATED: {reason}")
        else:
            print(f"   ❌ REJECTED: {reason}")

    async def _validate_finding_logic(
        self,
        finding: Finding,
        evidence_list: list[Evidence]
    ) -> tuple[bool, str]:
        """
        Core validation logic.

        Returns: (is_valid, reason)
        """
        # Rule 1: Check if evidence supports the finding
        has_supporting_evidence = any(
            self._evidence_supports_finding(finding, evidence)
            for evidence in evidence_list
        )

        if not has_supporting_evidence:
            return False, "No evidence supports this finding"

        # Rule 2: Severity validation
        severity_valid = self._validate_severity(finding, evidence_list)
        if not severity_valid:
            return False, "Severity does not match evidence"

        # Rule 3: False positive detection
        is_false_positive = self._detect_false_positive(finding, evidence_list)
        if is_false_positive:
            return False, "Detected as false positive"

        # Rule 4: OWASP mapping validation (if applicable)
        if finding.owasp_mappings and len(finding.owasp_mappings) > 0:
            owasp_valid = self._validate_owasp_category(finding)
            if not owasp_valid:
                return False, f"Invalid OWASP mapping: {finding.owasp_mappings[0]}"

        return True, "All validation checks passed"

    def _evidence_supports_finding(self, finding: Finding, evidence: Evidence) -> bool:
        """Check if evidence supports the finding."""
        # Check if evidence contains indicators of the vulnerability

        finding_title_lower = finding.title.lower()
        finding_desc_lower = (finding.description or "").lower()

        # Common vulnerability indicators
        if "sql injection" in finding_title_lower:
            # Look for SQL error messages in evidence
            if evidence.content:
                content_str = str(evidence.content).lower()
                sql_indicators = ["sql syntax", "mysql", "postgresql", "syntax error", "query failed"]
                return any(indicator in content_str for indicator in sql_indicators)

        elif "xss" in finding_title_lower or "cross-site scripting" in finding_title_lower:
            # Look for XSS indicators
            if evidence.content:
                content_str = str(evidence.content).lower()
                xss_indicators = ["<script>", "onerror=", "onload=", "javascript:", "alert("]
                return any(indicator in content_str for indicator in xss_indicators)

        elif "open port" in finding_title_lower:
            # Check if evidence shows open port
            if evidence.content:
                content_str = str(evidence.content)
                return "open" in content_str.lower() or "filtered" in content_str.lower()

        elif "subdomain" in finding_title_lower:
            # Check if evidence contains subdomain info
            if evidence.content:
                return bool(evidence.content)

        # Default: if evidence exists and has content, consider it supporting
        return evidence.content is not None

    def _validate_severity(self, finding: Finding, evidence_list: list[Evidence]) -> bool:
        """Validate severity matches evidence."""
        # Severity mapping rules
        severity = finding.severity

        # Critical: Must have clear exploitation evidence
        if severity == "CRITICAL":
            # Check for exploitation indicators
            for evidence in evidence_list:
                if evidence.content:
                    content_str = str(evidence.content).lower()
                    if any(ind in content_str for ind in ["exploit", "compromised", "shell", "root"]):
                        return True
            # If no exploitation evidence, CRITICAL may be too high
            return False

        # High: Clear vulnerability with known attack vector
        elif severity == "HIGH":
            # Should have vulnerability indicators
            return len(evidence_list) > 0

        # Medium/Low: Information gathering or minor issues
        elif severity in ["MEDIUM", "LOW"]:
            return True

        # Info: Always valid
        elif severity == "INFO":
            return True

        return True

    def _detect_false_positive(self, finding: Finding, evidence_list: list[Evidence]) -> bool:
        """Detect if finding is a false positive."""
        # Common false positive patterns

        # FP1: Findings with no evidence content
        if not any(evidence.content for evidence in evidence_list):
            return True

        # FP2: Generic "port open" findings without actual service
        if "open port" in finding.title.lower():
            for evidence in evidence_list:
                if evidence.content:
                    content_str = str(evidence.content).lower()
                    # If port is closed or filtered, it's FP
                    if "closed" in content_str or ("filtered" in content_str and "open" not in content_str):
                        return True

        # FP3: XSS findings without actual reflection
        if "xss" in finding.title.lower():
            has_reflection = False
            for evidence in evidence_list:
                if evidence.content:
                    content_str = str(evidence.content).lower()
                    if "<script>" in content_str or "alert(" in content_str:
                        has_reflection = True
            if not has_reflection:
                return True

        return False

    def _validate_owasp_category(self, finding: Finding) -> bool:
        """Validate OWASP category."""
        valid_categories = [
            "A01:2021",
            "A02:2021",
            "A03:2021",
            "A04:2021",
            "A05:2021",
            "A06:2021",
            "A07:2021",
            "A08:2021",
            "A09:2021",
            "A10:2021"
        ]

        # Check if first mapping is valid
        if finding.owasp_mappings and len(finding.owasp_mappings) > 0:
            return finding.owasp_mappings[0] in valid_categories

        return False


async def main():
    """Main entry point for ValidatorAgent."""
    agent = ValidatorAgent()
    await agent.start()


if __name__ == "__main__":
    asyncio.run(main())

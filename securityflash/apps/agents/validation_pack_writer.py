"""
Validation Pack writer - produces human-run validation workflows only.
"""
from typing import Dict, Any, List
import logging
from apps.agents.clients.control_plane_client import ControlPlaneClient

logger = logging.getLogger(__name__)


class ValidationPackWriter:
    """
    Generates DRAFT validation packs for risky findings.

    Safety constraints:
    - Never includes exploit payloads
    - Commands are read-only / validation-only
    - Produces stop conditions and evidence requirements
    """

    def __init__(self, api_client: ControlPlaneClient):
        self.api_client = api_client

    def build_pack_payload(
        self,
        run_id: str,
        project_id: str,
        scope_id: str,
        finding: Dict[str, Any],
        evidence: List[Dict[str, Any]],
        created_by: str = "agent"
    ) -> Dict[str, Any]:
        title = f"Validate finding: {finding.get('title', 'Potential issue')}"
        risk_level = "HIGH" if finding.get("severity", "").upper() == "HIGH" else "MED"
        instructions_md = (
            "Follow these steps to validate the finding without exploitation:\n"
            "1. Review the scope and confirm the target host is authorized.\n"
            "2. Run the provided validation commands exactly as written.\n"
            "3. Stop immediately if any unexpected state change is observed."
        )
        command_templates = [
            {
                "label": "Non-destructive HTTP validation",
                "command": "httpx -status-code -location -title -path /",
                "params_schema": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string", "description": "Hostname or URL to validate"}
                    },
                    "required": ["target"]
                },
                "safety_notes": "Do not modify data. Read-only GET requests only."
            }
        ]
        stop_conditions = [
            "Any response indicating state change or data mutation",
            "Service instability, rate limit errors, or 5xx spikes",
            "Unexpected authentication prompts or redirects"
        ]
        required_evidence = [
            "Screenshots or response bodies demonstrating the issue",
            "Command outputs with headers and status codes",
            "Timestamped notes on steps taken"
        ]

        return {
            "title": title,
            "risk_level": risk_level,
            "instructions_md": instructions_md,
            "command_templates": command_templates,
            "stop_conditions": stop_conditions,
            "required_evidence": required_evidence,
            "finding_id": finding.get("id"),
            "created_by": created_by
        }

    def create_draft(
        self,
        run_id: str,
        project_id: str,
        scope_id: str,
        finding: Dict[str, Any],
        evidence: List[Dict[str, Any]],
        created_by: str = "agent"
    ) -> Dict[str, Any]:
        """Create a draft validation pack via the Control Plane API."""
        payload = self.build_pack_payload(run_id, project_id, scope_id, finding, evidence, created_by)
        logger.info("Creating validation pack draft (manual execution only)")
        return self.api_client.create_validation_pack(run_id, payload)

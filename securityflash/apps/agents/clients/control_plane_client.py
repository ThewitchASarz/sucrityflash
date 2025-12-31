"""
Control Plane HTTP client for agents.

Agents use this client to communicate with the Control Plane API.
"""
import requests
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class ControlPlaneClient:
    """HTTP client for Control Plane API."""

    def __init__(self, base_url: str = "http://localhost:8000/api/v1"):
        """
        Initialize Control Plane client.

        Args:
            base_url: Base URL for Control Plane API
        """
        self.base_url = base_url
        self.session = requests.Session()

    def get_run(self, run_id: str) -> Dict[str, Any]:
        """
        Get run details.

        Args:
            run_id: Run ID

        Returns:
            Run dict
        """
        response = self.session.get(f"{self.base_url}/runs/{run_id}")
        response.raise_for_status()
        return response.json()

    def get_scope(self, project_id: str, scope_id: str) -> Dict[str, Any]:
        """
        Get scope details.

        Args:
            project_id: Project ID
            scope_id: Scope ID

        Returns:
            Scope dict with scope_json
        """
        response = self.session.get(
            f"{self.base_url}/projects/{project_id}/scopes/{scope_id}"
        )
        response.raise_for_status()
        return response.json()

    def propose_action(
        self,
        run_id: str,
        tool: str,
        arguments: List[str],
        target: str,
        proposed_by: str,
        justification: str = ""
    ) -> Dict[str, Any]:
        """
        Propose an ActionSpec.

        Args:
            run_id: Run ID
            tool: Tool name (httpx, nmap)
            arguments: Tool arguments
            target: Target (must be in scope)
            proposed_by: Agent ID
            justification: Reason for action

        Returns:
            ActionSpec response with policy evaluation
        """
        payload = {
            "tool": tool,
            "arguments": arguments,
            "target": target,
            "proposed_by": proposed_by,
            "justification": justification
        }

        logger.info(f"Proposing action: {tool} {target}")

        response = self.session.post(
            f"{self.base_url}/runs/{run_id}/action-specs",
            json=payload
        )
        response.raise_for_status()
        return response.json()

    def list_action_specs(
        self,
        run_id: str,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List ActionSpecs for a run.

        Args:
            run_id: Run ID
            status: Optional status filter

        Returns:
            List of ActionSpec dicts
        """
        params = {"status": status} if status else {}
        response = self.session.get(
            f"{self.base_url}/runs/{run_id}/action-specs",
            params=params
        )
        response.raise_for_status()
        return response.json()

    def get_evidence(self, run_id: str) -> List[Dict[str, Any]]:
        """
        Get all evidence for a run.

        Args:
            run_id: Run ID

        Returns:
            List of Evidence dicts
        """
        response = self.session.get(f"{self.base_url}/runs/{run_id}/evidence")
        response.raise_for_status()
        return response.json()

    def get_evidence_by_id(self, run_id: str, evidence_id: str) -> Dict[str, Any]:
        """
        Get specific evidence.

        Args:
            run_id: Run ID
            evidence_id: Evidence ID

        Returns:
            Evidence dict
        """
        response = self.session.get(
            f"{self.base_url}/runs/{run_id}/evidence/{evidence_id}"
        )
        response.raise_for_status()
        return response.json()

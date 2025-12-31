"""
SecurityFlash V1 HTTP Client

This client provides the ONLY interface between V2 (orchestration/UI) and V1 (execution authority).

V2 MUST NEVER:
- Execute tools via subprocess
- Bypass approvals
- Store evidence directly
- Manage policy logic

All of the above lives in SecurityFlash V1.
"""
import httpx
import os
from typing import Dict, List, Optional, Any
from datetime import datetime


class SecurityFlashClient:
    """
    HTTP client for SecurityFlash V1 Control Plane.
    
    V2 uses this client to:
    - Submit action specs for approval
    - Query run status
    - Retrieve evidence
    - Get findings
    
    V1 handles:
    - Policy enforcement
    - Approval workflows
    - Tool execution
    - Evidence storage
    """
    
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize SecurityFlash client.
        
        Args:
            base_url: SecurityFlash Control Plane URL (default: env SECURITYFLASH_API_URL)
            api_key: JWT token for authentication (default: env SECURITYFLASH_API_KEY)
        """
        self.base_url = base_url or os.getenv("SECURITYFLASH_API_URL")
        if not self.base_url:
            raise ValueError(
                "SECURITYFLASH_API_URL must be set. V2 cannot operate without V1."
            )
        
        self.api_key = api_key or os.getenv("SECURITYFLASH_API_KEY")
        if not self.api_key:
            raise ValueError(
                "SECURITYFLASH_API_KEY must be set for authentication with V1."
            )
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        self.timeout = 30.0
    
    async def create_project(self, name: str, description: str) -> Dict[str, Any]:
        """Create project in SecurityFlash V1."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/projects",
                json={"name": name, "description": description},
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
    
    async def create_scope(
        self,
        project_id: str,
        target_systems: List[str],
        excluded_systems: List[str],
        forbidden_methods: List[str],
        roe: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create scope in SecurityFlash V1 (requires dual signature)."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/scopes",
                json={
                    "project_id": project_id,
                    "target_systems": target_systems,
                    "excluded_systems": excluded_systems,
                    "forbidden_methods": forbidden_methods,
                    "roe": roe
                },
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
    
    async def submit_action_spec(
        self,
        run_id: str,
        method: str,
        args: Dict[str, Any],
        risk_level: str
    ) -> Dict[str, Any]:
        """
        Submit action spec to SecurityFlash V1 for approval/execution.
        
        V1 will:
        - Validate against policy
        - Require approval if L2/L3
        - Execute via Worker Runtime
        - Store evidence
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/action-specs",
                json={
                    "run_id": run_id,
                    "method": method,
                    "args": args,
                    "risk_level": risk_level
                },
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
    
    async def get_run_status(self, run_id: str) -> Dict[str, Any]:
        """Get run status from SecurityFlash V1."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/runs/{run_id}",
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
    
    async def get_evidence(self, run_id: str) -> List[Dict[str, Any]]:
        """
        Get evidence from SecurityFlash V1.
        
        Evidence is IMMUTABLE and stored in V1 only.
        V2 can query but never modify.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/evidence",
                params={"run_id": run_id},
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
    
    async def approve_action(
        self,
        approval_id: str,
        approved_by: str,
        signature: str
    ) -> Dict[str, Any]:
        """
        Approve action in SecurityFlash V1.
        
        V1 validates:
        - Digital signature
        - User permissions
        - Policy compliance
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/approvals/{approval_id}/approve",
                json={
                    "approved_by": approved_by,
                    "signature": signature
                },
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
    
    async def get_findings(self, run_id: str) -> List[Dict[str, Any]]:
        """Get findings from SecurityFlash V1."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/findings",
                params={"run_id": run_id},
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if SecurityFlash V1 is healthy."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/health",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()


# Singleton instance
_client: Optional[SecurityFlashClient] = None


def get_securityflash_client() -> SecurityFlashClient:
    """
    Get SecurityFlash client singleton.
    
    Usage:
        client = get_securityflash_client()
        status = await client.get_run_status(run_id)
    """
    global _client
    if _client is None:
        _client = SecurityFlashClient()
    return _client

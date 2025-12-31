"""
V2 Orchestrator

Coordinates with SecurityFlash V1 for action execution.
DOES NOT execute tools directly - delegates all execution to V1.
"""
import asyncio
from typing import Dict, Any, List
from clients.securityflash_client import get_securityflash_client


class V2Orchestrator:
    """
    Orchestration layer for V2.
    
    Responsibilities:
    - Submit action specs to SecurityFlash V1
    - Monitor run progress
    - Retrieve results/evidence
    - Coordinate UI updates
    
    NOT responsible for:
    - Tool execution (V1 Worker Runtime)
    - Policy enforcement (V1 Policy Engine)
    - Evidence storage (V1 Evidence Service)
    - Approvals (V1 Approval Manager)
    """
    
    def __init__(self):
        self.client = get_securityflash_client()
    
    async def submit_action(
        self,
        run_id: str,
        method: str,
        args: Dict[str, Any],
        risk_level: str
    ) -> Dict[str, Any]:
        """
        Submit action to SecurityFlash V1 for execution.
        
        V1 will handle:
        - Policy validation
        - Approval workflow (if L2/L3)
        - Tool execution via Worker Runtime
        - Evidence storage
        
        Returns:
            Action spec with status
        """
        return await self.client.submit_action_spec(
            run_id=run_id,
            method=method,
            args=args,
            risk_level=risk_level
        )
    
    async def monitor_run(self, run_id: str) -> Dict[str, Any]:
        """
        Monitor run status in SecurityFlash V1.
        
        Returns:
            Run status with execution progress
        """
        return await self.client.get_run_status(run_id)
    
    async def get_results(self, run_id: str) -> Dict[str, Any]:
        """
        Retrieve results from SecurityFlash V1.
        
        Returns:
            Evidence and findings from V1
        """
        evidence = await self.client.get_evidence(run_id)
        findings = await self.client.get_findings(run_id)
        
        return {
            "evidence": evidence,
            "findings": findings
        }
    
    async def wait_for_completion(
        self,
        run_id: str,
        poll_interval: float = 5.0,
        timeout: float = 3600.0
    ) -> Dict[str, Any]:
        """
        Wait for run to complete in SecurityFlash V1.
        
        Args:
            run_id: Run ID to monitor
            poll_interval: Seconds between status checks
            timeout: Maximum time to wait
        
        Returns:
            Final run status
        """
        elapsed = 0.0
        while elapsed < timeout:
            status = await self.monitor_run(run_id)
            
            if status.get("status") in ["completed", "failed", "cancelled"]:
                return status
            
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
        
        raise TimeoutError(f"Run {run_id} did not complete within {timeout}s")


# Singleton instance
_orchestrator = None


def get_orchestrator() -> V2Orchestrator:
    """Get V2 orchestrator singleton."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = V2Orchestrator()
    return _orchestrator

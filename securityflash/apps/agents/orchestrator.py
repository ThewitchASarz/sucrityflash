"""
OrchestratorAgent - V1 minimal implementation.

CRITICAL: This is a simple, deterministic agent for V1.
Proposes SAFE recon actions in sequence:
1. httpx probe (if URL target)
2. subfinder (if domain target)
3. dnsx resolve
4. nmap safe scan

No LLM reasoning in V1 (deterministic workflow).

V2+ will add:
- LLM-based planning
- Multi-step reasoning
- Evidence interpretation
- Dynamic tool selection
"""
from typing import List, Dict, Any
import logging
import re
from urllib.parse import urlparse
from apps.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """
    V1 Orchestrator Agent.

    Deterministic recon workflow:
    1. Read targets from locked scope
    2. For each target, determine type (URL, domain, IP)
    3. Propose safe recon actions in sequence:
       - httpx probe (if URL)
       - subfinder (if domain)
       - nmap safe scan
    4. Wait for evidence before next step
    5. Done when all targets processed

    No LLM reasoning in V1 (deterministic plan).
    """

    def __init__(self, *args, **kwargs):
        """Initialize OrchestratorAgent."""
        super().__init__(*args, **kwargs)

        # Initialize target queue and workflow state
        if "target_queue" in self.memory:
            self.target_queue: List[Dict[str, Any]] = self.memory["target_queue"]
            self.processed_targets: List[str] = self.memory.get("processed_targets", [])
            self.current_phase: str = self.memory.get("current_phase", "init")
            logger.info(f"Restored queue: {len(self.target_queue)} targets remaining")
        else:
            # First run: populate queue with workflow phases
            self.target_queue = self._build_recon_plan()
            self.processed_targets = []
            self.current_phase = "init"
            logger.info(f"Initialized plan: {len(self.target_queue)} actions")

        # Save to memory
        self.memory["target_queue"] = self.target_queue
        self.memory["processed_targets"] = self.processed_targets
        self.memory["current_phase"] = self.current_phase

    def _build_recon_plan(self) -> List[Dict[str, Any]]:
        """
        Build deterministic recon plan from scope targets.

        Returns list of planned actions in order.
        """
        plan = []
        targets = self.scope.get("targets", [])

        logger.info(f"Building recon plan for {len(targets)} targets")

        for target in targets:
            target_value = target["value"]
            target_type = self._classify_target(target_value)

            logger.info(f"Target {target_value} classified as {target_type}")

            # Add actions based on target type
            if target_type == "url":
                # HTTP probe first
                plan.append({
                    "action": "httpx",
                    "target": target_value,
                    "justification": f"HTTP reconnaissance of {target_value}",
                    "arguments": {}
                })

                # Then nmap on extracted host
                parsed = urlparse(target_value)
                host = parsed.netloc or parsed.path
                if host:
                    plan.append({
                        "action": "nmap",
                        "target": host,
                        "justification": f"Port scan of {host} (extracted from {target_value})",
                        "arguments": {}
                    })
                    plan.append({
                        "action": "neurosploit",
                        "target": host,
                        "justification": f"NeuroSploit recon module against {host}",
                        "arguments": {
                            "module": "recon/portscan",
                            "options": [host]
                        }
                    })

            elif target_type == "domain":
                # Subdomain enumeration first
                plan.append({
                    "action": "subfinder",
                    "target": target_value,
                    "justification": f"Subdomain enumeration for {target_value}",
                    "arguments": {"domain": target_value}
                })

                # Then nmap on main domain
                plan.append({
                    "action": "nmap",
                    "target": target_value,
                    "justification": f"Port scan of {target_value}",
                    "arguments": {}
                })
                plan.append({
                    "action": "neurosploit",
                    "target": target_value,
                    "justification": f"NeuroSploit recon module against {target_value}",
                    "arguments": {
                        "module": "recon/portscan",
                        "options": [target_value]
                    }
                })

            elif target_type == "ip":
                # Direct nmap scan
                plan.append({
                    "action": "nmap",
                    "target": target_value,
                    "justification": f"Port scan of {target_value}",
                    "arguments": {}
                })
                plan.append({
                    "action": "neurosploit",
                    "target": target_value,
                    "justification": f"NeuroSploit recon module against {target_value}",
                    "arguments": {
                        "module": "recon/portscan",
                        "options": [target_value]
                    }
                })

        logger.info(f"Recon plan built: {len(plan)} actions")
        return plan

    def _classify_target(self, target: str) -> str:
        """
        Classify target as URL, domain, or IP.

        Args:
            target: Target string

        Returns:
            "url", "domain", or "ip"
        """
        # Check if it's a URL (has scheme)
        if target.startswith("http://") or target.startswith("https://"):
            return "url"

        # Check if it's an IP address
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if re.match(ip_pattern, target):
            return "ip"

        # Otherwise assume it's a domain
        return "domain"

    def step(self) -> bool:
        """
        Execute one iteration of the recon plan.

        V1 logic:
        1. Pop next action from plan
        2. Propose action via API (goes through Policy Engine)
        3. Wait for approval and execution
        4. Record evidence
        5. Continue to next action

        Returns:
            True to continue, False if done
        """
        # Check if plan is complete
        if not self.target_queue:
            logger.info("Recon plan complete. Agent finished.")
            return False

        # Get next action from plan
        planned_action = self.target_queue.pop(0)
        tool = planned_action["action"]
        target = planned_action["target"]
        justification = planned_action["justification"]
        arguments = planned_action.get("arguments", {})

        logger.info(f"Executing: {tool} on {target}")

        try:
            # Propose action (goes through Policy Engine)
            action_response = self.propose_action(
                tool=tool,
                arguments=arguments,
                target=target,
                justification=justification
            )

            action_id = action_response["id"]
            status = action_response["status"]
            risk_score = action_response.get("risk_score")
            approval_tier = action_response.get("approval_tier")

            logger.info(
                f"Action proposed: {action_id[:8]}... "
                f"(status={status}, risk={risk_score:.2f}, tier={approval_tier})"
            )

            # Check action status
            if status == "APPROVED":
                logger.info("Action auto-approved (Tier A - safe recon)")
            elif status == "PENDING_APPROVAL":
                logger.info("Action requires human approval (Tier B). Waiting...")
                # In V1, we continue to next action without blocking
                # Worker will execute when approved
            elif status == "REJECTED":
                logger.warning(f"Action rejected by policy: {action_response.get('policy_check_result', {})}")
                # Mark as processed and continue
                self.processed_targets.append(f"{tool}:{target}")
                self.memory["target_queue"] = self.target_queue
                self.memory["processed_targets"] = self.processed_targets
                return True

            # Wait for evidence (worker executes approved actions)
            logger.info("Waiting for evidence from worker...")
            evidence = self.wait_for_evidence(action_id, timeout_sec=180)

            if evidence:
                logger.info(f"Evidence received: {evidence['id']}")
                evidence_size = len(evidence.get('metadata', {}).get('stdout', ''))
                logger.info(f"Tool output: {evidence_size} bytes")

                # V1: No evidence interpretation (no LLM)
                # Just mark as processed
                self.processed_targets.append(f"{tool}:{target}")
            else:
                logger.warning(f"Evidence not received within timeout for {tool} on {target}")
                # Don't retry in V1 - just mark as failed and continue
                self.processed_targets.append(f"{tool}:{target}:timeout")

        except Exception as e:
            logger.error(f"Error executing {tool} on {target}: {e}", exc_info=True)
            # Don't retry - just mark as failed and continue
            self.processed_targets.append(f"{tool}:{target}:error")

        # Update memory
        self.memory["target_queue"] = self.target_queue
        self.memory["processed_targets"] = self.processed_targets
        self.memory["current_phase"] = "executing"

        # Continue if more actions in plan
        return len(self.target_queue) > 0


class SimpleHttpAgent(BaseAgent):
    """
    Alternative V1 agent: HTTP probing.

    Simple logic:
    1. For each target, probe with httpx
    2. Record evidence
    3. Done

    No LLM reasoning.
    """

    def __init__(self, *args, **kwargs):
        """Initialize SimpleHttpAgent."""
        super().__init__(*args, **kwargs)

        if "target_queue" in self.memory:
            self.target_queue: List[Dict[str, Any]] = self.memory["target_queue"]
            self.probed_targets: List[str] = self.memory.get("probed_targets", [])
        else:
            self.target_queue = self.scope.get("targets", []).copy()
            self.probed_targets = []

        self.memory["target_queue"] = self.target_queue
        self.memory["probed_targets"] = self.probed_targets

    def step(self) -> bool:
        """
        Execute one iteration.

        Returns:
            True to continue, False if done
        """
        if not self.target_queue:
            logger.info("All targets probed. Agent complete.")
            return False

        target = self.target_queue.pop(0)
        target_value = target["value"]

        logger.info(f"Probing target: {target_value}")

        try:
            # Propose httpx GET request
            action_response = self.propose_action(
                tool="httpx",
                arguments=["-m", "GET"],
                target=f"https://{target_value}",
                justification=f"HTTP probe of {target_value}"
            )

            action_id = action_response["id"]
            status = action_response["status"]

            logger.info(f"Action proposed: {action_id[:8]}... (status={status})")

            if status == "REJECTED":
                logger.warning("Action rejected")
                self.probed_targets.append(target_value)
                self.memory["target_queue"] = self.target_queue
                self.memory["probed_targets"] = self.probed_targets
                return True

            # Wait for evidence
            evidence = self.wait_for_evidence(action_id, timeout_sec=60)

            if evidence:
                logger.info(f"Evidence received: HTTP response captured")
                self.probed_targets.append(target_value)
            else:
                logger.warning("Evidence not received")
                self.target_queue.append(target)

        except Exception as e:
            logger.error(f"Error probing {target_value}: {e}")
            self.target_queue.append(target)

        self.memory["target_queue"] = self.target_queue
        self.memory["probed_targets"] = self.probed_targets

        return len(self.target_queue) > 0

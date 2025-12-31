"""
OrchestratorAgent - V1 minimal implementation.

CRITICAL: This is a simple, deterministic agent for V1.
No LLM reasoning. Just proposes nmap scans for each target.

V2+ will add:
- LLM-based planning
- Multi-step reasoning
- Evidence interpretation
- Dynamic tool selection
"""
from typing import List, Dict, Any
import logging
from apps.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """
    V1 Orchestrator Agent.

    Simple logic:
    1. Read targets from scope
    2. For each target, propose nmap scan
    3. Wait for evidence
    4. Move to next target
    5. Done when all targets scanned

    No LLM reasoning in V1 (deterministic).
    """

    def __init__(self, *args, **kwargs):
        """Initialize OrchestratorAgent."""
        super().__init__(*args, **kwargs)

        # Initialize target queue from memory or scope
        if "target_queue" in self.memory:
            self.target_queue: List[Dict[str, Any]] = self.memory["target_queue"]
            self.scanned_targets: List[str] = self.memory.get("scanned_targets", [])
            logger.info(f"Restored queue: {len(self.target_queue)} targets remaining")
        else:
            # First run: populate queue
            self.target_queue = self.scope.get("targets", []).copy()
            self.scanned_targets = []
            logger.info(f"Initialized queue: {len(self.target_queue)} targets")

        # Save to memory
        self.memory["target_queue"] = self.target_queue
        self.memory["scanned_targets"] = self.scanned_targets

    def step(self) -> bool:
        """
        Execute one iteration.

        V1 logic:
        1. Pop next target from queue
        2. Propose nmap scan
        3. Wait for approval and execution
        4. Record evidence
        5. Continue or done

        Returns:
            True to continue, False if done
        """
        # Check if queue is empty
        if not self.target_queue:
            logger.info("All targets scanned. Agent complete.")
            return False

        # Get next target
        target = self.target_queue.pop(0)
        target_value = target["value"]

        logger.info(f"Processing target: {target_value} (criticality: {target.get('criticality', 'MEDIUM')})")

        # Propose nmap scan
        justification = f"Initial reconnaissance scan of {target_value} (criticality: {target.get('criticality')})"

        try:
            action_response = self.propose_action(
                tool="nmap",
                arguments=["-sV", "-Pn", "-p", "1-1000"],  # Scan common ports
                target=target_value,
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

            # Check if auto-approved or needs review
            if status == "APPROVED":
                logger.info("Action auto-approved (low risk)")
            elif status == "PENDING_APPROVAL":
                logger.info("Action requires human approval. Waiting...")
            elif status == "REJECTED":
                logger.warning(f"Action rejected: {action_response.get('policy_check_result', {}).get('reason')}")
                # Continue to next target
                self.scanned_targets.append(target_value)
                self.memory["target_queue"] = self.target_queue
                self.memory["scanned_targets"] = self.scanned_targets
                return True

            # Wait for evidence (worker will execute after approval)
            logger.info("Waiting for evidence...")
            evidence = self.wait_for_evidence(action_id, timeout_sec=180)

            if evidence:
                logger.info(f"Evidence received: {evidence['id']}")
                logger.info(f"Tool output: {len(evidence['metadata'].get('stdout', ''))} bytes")

                # V1: We don't interpret evidence (no LLM)
                # Just record that target was scanned
                self.scanned_targets.append(target_value)
            else:
                logger.warning(f"Evidence not received within timeout for {target_value}")
                # Re-add target to queue for retry
                self.target_queue.append(target)

        except Exception as e:
            logger.error(f"Error processing target {target_value}: {e}")
            # Re-add target to queue for retry
            self.target_queue.append(target)

        # Update memory
        self.memory["target_queue"] = self.target_queue
        self.memory["scanned_targets"] = self.scanned_targets

        # Continue if more targets
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

"""
BaseAgent - Abstract base class for all agents.

CRITICAL: Agents NEVER execute tools directly.
Agents propose ActionSpecs, which are gated by Policy Engine,
approved by humans, and executed by Workers.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import logging
import time
from apps.agents.clients.control_plane_client import ControlPlaneClient
from apps.agents.clients.db_client import DBClient
from apps.agents.model_router import ModelRouter, Role
from apps.api.core.config import settings

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Abstract base class for agents.

    Responsibilities:
    - Propose ActionSpecs (via Control Plane API)
    - Query LLM for reasoning (with audit logging)
    - Checkpoint state every N iterations
    - Respect scope boundaries
    - NEVER execute tools directly

    Subclasses must implement:
    - step() - Single iteration logic
    """

    def __init__(
        self,
        run_id: str,
        agent_id: str,
        api_base_url: Optional[str] = None,
        max_iterations: int = None,
        checkpoint_interval: int = 5
    ):
        """
        Initialize BaseAgent.

        Args:
            run_id: Run ID
            agent_id: Unique agent identifier
            api_base_url: Control Plane API base URL
            max_iterations: Max iterations (defaults to run.max_iterations)
            checkpoint_interval: Checkpoint every N iterations
        """
        self.run_id = run_id
        self.agent_id = agent_id
        self.iteration = 0
        self.checkpoint_interval = checkpoint_interval

        # Initialize clients
        resolved_api_base = api_base_url or settings.CONTROL_PLANE_API_URL or f"http://localhost:{settings.PORT}/api/v1"
        self.api_client = ControlPlaneClient(resolved_api_base)
        self.db_client = DBClient()
        self.model_router = ModelRouter(
            db_client=self.db_client,
            run_id=self.run_id,
            agent_id=self.agent_id,
            policy_version=None  # will be set after run data load
        )

        # Load run and scope
        logger.info(f"Initializing agent {agent_id} for run {run_id}")
        self.run_data = self.api_client.get_run(run_id)

        # Get scope
        scope_response = self.api_client.get_scope(
            project_id=str(self.run_data["project_id"]),
            scope_id=str(self.run_data["scope_id"])
        )
        self.scope = scope_response["scope_json"]
        self.policy_version = self.run_data["policy_version"]
        self.model_router.policy_version = self.policy_version

        # Max iterations
        self.max_iterations = max_iterations or self.run_data.get("max_iterations", 100)

        # Agent memory (subclass-specific state)
        self.memory: Dict[str, Any] = {}

        # Try to restore from checkpoint
        self._restore_checkpoint()

        logger.info(f"Agent initialized (scope: {len(self.scope.get('targets', []))} targets)")

    def run(self):
        """
        Main agent loop.

        MUST-FIX A: Agent checks run.status before acting.
        Only proceeds if run.status == RUNNING.
        """
        logger.info(f"Agent {self.agent_id} starting execution")

        # MUST-FIX A: Check run status
        self.run_data = self.api_client.get_run(self.run_id)
        if self.run_data["status"] != "RUNNING":
            logger.warning(f"Run status is {self.run_data['status']}, not RUNNING. Waiting...")
            self._wait_for_running_status()

        logger.info(f"Run status: RUNNING. Beginning agent execution.")

        # Main loop
        while self.iteration < self.max_iterations:
            try:
                logger.info(f"Iteration {self.iteration + 1}/{self.max_iterations}")

                # Execute one step
                should_continue = self.step()

                self.iteration += 1

                # Checkpoint periodically
                if self.iteration % self.checkpoint_interval == 0:
                    self.checkpoint()

                # Check if agent is done
                if not should_continue:
                    logger.info("Agent completed successfully")
                    self.checkpoint(state="completed")
                    break

                # Brief sleep between iterations
                time.sleep(1)

            except KeyboardInterrupt:
                logger.info("Agent interrupted by user")
                self.checkpoint(state="paused")
                break

            except Exception as e:
                logger.error(f"Agent error: {e}", exc_info=True)
                self.checkpoint(state="failed")
                raise

        if self.iteration >= self.max_iterations:
            logger.warning(f"Agent reached max iterations ({self.max_iterations})")
            self.checkpoint(state="completed")

        logger.info(f"Agent execution finished (iterations: {self.iteration})")

    def _wait_for_running_status(self, timeout_sec: int = 300, poll_interval: int = 5):
        """
        Wait for run to transition to RUNNING status.

        MUST-FIX A: Agents must not act until run is started.

        Args:
            timeout_sec: Max time to wait
            poll_interval: Polling interval in seconds
        """
        start_time = time.time()

        while time.time() - start_time < timeout_sec:
            self.run_data = self.api_client.get_run(self.run_id)

            if self.run_data["status"] == "RUNNING":
                logger.info("Run is now RUNNING")
                return

            logger.info(f"Run status: {self.run_data['status']}, waiting...")
            time.sleep(poll_interval)

        raise TimeoutError(f"Run did not start within {timeout_sec}s")

    @abstractmethod
    def step(self) -> bool:
        """
        Execute one iteration step.

        Subclasses implement their logic here.

        Returns:
            True to continue, False to stop
        """
        pass

    def propose_action(
        self,
        tool: str,
        arguments: Any,
        target: str,
        justification: str = ""
    ) -> Dict[str, Any]:
        """
        Propose an ActionSpec.

        This goes through Policy Engine evaluation.

        Args:
            tool: Tool name (httpx, nmap)
            arguments: Tool arguments
            target: Target (must be in scope)
            justification: Reason for action

        Returns:
            ActionSpec response with policy evaluation results
        """
        # Validate target is in scope
        if not self.is_in_scope(target):
            logger.error(f"Target {target} is not in scope")
            raise ValueError(f"Target {target} is not in scope")

        logger.info(f"Proposing action: {tool} {target}")

        return self.api_client.propose_action(
            run_id=self.run_id,
            tool=tool,
            arguments=arguments,
            target=target,
            proposed_by=self.agent_id,
            justification=justification
        )

    def query_llm(
        self,
        prompt: str,
        system_message: str = "You are a security testing assistant.",
        model: str = "gpt-4"
    ) -> str:
        """
        Query LLM with audit logging.

        Args:
            prompt: User prompt
            system_message: System message
            model: Model name

        Returns:
            LLM response text
        """
        return self.model_router.invoke(
            prompt=prompt,
            system_message=system_message,
            role=Role.VALIDATOR
        )

    def is_in_scope(self, target: str) -> bool:
        """
        Check if target is in approved scope.

        Args:
            target: Target to check

        Returns:
            True if in scope
        """
        allowed_targets = [t["value"] for t in self.scope.get("targets", [])]
        excluded_targets = [t["value"] for t in self.scope.get("excluded_targets", [])]

        # Check excluded first
        if target in excluded_targets:
            return False

        # Check if target matches any allowed target (exact or subdomain)
        for allowed in allowed_targets:
            if target == allowed or target.endswith(f".{allowed}"):
                return True

        return False

    def checkpoint(self, state: str = "running"):
        """
        Save agent state to database.

        Args:
            state: Agent state (running, paused, completed, failed)
        """
        try:
            self.db_client.save_checkpoint(
                run_id=self.run_id,
                agent_id=self.agent_id,
                iteration=self.iteration,
                state=state,
                memory=self.memory
            )
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    def _restore_checkpoint(self):
        """Restore agent state from checkpoint if exists."""
        try:
            checkpoint = self.db_client.load_checkpoint(
                run_id=self.run_id,
                agent_id=self.agent_id
            )

            if checkpoint:
                self.iteration = checkpoint["iteration"]
                self.memory = checkpoint["memory"]
                logger.info(f"Restored checkpoint: iteration {self.iteration}")
            else:
                logger.info("No checkpoint found, starting fresh")

        except Exception as e:
            logger.warning(f"Failed to restore checkpoint: {e}")

    def wait_for_evidence(
        self,
        action_id: str,
        timeout_sec: int = 120,
        poll_interval: int = 5
    ) -> Optional[Dict[str, Any]]:
        """
        Wait for evidence to be generated for an action.

        Args:
            action_id: ActionSpec ID
            timeout_sec: Max time to wait
            poll_interval: Polling interval

        Returns:
            Evidence dict or None if timeout
        """
        start_time = time.time()

        while time.time() - start_time < timeout_sec:
            # Get all evidence for run
            evidence_list = self.api_client.get_evidence(self.run_id)

            # Find evidence matching this action
            # (In production, evidence would have action_id reference)
            # For V1, we assume evidence appears in chronological order
            if evidence_list:
                # Return most recent evidence
                return evidence_list[-1]

            logger.debug(f"Waiting for evidence (action {action_id[:8]}...)")
            time.sleep(poll_interval)

        logger.warning(f"Evidence not found within {timeout_sec}s")
        return None

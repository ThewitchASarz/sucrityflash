"""
Worker Main Loop - Executes approved actions.

CRITICAL: This worker is responsible for:
1. Polling for APPROVED ActionSpecs
2. Executing tools via tool_registry runners
3. Storing stdout/stderr as Evidence artifacts
4. Updating action status via API

V1 Implementation:
- Simple polling loop
- Uses RunnerFactory to get tool runners
- Enforces timeouts and output caps from tool_registry
- Graceful shutdown on SIGTERM
"""
import logging
import time
import signal
import sys
import json
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from apps.api.db.session import SessionLocal
from apps.api.models.action_spec import ActionSpec, ActionStatus
from apps.api.models.run import Run, RunStatus
from apps.api.models.evidence import Evidence
from apps.api.services.audit_service import audit_log
from apps.workers.tool_registry import TOOL_REGISTRY
from apps.workers.runners.runner_factory import RunnerFactory
from apps.api.core.config import settings
import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Worker:
    """
    Worker for executing approved actions.

    Polls DB for APPROVED ActionSpecs and executes them using tool runners.
    """

    def __init__(
        self,
        poll_interval_sec: int = 5,
        api_base_url: Optional[str] = None
    ):
        """
        Initialize Worker.

        Args:
            poll_interval_sec: Polling interval in seconds
            api_base_url: Control Plane API base URL
        """
        self.poll_interval_sec = poll_interval_sec
        self.api_base_url = api_base_url or f"http://localhost:{settings.PORT}/api/v1"
        self.running = True

        # Handle graceful shutdown
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

        logger.info("Worker initialized")
        logger.info(f"Poll interval: {poll_interval_sec}s")
        logger.info(f"API base URL: {self.api_base_url}")
        logger.info(f"Supported tools: {RunnerFactory.get_supported_tools()}")

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signal."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
        sys.exit(0)

    def start(self):
        """
        Start worker main loop.

        Polls DB for APPROVED actions and executes them.
        """
        logger.info("Worker starting main loop")

        while self.running:
            try:
                self._poll_and_execute()
                time.sleep(self.poll_interval_sec)

            except KeyboardInterrupt:
                logger.info("Worker interrupted by user")
                break

            except Exception as e:
                logger.error(f"Error in worker loop: {e}", exc_info=True)
                time.sleep(self.poll_interval_sec)

        logger.info("Worker stopped")

    def _poll_and_execute(self):
        """
        Poll DB for approved actions and execute them.

        Logic:
        1. Query for ActionSpecs where status=APPROVED and run.status=RUNNING
        2. For each action:
           a. Update status to EXECUTING
           b. Execute using tool runner
           c. Store evidence (stdout/stderr/artifacts)
           d. Update status to EXECUTED or FAILED
        """
        db: Session = SessionLocal()

        try:
            # Query for approved actions in running runs
            approved_actions = db.query(ActionSpec).join(Run).filter(
                ActionSpec.status == ActionStatus.APPROVED,
                Run.status == RunStatus.RUNNING
            ).limit(10).all()  # Process up to 10 actions per poll

            if not approved_actions:
                logger.debug("No approved actions to execute")
                return

            logger.info(f"Found {len(approved_actions)} approved actions to execute")

            for action_spec in approved_actions:
                try:
                    self._execute_action(db, action_spec)
                except Exception as e:
                    logger.error(f"Failed to execute action {action_spec.id}: {e}", exc_info=True)

        finally:
            db.close()

    def _execute_action(self, db: Session, action_spec: ActionSpec):
        """
        Execute a single action.

        Args:
            db: Database session
            action_spec: ActionSpec to execute
        """
        action_id = str(action_spec.id)
        tool = action_spec.action_json.get("tool")
        target = action_spec.action_json.get("target")

        logger.info(f"Executing action {action_id[:8]}...: {tool} on {target}")

        # Check if tool is supported
        if not RunnerFactory.is_tool_supported(tool):
            logger.error(f"Tool {tool} not supported by worker")
            self._update_action_status(
                action_id=action_id,
                status="FAILED",
                reason=f"Tool {tool} not supported by worker"
            )
            return

        # Update status to EXECUTING
        action_spec.status = ActionStatus.EXECUTING
        db.commit()

        # Emit timeline event
        audit_log(
            db=db,
            run_id=action_spec.run_id,
            event_type="EXECUTION_STARTED",
            actor="worker",
            details={
                "action_id": action_id,
                "tool": tool,
                "target": target
            }
        )

        try:
            # Get runner for tool
            runner = RunnerFactory.get_runner(tool)
            if not runner:
                raise Exception(f"Failed to create runner for tool {tool}")

            # Execute tool
            logger.info(f"Running {tool} runner...")
            start_time = time.time()
            result = runner.run(action_spec.action_json)
            execution_time = time.time() - start_time

            logger.info(
                f"Execution completed: success={result.success}, "
                f"exit_code={result.exit_code}, "
                f"time={execution_time:.2f}s"
            )

            # Store evidence
            evidence = self._store_evidence(db, action_spec, result)

            # Update action status
            if result.success:
                action_spec.status = ActionStatus.EXECUTED

                # Update via API to trigger timeline event
                self._update_action_status(
                    action_id=action_id,
                    status="EXECUTED",
                    evidence_id=str(evidence.id) if evidence else None,
                    metadata={
                        "execution_time_sec": execution_time,
                        "exit_code": result.exit_code,
                        "artifacts_count": len(result.artifacts)
                    }
                )
            else:
                action_spec.status = ActionStatus.FAILED

                # Update via API to trigger timeline event
                self._update_action_status(
                    action_id=action_id,
                    status="FAILED",
                    reason=result.error_message or result.stderr,
                    metadata={
                        "execution_time_sec": execution_time,
                        "exit_code": result.exit_code
                    }
                )

            db.commit()

            logger.info(f"Action {action_id[:8]}... completed: {action_spec.status.value}")

        except Exception as e:
            logger.error(f"Execution failed for action {action_id}: {e}", exc_info=True)

            # Mark as FAILED
            action_spec.status = ActionStatus.FAILED
            db.commit()

            # Update via API to trigger timeline event
            self._update_action_status(
                action_id=action_id,
                status="FAILED",
                reason=str(e)
            )

    def _store_evidence(
        self,
        db: Session,
        action_spec: ActionSpec,
        result
    ) -> Optional[Evidence]:
        """
        Store tool execution results as Evidence.

        Args:
            db: Database session
            action_spec: ActionSpec that was executed
            result: ToolResult from runner

        Returns:
            Evidence instance or None
        """
        try:
            tool = action_spec.action_json.get("tool")
            target = action_spec.action_json.get("target")

            # Build evidence metadata
            metadata = {
                "tool": tool,
                "target": target,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.exit_code,
                "execution_time_sec": result.execution_time_sec,
                "artifacts": result.artifacts
            }

            # Create Evidence record
            evidence = Evidence(
                run_id=action_spec.run_id,
                action_id=action_spec.id,
                evidence_type=f"{tool}_output",
                metadata=metadata,
                collected_by="worker",
                source_url=target
            )

            db.add(evidence)
            db.commit()
            db.refresh(evidence)

            logger.info(f"Evidence stored: {evidence.id}")

            # Emit timeline event
            audit_log(
                db=db,
                run_id=action_spec.run_id,
                event_type="EVIDENCE_ADDED",
                actor="worker",
                details={
                    "evidence_id": str(evidence.id),
                    "action_id": str(action_spec.id),
                    "tool": tool,
                    "target": target,
                    "artifacts_count": len(result.artifacts)
                }
            )

            return evidence

        except Exception as e:
            logger.error(f"Failed to store evidence: {e}", exc_info=True)
            return None

    def _update_action_status(
        self,
        action_id: str,
        status: str,
        reason: Optional[str] = None,
        evidence_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Update action status via API.

        This triggers timeline events and state validation.

        Args:
            action_id: ActionSpec ID
            status: New status (EXECUTING, EXECUTED, FAILED)
            reason: Optional failure reason
            evidence_id: Optional evidence ID
            metadata: Optional metadata dict
        """
        try:
            url = f"{self.api_base_url}/action-specs/{action_id}/status"

            payload = {
                "status": status,
                "reason": reason,
                "evidence_id": evidence_id,
                "metadata": metadata
            }

            response = requests.patch(url, json=payload, timeout=10)
            response.raise_for_status()

            logger.info(f"Action status updated via API: {action_id[:8]}... -> {status}")

        except Exception as e:
            logger.error(f"Failed to update action status via API: {e}")


def main():
    """Main entry point for worker."""
    logger.info("Starting Worker")

    worker = Worker(
        poll_interval_sec=5,
        api_base_url=None  # Use default from settings
    )

    worker.start()


if __name__ == "__main__":
    main()

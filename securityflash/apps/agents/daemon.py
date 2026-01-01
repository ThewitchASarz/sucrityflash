"""
Agent Daemon - Auto-starts agents for RUNNING runs.

CRITICAL: This daemon is responsible for:
1. Polling DB for runs where status=RUNNING and agent_started_at is null
2. Starting agent loop in-process
3. Emitting AGENT_STARTED timeline event
4. Running deterministic recon workflow

V1 Implementation:
- Simple polling loop
- One agent per run (in-process)
- Graceful shutdown on SIGTERM
"""
import logging
import time
import signal
import sys
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from apps.api.db.session import SessionLocal
from apps.api.models.run import Run, RunStatus
from apps.api.models.scope import Scope
from apps.api.services.audit_service import audit_log
from apps.agents.orchestrator import OrchestratorAgent
from apps.api.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AgentDaemon:
    """
    Agent Daemon for auto-starting agents.

    Polls DB for RUNNING runs that need agents started.
    Spawns OrchestratorAgent in-process.
    """

    def __init__(
        self,
        poll_interval_sec: int = 5,
        api_base_url: Optional[str] = None
    ):
        """
        Initialize Agent Daemon.

        Args:
            poll_interval_sec: Polling interval in seconds
            api_base_url: Control Plane API base URL (defaults to settings)
        """
        self.poll_interval_sec = poll_interval_sec
        self.api_base_url = api_base_url or f"http://localhost:{settings.PORT}/api/v1"
        self.running = True

        # Handle graceful shutdown
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

        logger.info("Agent Daemon initialized")
        logger.info(f"Poll interval: {poll_interval_sec}s")
        logger.info(f"API base URL: {self.api_base_url}")

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signal."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
        sys.exit(0)

    def start(self):
        """
        Start daemon main loop.

        Polls DB for runs needing agents started.
        """
        logger.info("Agent Daemon starting main loop")

        while self.running:
            try:
                self._poll_and_start_agents()
                time.sleep(self.poll_interval_sec)

            except KeyboardInterrupt:
                logger.info("Daemon interrupted by user")
                break

            except Exception as e:
                logger.error(f"Error in daemon loop: {e}", exc_info=True)
                time.sleep(self.poll_interval_sec)

        logger.info("Agent Daemon stopped")

    def _poll_and_start_agents(self):
        """
        Poll DB for runs needing agents started.

        Logic:
        1. Query for runs where status=RUNNING and agent_started_at is null
        2. For each run:
           a. Mark agent_started_at = now()
           b. Emit AGENT_STARTED timeline event
           c. Spawn OrchestratorAgent
        """
        db: Session = SessionLocal()

        try:
            # Query for runs needing agents
            runs_needing_agents = db.query(Run).filter(
                Run.status == RunStatus.RUNNING,
                Run.agent_started_at == None
            ).all()

            if not runs_needing_agents:
                logger.debug("No runs needing agents")
                return

            logger.info(f"Found {len(runs_needing_agents)} runs needing agents")

            for run in runs_needing_agents:
                try:
                    self._start_agent_for_run(db, run)
                except Exception as e:
                    logger.error(f"Failed to start agent for run {run.id}: {e}", exc_info=True)

        finally:
            db.close()

    def _start_agent_for_run(self, db: Session, run: Run):
        """
        Start agent for a specific run.

        Args:
            db: Database session
            run: Run model instance
        """
        run_id = str(run.id)
        logger.info(f"Starting agent for run {run_id}")

        # Mark agent as started
        run.agent_started_at = datetime.utcnow()
        db.commit()

        # Get scope for context
        scope = db.query(Scope).filter(Scope.id == run.scope_id).first()
        if not scope:
            logger.error(f"Scope not found for run {run_id}")
            return

        # Emit AGENT_STARTED timeline event
        audit_log(
            db=db,
            run_id=run.id,
            event_type="AGENT_STARTED",
            actor="agent_daemon",
            details={
                "agent_type": "OrchestratorAgent",
                "run_id": run_id,
                "scope_id": str(run.scope_id),
                "targets_count": len(scope.scope_json.get("targets", [])),
                "policy_version": run.policy_version
            }
        )

        logger.info(f"Agent marked as started for run {run_id}")

        # Start OrchestratorAgent in-process
        # NOTE: In production, this would be spawned in a separate process/thread
        # For V1, we run in-process and block until agent completes
        try:
            agent = OrchestratorAgent(
                run_id=run_id,
                agent_id=f"orchestrator-{run_id[:8]}",
                api_base_url=self.api_base_url,
                max_iterations=run.max_iterations or 100,
                checkpoint_interval=5
            )

            logger.info(f"OrchestratorAgent initialized for run {run_id}")

            # Run agent (this blocks until agent completes or max iterations)
            agent.run()

            logger.info(f"OrchestratorAgent completed for run {run_id}")

            # Emit AGENT_COMPLETED timeline event
            audit_log(
                db=db,
                run_id=run.id,
                event_type="AGENT_COMPLETED",
                actor="agent_daemon",
                details={
                    "agent_type": "OrchestratorAgent",
                    "run_id": run_id,
                    "iterations": agent.iteration,
                    "targets_scanned": len(agent.scanned_targets) if hasattr(agent, 'scanned_targets') else 0
                }
            )

        except Exception as e:
            logger.error(f"Agent execution failed for run {run_id}: {e}", exc_info=True)

            # Emit AGENT_FAILED timeline event
            audit_log(
                db=db,
                run_id=run.id,
                event_type="AGENT_FAILED",
                actor="agent_daemon",
                details={
                    "agent_type": "OrchestratorAgent",
                    "run_id": run_id,
                    "error": str(e)
                }
            )


def main():
    """Main entry point for agent daemon."""
    logger.info("Starting Agent Daemon")

    daemon = AgentDaemon(
        poll_interval_sec=5,
        api_base_url=None  # Use default from settings
    )

    daemon.start()


if __name__ == "__main__":
    main()

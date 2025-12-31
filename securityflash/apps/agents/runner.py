"""
SecurityFlash V1 Agent Runtime.

CRITICAL: This is a standalone Python process, not a workflow engine.
Do not integrate n8n, Airflow, Celery, or other orchestrators in V1.

Agent execution model:
  1. python -m apps.agents.runner <run_id>
  2. Agent polls Control Plane API for run.status (must be RUNNING)
  3. Agent proposes ActionSpecs via POST /api/v1/runs/{run_id}/action-specs
  4. Agent waits for approval + execution (polls for evidence)
  5. Agent completes when done or max_iterations reached
  6. Process exits

MUST-FIX E: V1 uses in-repo Python agents only.
n8n integration is EXCLUDED from V1 (optional in V2+).

For multi-agent scenarios, deploy multiple containers.
For workflow choreography, add n8n in V2 (not V1).

Responsibilities:
- Read locked scope from Control Plane API
- Propose ActionSpecs (tool, arguments, target, proposed_by)
- NEVER execute tools directly (workers do this)
- NEVER modify scope or policy
- Poll for evidence after approval
- Checkpoint state every 5 iterations

V1 Agent: OrchestratorAgent (minimal, hardcoded logic)
- Proposes nmap scan for each target in scope
- No LLM reasoning in V1 (just deterministic target iteration)

Runtime Separation:
- Control Plane: apps/api/main.py (FastAPI)
- Agent Runtime: THIS FILE (separate Python process)
- Worker Runtime: apps/workers/runner.py (separate Python process)

Local dev: python -m apps.agents.runner <run_id>
"""
import sys
import logging
from apps.agents.orchestrator import OrchestratorAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("agent")


def main():
    """
    Agent runtime entrypoint.

    Usage:
        python -m apps.agents.runner <run_id>

    Examples:
        python -m apps.agents.runner 550e8400-e29b-41d4-a716-446655440000
    """
    if len(sys.argv) < 2:
        logger.error("Usage: python -m apps.agents.runner <run_id>")
        sys.exit(1)

    run_id = sys.argv[1]

    logger.info("=" * 80)
    logger.info("SecurityFlash V1 Agent Runtime")
    logger.info("=" * 80)
    logger.info(f"Run ID: {run_id}")
    logger.info("MUST-FIX E: V1 uses in-repo Python agents only (n8n excluded)")
    logger.info("CRITICAL: Agent NEVER executes tools (workers do this)")
    logger.info("=" * 80)

    try:
        # Initialize agent
        agent = OrchestratorAgent(
            run_id=run_id,
            agent_id=f"orchestrator-{run_id[:8]}"
        )

        # Run agent
        logger.info("Starting agent execution...")
        agent.run()

        logger.info("=" * 80)
        logger.info("Agent execution completed successfully")
        logger.info("=" * 80)

    except KeyboardInterrupt:
        logger.info("\nAgent interrupted by user")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Agent failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()


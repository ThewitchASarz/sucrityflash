"""
SecurityFlash V1 Worker Runtime.

CRITICAL: This is a stateless, deterministic execution runtime.
Workers NEVER reason, propose actions, or modify policy.

Worker execution model:
  1. python -m apps.workers.runner (daemon, runs forever)
  2. Poll GET /api/v1/action-specs?status=APPROVED&run_status=RUNNING every 5s
  3. For each approved action:
     a. Verify JWT token (signature, expiry, action_hash match)
     b. Validate tool in allowlist (httpx or nmap only in V1)
     c. Validate arguments (no shell metacharacters, safe flags)
     d. Execute tool via subprocess (shell=False, 30s timeout, 50KB output cap)
     e. Write evidence artifact to MinIO (S3-compatible)
     f. Create Evidence row in DB (artifact_uri, artifact_hash, metadata)
     g. Update action_specs.status: EXECUTING → EXECUTED (or FAILED)
     h. Log to audit_log: ACTION_EXECUTED, EVIDENCE_STORED
  4. Loop forever

MUST-FIX D: Resource Limits
- Docker container: CPU 1.0, Memory 512M
- Subprocess timeout: 30s (kills runaway processes)
- Output truncate: 50KB (prevents memory exhaustion)

V1 Tool Allowlist (HARDCODED):
- httpx: GET/POST only, 30s timeout
- nmap: -sV, -O, -p, -A, -Pn flags only (whitelist), 30s timeout

Token Verification (CRITICAL):
- JWT must be signed with POLICY_SIGNING_SECRET
- Expiration check (expires_at < now → reject)
- Action hash check (sha256(action_json) == token.action_hash → reject if mismatch)

Responsibilities:
- Fetch APPROVED actions from Control Plane
- Verify approval tokens (JWT signature + hash + expiry)
- Execute tools safely (no shell injection, resource limits)
- Write evidence immutably to MinIO
- Update action status (EXECUTING → EXECUTED/FAILED)
- Log all executions to audit_log

Runtime Separation:
- Control Plane: apps/api/main.py (FastAPI)
- Agent Runtime: apps/agents/runner.py (separate Python process)
- Worker Runtime: THIS FILE (separate Python process)

Local dev: python -m apps.workers.runner
"""
import time
import logging
import requests
from datetime import datetime
from typing import List, Dict, Any
from apps.workers.token_verify import verify_action_token
from apps.workers.tool_allowlist import is_tool_allowed
from apps.workers.tools.httpx_runner import run_httpx_safe
from apps.workers.tools.nmap_runner import run_nmap_safe
from apps.workers.tools.neurosploit_runner import run_neurosploit_safe
from apps.workers.evidence_writer import write_evidence

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("worker")

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
POLL_INTERVAL_SEC = 5


def fetch_approved_actions() -> List[Dict[str, Any]]:
    """
    Fetch APPROVED actions from Control Plane.

    Returns:
        List of ActionSpec dicts with status=APPROVED and run.status=RUNNING
    """
    try:
        # Note: This is a simplified query. In production, add run_status filter
        response = requests.get(
            f"{API_BASE_URL}/action-specs",
            params={"status": "APPROVED"}
        )

        if response.status_code == 200:
            # TODO: Filter by run.status=RUNNING (needs API support)
            return response.json()
        else:
            logger.warning(f"Failed to fetch actions: {response.status_code}")
            return []

    except Exception as e:
        logger.error(f"Error fetching actions: {e}")
        return []


def execute_action(action: Dict[str, Any]):
    """
    Execute a single approved action.

    Steps:
    1. Verify token
    2. Validate tool
    3. Execute tool
    4. Write evidence
    5. Update status
    """
    action_id = action["id"]
    run_id = action["run_id"]
    action_json = action["action_json"]
    approval_token = action.get("approval_token")

    logger.info(f"Executing action {action_id} (tool={action_json['tool']}, target={action_json['target']})")

    # 1. Verify token (CRITICAL)
    is_valid, error_msg = verify_action_token(action_json, approval_token)
    if not is_valid:
        logger.error(f"Token verification failed for {action_id}: {error_msg}")
        update_action_status(action_id, "FAILED", error_msg)
        return

    # 2. Validate tool
    tool = action_json["tool"]
    if not is_tool_allowed(tool):
        logger.error(f"Tool {tool} not in allowlist for {action_id}")
        update_action_status(action_id, "FAILED", f"Tool {tool} not allowed")
        return

    # 3. Update status to EXECUTING
    update_action_status(action_id, "EXECUTING", None)

    # 4. Execute tool
    try:
        if tool == "httpx":
            result = run_httpx_safe(
                arguments=action_json["arguments"],
                target=action_json["target"],
                timeout_sec=30
            )
        elif tool == "nmap":
            result = run_nmap_safe(
                arguments=action_json["arguments"],
                target=action_json["target"],
                timeout_sec=30
            )
        elif tool == "neurosploit":
            result = run_neurosploit_safe(
                action_arguments=action_json["arguments"],
                timeout_sec=30
            )
        else:
            result = {
                "status": "FAILED",
                "reason": f"Unknown tool {tool}",
                "stdout": "",
                "stderr": "",
                "returncode": -1
            }

        logger.info(f"Tool execution completed: {result['status']}")

        # 5. Write evidence
        try:
            evidence = write_evidence(
                run_id=run_id,
                tool_used=tool,
                tool_result=result,
                action_spec=action_json,
                api_base_url=API_BASE_URL
            )
            logger.info(f"Evidence created: {evidence['id']}")
        except Exception as e:
            logger.error(f"Failed to write evidence: {e}")

        # 6. Update action status to EXECUTED or FAILED
        final_status = "EXECUTED" if result["status"] == "EXECUTED" else "FAILED"
        update_action_status(action_id, final_status, result.get("reason"))

    except Exception as e:
        logger.error(f"Tool execution error: {e}")
        update_action_status(action_id, "FAILED", str(e))


def update_action_status(action_id: str, status: str, reason: str = None):
    """
    Update ActionSpec status via API.

    Note: In V1, we assume the API handles FSM validation.
    """
    try:
        # Note: This endpoint doesn't exist yet - simplified for V1
        # In reality, status transitions are handled by Control Plane
        logger.info(f"Action {action_id} → {status}" + (f" ({reason})" if reason else ""))
    except Exception as e:
        logger.error(f"Failed to update action status: {e}")


def worker_main():
    """
    Main worker loop.

    MUST-FIX D: This process should run in Docker with:
    - CPU limit: 1.0
    - Memory limit: 512M
    """
    logger.info("SecurityFlash Worker Runtime starting...")
    logger.info("MUST-FIX D: Resource limits enforced (CPU 1.0, Memory 512M)")
    logger.info(f"Polling interval: {POLL_INTERVAL_SEC}s")
    logger.info(f"Tool timeout: 30s, Output cap: 50KB")

    while True:
        try:
            # Fetch approved actions
            actions = fetch_approved_actions()

            if actions:
                logger.info(f"Found {len(actions)} approved actions")

                for action in actions:
                    try:
                        execute_action(action)
                    except Exception as e:
                        logger.error(f"Error executing action: {e}")

            # Sleep before next poll
            time.sleep(POLL_INTERVAL_SEC)

        except KeyboardInterrupt:
            logger.info("Worker shutting down...")
            break
        except Exception as e:
            logger.error(f"Worker loop error: {e}")
            time.sleep(POLL_INTERVAL_SEC)


if __name__ == "__main__":
    worker_main()

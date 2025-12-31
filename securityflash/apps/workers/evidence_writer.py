"""
Evidence writer - creates evidence records after tool execution.
"""
import hashlib
import json
from datetime import datetime
from typing import Dict, Any
from apps.workers.storage.minio_store import MinIOStore
import requests


def write_evidence(
    run_id: str,
    tool_used: str,
    tool_result: Dict[str, Any],
    action_spec: Dict[str, Any],
    api_base_url: str
) -> Dict[str, Any]:
    """
    Write evidence after tool execution.

    Steps:
    1. Compute SHA256 hash of stdout
    2. Write artifact to MinIO
    3. Create Evidence record via API
    4. Return evidence details

    Args:
        run_id: Run ID
        tool_used: Tool name (httpx, nmap)
        tool_result: Result from tool runner
        action_spec: ActionSpec that was executed
        api_base_url: Control Plane API base URL

    Returns:
        Evidence response dict
    """
    # Create evidence artifact
    artifact = {
        "tool_used": tool_used,
        "tool_version": "system",  # TODO: Get actual version
        "target": action_spec.get("target"),
        "arguments": action_spec.get("arguments"),
        "timestamp": datetime.utcnow().isoformat(),
        "returncode": tool_result.get("returncode"),
        "stdout": tool_result.get("stdout"),
        "stderr": tool_result.get("stderr"),
        "status": tool_result.get("status"),
        "model_attribution": None  # Tools don't use LLM
    }

    # Compute hash
    artifact_json = json.dumps(artifact, sort_keys=True)
    artifact_hash = hashlib.sha256(artifact_json.encode()).hexdigest()

    # Write to MinIO
    minio_store = MinIOStore()
    evidence_id = hashlib.sha256(f"{run_id}:{datetime.utcnow().isoformat()}".encode()).hexdigest()[:16]
    artifact_uri = minio_store.write_evidence(run_id, evidence_id, artifact)

    # Create Evidence record via API
    evidence_data = {
        "evidence_type": "command_output",
        "artifact_uri": artifact_uri,
        "artifact_hash": artifact_hash,
        "generated_by": "worker",
        "metadata": {
            "tool_used": tool_used,
            "timestamp": artifact["timestamp"],
            "returncode": tool_result.get("returncode"),
            "model_attribution": None
        }
    }

    response = requests.post(
        f"{api_base_url}/runs/{run_id}/evidence",
        json=evidence_data
    )

    if response.status_code != 201:
        raise Exception(f"Failed to create evidence record: {response.text}")

    return response.json()

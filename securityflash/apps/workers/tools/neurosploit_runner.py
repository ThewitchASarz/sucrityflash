"""
NeuroSploit tool wrapper.

This provides a governance-friendly shim around NeuroSploit modules so workers
can execute only pre-approved modules with strict resource limits, mirroring
the deterministic execution model used for httpx/nmap.
"""
import subprocess
from typing import Dict, Any

from apps.workers.tool_allowlist import get_neurosploit_allowed_modules


def run_neurosploit_safe(action_arguments: Dict[str, Any], timeout_sec: int = 30) -> Dict[str, Any]:
    """
    Execute a NeuroSploit module with safety constraints.

    Args:
        action_arguments: Dict containing at minimum ``module`` and optional
            ``options`` (list[str]) to pass through.
        timeout_sec: Execution timeout.

    Returns:
        Execution result dict with status, stdout, stderr, returncode, reason (on error).
    """
    module = action_arguments.get("module")
    options = action_arguments.get("options", [])

    if not module:
        return {
            "status": "FAILED",
            "reason": "Missing required module name",
            "stdout": "",
            "stderr": "module not provided",
            "returncode": -1,
        }

    allowed_modules = get_neurosploit_allowed_modules()
    if module not in allowed_modules:
        return {
            "status": "FAILED",
            "reason": f"Module {module} not in allowlist",
            "stdout": "",
            "stderr": f"Rejected: {module} not allowed",
            "returncode": -1,
        }

    cmd = ["neurosploit", module]
    if isinstance(options, list):
        cmd.extend([str(opt) for opt in options])

    try:
        result = subprocess.run(
            cmd,
            timeout=timeout_sec,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            check=False,
        )

        stdout_str = result.stdout.decode("utf-8", errors="ignore")[:51200]
        stderr_str = result.stderr.decode("utf-8", errors="ignore")[:5120]

        return {
            "status": "EXECUTED" if result.returncode == 0 else "FAILED",
            "stdout": stdout_str,
            "stderr": stderr_str,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "FAILED",
            "reason": f"Command exceeded {timeout_sec}s timeout",
            "stdout": "",
            "stderr": "Timeout",
            "returncode": -1,
        }
    except FileNotFoundError:
        return {
            "status": "FAILED",
            "reason": "neurosploit command not found (install required)",
            "stdout": "",
            "stderr": "neurosploit not found in PATH",
            "returncode": -1,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "FAILED",
            "reason": f"Execution error: {exc}",
            "stdout": "",
            "stderr": str(exc),
            "returncode": -1,
        }

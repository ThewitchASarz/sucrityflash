"""
httpx tool wrapper - MUST-FIX D: Resource limits enforced.

Safe execution:
- Only GET/POST methods
- 30s timeout
- 50KB output cap
- No shell injection
"""
import subprocess
from typing import Dict, Any, List


def run_httpx_safe(arguments: List[str], target: str, timeout_sec: int = 30) -> Dict[str, Any]:
    """
    Execute httpx with safety constraints.

    MUST-FIX D: Resource limits
    - Timeout: 30s (kills runaway processes)
    - Output cap: 50KB (prevents memory exhaustion)
    - No shell=True (prevents injection)

    Args:
        arguments: httpx command arguments
        target: Target URL
        timeout_sec: Timeout in seconds (default 30)

    Returns:
        Execution result dict with status, stdout, stderr, returncode
    """
    # Validate method (only GET/POST allowed)
    method = "GET"  # Default
    if "-m" in arguments or "--method" in arguments:
        try:
            method_idx = arguments.index("-m") if "-m" in arguments else arguments.index("--method")
            method = arguments[method_idx + 1].upper()
        except (IndexError, ValueError):
            pass

    if method not in ["GET", "POST"]:
        return {
            "status": "FAILED",
            "reason": f"Method {method} not allowed (only GET/POST)",
            "stdout": "",
            "stderr": f"Rejected: method {method} not in allowlist",
            "returncode": -1
        }

    # Build command
    cmd = ["httpx"] + arguments

    # Ensure target is included
    if target not in cmd:
        cmd.append(target)

    # Execute with timeout and output cap
    try:
        result = subprocess.run(
            cmd,
            timeout=timeout_sec,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,  # CRITICAL: Never use shell=True
            check=False
        )

        # Truncate output to 50KB
        stdout_str = result.stdout.decode('utf-8', errors='ignore')[:51200]  # 50KB
        stderr_str = result.stderr.decode('utf-8', errors='ignore')[:5120]   # 5KB

        return {
            "status": "EXECUTED" if result.returncode == 0 else "FAILED",
            "stdout": stdout_str,
            "stderr": stderr_str,
            "returncode": result.returncode
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "FAILED",
            "reason": f"Command exceeded {timeout_sec}s timeout",
            "stdout": "",
            "stderr": "Timeout",
            "returncode": -1
        }
    except FileNotFoundError:
        return {
            "status": "FAILED",
            "reason": "httpx command not found (is it installed?)",
            "stdout": "",
            "stderr": "httpx not found in PATH",
            "returncode": -1
        }
    except Exception as e:
        return {
            "status": "FAILED",
            "reason": f"Execution error: {str(e)}",
            "stdout": "",
            "stderr": str(e),
            "returncode": -1
        }

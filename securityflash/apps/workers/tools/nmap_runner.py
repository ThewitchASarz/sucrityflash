"""
nmap tool wrapper - MUST-FIX D: Resource limits enforced.

Safe execution:
- Only safe flags allowed (-sV, -O, -p, -A, -Pn)
- 30s timeout
- 50KB output cap
- No shell injection
- Greppable format (-oG -)
"""
import subprocess
from typing import Dict, Any, List


# Whitelist of allowed nmap flags
ALLOWED_FLAGS = {"-sV", "-O", "-p", "-A", "-Pn", "-oG", "--open", "-T4", "-T3", "-T2", "-T1", "-T0"}


def run_nmap_safe(arguments: List[str], target: str, timeout_sec: int = 30) -> Dict[str, Any]:
    """
    Execute nmap with safety constraints.

    MUST-FIX D: Resource limits
    - Timeout: 30s (kills runaway scans)
    - Output cap: 50KB (prevents memory exhaustion)
    - Flag whitelist: Only safe reconnaissance flags
    - No shell=True (prevents injection)

    Args:
        arguments: nmap command arguments
        target: Target to scan
        timeout_sec: Timeout in seconds (default 30)

    Returns:
        Execution result dict with status, stdout, stderr, returncode
    """
    # Validate all flags are in allowlist
    for arg in arguments:
        if arg.startswith("-"):
            # Extract flag (e.g., "-sV" or "-oG")
            flag = arg.split("=")[0] if "=" in arg else arg.split()[0]

            if flag not in ALLOWED_FLAGS:
                return {
                    "status": "FAILED",
                    "reason": f"Flag {flag} not allowed (whitelist: {ALLOWED_FLAGS})",
                    "stdout": "",
                    "stderr": f"Rejected: flag {flag} not in allowlist",
                    "returncode": -1
                }

    # Build command
    cmd = ["nmap"] + arguments

    # Ensure target is included
    if target not in cmd:
        cmd.append(target)

    # Force greppable format if not present
    if "-oG" not in arguments:
        cmd.extend(["-oG", "-"])

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
            "reason": "nmap command not found (is it installed?)",
            "stdout": "",
            "stderr": "nmap not found in PATH",
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

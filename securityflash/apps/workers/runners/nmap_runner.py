"""
Nmap runner with SAFE FLAGS ONLY.

Enforces: -sV -T3 --top-ports 100 --max-retries 2 --host-timeout 2m
NO exploit scripts, NO aggressive scans, NO -Pn unless explicitly allowed.
"""
import subprocess
import shutil
import json
from typing import Dict, Any
from .base import BaseRunner, ToolResult


class NmapRunner(BaseRunner):
    """Nmap scanner with safety constraints."""

    def __init__(self):
        super().__init__(
            tool_name="nmap",
            max_runtime_sec=300,
            output_cap_kb=500
        )

    def run(self, action_json: Dict[str, Any]) -> ToolResult:
        """
        Execute nmap scan with SAFE flags only.

        Expected action_json:
        {
            "tool": "nmap",
            "arguments": {"target": "192.168.1.1", "ports": "80,443"},
            "target": "192.168.1.1"
        }
        """
        # Check if nmap is installed
        if not shutil.which("nmap"):
            return ToolResult(
                success=False,
                stdout="",
                stderr="nmap is not installed in this container",
                exit_code=127,
                artifacts=[
                    self._create_artifact(
                        filename="nmap_error.txt",
                        content="Tool unavailable: nmap is not installed. Please install nmap in the worker container.",
                        mime_type="text/plain"
                    )
                ],
                execution_time_sec=0.0,
                error_message="nmap not installed"
            )

        try:
            target = action_json.get("target") or action_json.get("arguments", {}).get("target")
            if not target:
                return ToolResult(
                    success=False,
                    stdout="",
                    stderr="No target provided",
                    exit_code=1,
                    artifacts=[],
                    execution_time_sec=0.0,
                    error_message="Missing target"
                )

            # Build SAFE nmap command
            cmd = [
                "nmap",
                "-sV",  # Service version detection
                "-T3",  # Normal timing (not aggressive)
                "--top-ports", "100",  # Only scan top 100 ports
                "--max-retries", "2",
                "--host-timeout", "2m",
                "-oX", "-",  # XML output to stdout
                target
            ]

            import time
            start_time = time.time()

            # Execute nmap
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.max_runtime_sec
            )

            execution_time = time.time() - start_time

            stdout = result.stdout
            stderr = result.stderr

            # Create artifacts
            artifacts = [
                self._create_artifact(
                    filename="nmap_output.xml",
                    content=stdout,
                    mime_type="application/xml"
                ),
                self._create_artifact(
                    filename="nmap_scan.txt",
                    content=f"""Nmap Scan Results
Target: {target}
Command: {' '.join(cmd)}
Execution Time: {execution_time:.2f}s
Exit Code: {result.returncode}

{stdout}
""",
                    mime_type="text/plain"
                )
            ]

            return ToolResult(
                success=result.returncode == 0,
                stdout=self._cap_output(stdout),
                stderr=self._cap_output(stderr),
                exit_code=result.returncode,
                artifacts=artifacts,
                execution_time_sec=execution_time
            )

        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                stdout="",
                stderr=f"nmap scan timed out after {self.max_runtime_sec} seconds",
                exit_code=124,
                artifacts=[],
                execution_time_sec=self.max_runtime_sec,
                error_message="Timeout"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                stdout="",
                stderr=f"Error executing nmap: {str(e)}",
                exit_code=1,
                artifacts=[],
                execution_time_sec=0.0,
                error_message=str(e)
            )

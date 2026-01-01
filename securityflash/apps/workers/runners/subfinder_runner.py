"""
Subfinder runner for subdomain enumeration.

Gracefully fails if subfinder CLI not installed.
"""
import subprocess
import shutil
import json
from typing import Dict, Any
from .base import BaseRunner, ToolResult


class SubfinderRunner(BaseRunner):
    """Subfinder for subdomain enumeration."""

    def __init__(self):
        super().__init__(
            tool_name="subfinder",
            max_runtime_sec=120,
            output_cap_kb=200
        )

    def run(self, action_json: Dict[str, Any]) -> ToolResult:
        """
        Execute subfinder.

        Expected action_json:
        {
            "tool": "subfinder",
            "arguments": {"domain": "example.com"},
            "target": "example.com"
        }
        """
        # Check if subfinder is installed
        if not shutil.which("subfinder"):
            return ToolResult(
                success=False,
                stdout="",
                stderr="subfinder is not installed in this container",
                exit_code=127,
                artifacts=[
                    self._create_artifact(
                        filename="subfinder_error.txt",
                        content="Tool unavailable: subfinder is not installed. Install from: https://github.com/projectdiscovery/subfinder",
                        mime_type="text/plain"
                    )
                ],
                execution_time_sec=0.0,
                error_message="subfinder not installed"
            )

        try:
            domain = action_json.get("target") or action_json.get("arguments", {}).get("domain")
            if not domain:
                return ToolResult(
                    success=False,
                    stdout="",
                    stderr="No domain provided",
                    exit_code=1,
                    artifacts=[],
                    execution_time_sec=0.0,
                    error_message="Missing domain"
                )

            cmd = ["subfinder", "-d", domain, "-silent", "-json"]

            import time
            start_time = time.time()

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.max_runtime_sec
            )

            execution_time = time.time() - start_time

            # Parse subdomains
            subdomains = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        data = json.loads(line)
                        subdomains.append(data.get('host', line))
                    except:
                        subdomains.append(line)

            output = f"""Subfinder Results
Domain: {domain}
Subdomains Found: {len(subdomains)}
Execution Time: {execution_time:.2f}s

Subdomains:
{chr(10).join(subdomains[:100])}  # Cap at 100
"""

            artifacts = [
                self._create_artifact(
                    filename="subfinder_results.json",
                    content=json.dumps({"domain": domain, "subdomains": subdomains, "count": len(subdomains)}, indent=2),
                    mime_type="application/json"
                ),
                self._create_artifact(
                    filename="subfinder_subdomains.txt",
                    content="\n".join(subdomains),
                    mime_type="text/plain"
                )
            ]

            return ToolResult(
                success=result.returncode == 0,
                stdout=self._cap_output(output),
                stderr=self._cap_output(result.stderr),
                exit_code=result.returncode,
                artifacts=artifacts,
                execution_time_sec=execution_time
            )

        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                stdout="",
                stderr=f"subfinder timed out after {self.max_runtime_sec} seconds",
                exit_code=124,
                artifacts=[],
                execution_time_sec=self.max_runtime_sec,
                error_message="Timeout"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                stdout="",
                stderr=f"Error executing subfinder: {str(e)}",
                exit_code=1,
                artifacts=[],
                execution_time_sec=0.0,
                error_message=str(e)
            )

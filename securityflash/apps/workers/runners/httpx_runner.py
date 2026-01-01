"""
HTTP probe runner using Python httpx library.

SAFE RECON ONLY - no exploitation, just HTTP probing.
"""
import httpx
import json
from typing import Dict, Any
from .base import BaseRunner, ToolResult


class HttpxRunner(BaseRunner):
    """HTTP probe using httpx Python library."""

    def __init__(self):
        super().__init__(
            tool_name="httpx",
            max_runtime_sec=60,
            output_cap_kb=100
        )

    def run(self, action_json: Dict[str, Any]) -> ToolResult:
        """
        Execute HTTP probe.

        Expected action_json:
        {
            "tool": "httpx",
            "arguments": {"url": "https://example.com", "timeout": 30},
            "target": "https://example.com"
        }
        """
        try:
            target_url = action_json.get("target") or action_json.get("arguments", {}).get("url")
            if not target_url:
                return ToolResult(
                    success=False,
                    stdout="",
                    stderr="No target URL provided",
                    exit_code=1,
                    artifacts=[],
                    execution_time_sec=0.0,
                    error_message="Missing target URL"
                )

            timeout = action_json.get("arguments", {}).get("timeout", 30)
            follow_redirects = action_json.get("arguments", {}).get("follow_redirects", True)
            verify_ssl = action_json.get("arguments", {}).get("verify_ssl", True)

            import time
            start_time = time.time()

            # Execute HTTP request
            with httpx.Client(timeout=timeout, follow_redirects=follow_redirects, verify=verify_ssl) as client:
                response = client.get(target_url)

            execution_time = time.time() - start_time

            # Build result output
            result_data = {
                "url": target_url,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content_length": len(response.content),
                "response_time_sec": execution_time,
                "redirect_chain": [str(r.url) for r in response.history] if response.history else []
            }

            stdout = f"""HTTP Probe Results:
URL: {target_url}
Status: {response.status_code}
Content-Length: {len(response.content)} bytes
Response Time: {execution_time:.2f}s
Redirects: {len(response.history)}
Server: {response.headers.get('server', 'unknown')}
"""

            # Create artifacts
            artifacts = [
                self._create_artifact(
                    filename="httpx_result.json",
                    content=json.dumps(result_data, indent=2),
                    mime_type="application/json"
                ),
                self._create_artifact(
                    filename="httpx_headers.txt",
                    content="\n".join([f"{k}: {v}" for k, v in response.headers.items()]),
                    mime_type="text/plain"
                )
            ]

            return ToolResult(
                success=True,
                stdout=self._cap_output(stdout),
                stderr="",
                exit_code=0,
                artifacts=artifacts,
                execution_time_sec=execution_time
            )

        except httpx.TimeoutException as e:
            return ToolResult(
                success=False,
                stdout="",
                stderr=f"HTTP request timed out: {str(e)}",
                exit_code=1,
                artifacts=[],
                execution_time_sec=0.0,
                error_message=f"Timeout: {str(e)}"
            )
        except httpx.HTTPError as e:
            return ToolResult(
                success=False,
                stdout="",
                stderr=f"HTTP error: {str(e)}",
                exit_code=1,
                artifacts=[],
                execution_time_sec=0.0,
                error_message=f"HTTP error: {str(e)}"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                stdout="",
                stderr=f"Unexpected error: {str(e)}",
                exit_code=1,
                artifacts=[],
                execution_time_sec=0.0,
                error_message=f"Error: {str(e)}"
            )

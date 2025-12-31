"""
Mock Burp Suite tool for web application scanning (L1 - Active Scanning).
"""
import asyncio
from datetime import datetime
from tools.base import BaseTool, ToolResult


class BurpTool(BaseTool):
    """Mock Burp Suite for web application vulnerability scanning."""

    def __init__(self):
        super().__init__(tool_name="burpsuite")

    async def execute(
        self,
        action_id: str,
        target: str,
        parameters: dict
    ) -> ToolResult:
        """
        Execute Burp Suite scan.

        Parameters:
            scan_type: "passive_crawl", "active_scan", "intruder"
            scope: "in_scope_only" (default: true)
            max_depth: Crawl depth (default: 3)
        """
        started_at = datetime.utcnow()

        try:
            scan_type = parameters.get("scan_type", "passive_crawl")
            max_depth = parameters.get("max_depth", 3)

            # Simulate scan delay
            await asyncio.sleep(3)

            # Mock scan results
            output = self._generate_mock_scan(target, scan_type, max_depth)

            completed_at = datetime.utcnow()
            return self._create_result(
                action_id=action_id,
                target=target,
                status="success",
                output=output,
                error=None,
                started_at=started_at,
                completed_at=completed_at
            )

        except Exception as e:
            completed_at = datetime.utcnow()
            return self._create_result(
                action_id=action_id,
                target=target,
                status="error",
                output={},
                error=str(e),
                started_at=started_at,
                completed_at=completed_at
            )

    def _generate_mock_scan(self, target: str, scan_type: str, max_depth: int) -> dict:
        """Generate realistic mock Burp scan results."""
        return {
            "scan_type": scan_type,
            "target": target,
            "max_depth": max_depth,
            "crawl_results": {
                "urls_discovered": 47,
                "forms_found": 12,
                "parameters_found": 38,
                "cookies_found": 5
            },
            "findings": [
                {
                    "severity": "high",
                    "title": "SQL Injection",
                    "url": f"{target}/api/users?id=1",
                    "parameter": "id",
                    "evidence": "MySQL error message in response",
                    "confidence": "firm"
                },
                {
                    "severity": "medium",
                    "title": "Cross-Site Scripting (Reflected)",
                    "url": f"{target}/search?q=test",
                    "parameter": "q",
                    "evidence": "Unescaped input in HTML context",
                    "confidence": "certain"
                },
                {
                    "severity": "low",
                    "title": "Missing Content-Security-Policy Header",
                    "url": f"{target}/",
                    "parameter": "N/A",
                    "evidence": "No CSP header present",
                    "confidence": "certain"
                },
                {
                    "severity": "info",
                    "title": "Cookie Without Secure Flag",
                    "url": f"{target}/login",
                    "parameter": "session_id",
                    "evidence": "Cookie transmitted over HTTPS without Secure flag",
                    "confidence": "certain"
                }
            ],
            "owasp_mappings": [
                "A03:2021 - Injection",
                "A07:2021 - Cross-Site Scripting (XSS)",
                "A05:2021 - Security Misconfiguration"
            ]
        }


# Global instance
burp_tool = BurpTool()

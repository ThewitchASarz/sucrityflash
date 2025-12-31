"""
Mock Nmap tool for network scanning (L1 - Active Scanning).
"""
import asyncio
from datetime import datetime
from typing import Optional
from tools.base import BaseTool, ToolResult


class NmapTool(BaseTool):
    """Mock Nmap scanner for port scanning and service detection."""

    def __init__(self):
        super().__init__(tool_name="nmap")

    async def execute(
        self,
        action_id: str,
        target: str,
        parameters: dict
    ) -> ToolResult:
        """
        Execute Nmap scan.

        Parameters:
            scan_type: "syn", "tcp_connect", "udp", "service_version"
            ports: "22,80,443" or "1-1000" or "all"
            timing: "T0" to "T5" (default: "T3")
        """
        started_at = datetime.utcnow()

        try:
            scan_type = parameters.get("scan_type", "syn")
            ports = parameters.get("ports", "1-1000")
            timing = parameters.get("timing", "T3")

            # Simulate scan delay
            await asyncio.sleep(2)

            # Mock scan results
            output = self._generate_mock_scan(target, scan_type, ports)

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

    def _generate_mock_scan(self, target: str, scan_type: str, ports: str) -> dict:
        """Generate realistic mock Nmap scan results."""
        # Mock open ports based on common services
        mock_ports = [
            {"port": 22, "state": "open", "service": "ssh", "version": "OpenSSH 8.2p1"},
            {"port": 80, "state": "open", "service": "http", "version": "nginx 1.18.0"},
            {"port": 443, "state": "open", "service": "https", "version": "nginx 1.18.0"},
            {"port": 3306, "state": "filtered", "service": "mysql", "version": ""},
            {"port": 8080, "state": "open", "service": "http-proxy", "version": "Tomcat 9.0.40"},
        ]

        return {
            "scan_type": scan_type,
            "target": target,
            "ports_scanned": ports,
            "scan_result": {
                "host_status": "up",
                "latency_ms": 12.5,
                "open_ports": [p for p in mock_ports if p["state"] == "open"],
                "filtered_ports": [p for p in mock_ports if p["state"] == "filtered"],
                "closed_ports_count": 995,
                "os_detection": {
                    "os_family": "Linux",
                    "os_generation": "4.x",
                    "accuracy": 95
                }
            },
            "vulnerabilities_hint": [
                "Outdated nginx version (CVE-2021-23017 potential)",
                "SSH banner reveals version (information disclosure)"
            ]
        }


# Global instance
nmap_tool = NmapTool()

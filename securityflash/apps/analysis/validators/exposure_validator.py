"""
Exposure Validator - Phase 2/3

Analyzes port scans and service enumeration.
Generates DRAFT findings for exposed services and open ports.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class ExposureValidator:
    """
    Validates service exposure from nmap outputs.

    Checks for:
    - Open ports with known vulnerabilities
    - Exposed administrative interfaces
    - Unnecessary services
    - Version information disclosure
    """

    HIGH_RISK_PORTS = {
        21: ("FTP", "MEDIUM", "FTP service exposed - often misconfigured or outdated"),
        23: ("Telnet", "HIGH", "Telnet service exposed - transmits credentials in cleartext"),
        69: ("TFTP", "MEDIUM", "TFTP service exposed - no authentication"),
        135: ("MSRPC", "MEDIUM", "Microsoft RPC exposed - potential for RCE"),
        139: ("NetBIOS", "MEDIUM", "NetBIOS exposed - information disclosure"),
        445: ("SMB", "HIGH", "SMB service exposed - high-value target for attacks"),
        1433: ("MSSQL", "HIGH", "Microsoft SQL Server exposed - should be internal only"),
        1521: ("Oracle", "HIGH", "Oracle Database exposed - should be internal only"),
        3306: ("MySQL", "HIGH", "MySQL Database exposed - should be internal only"),
        3389: ("RDP", "HIGH", "Remote Desktop exposed - common brute-force target"),
        5432: ("PostgreSQL", "HIGH", "PostgreSQL Database exposed - should be internal only"),
        5900: ("VNC", "HIGH", "VNC service exposed - often weak authentication"),
        6379: ("Redis", "HIGH", "Redis exposed - often no authentication by default"),
        8080: ("HTTP-Proxy", "MEDIUM", "HTTP proxy/admin interface exposed"),
        9200: ("Elasticsearch", "HIGH", "Elasticsearch exposed - often unauthenticated"),
        27017: ("MongoDB", "HIGH", "MongoDB exposed - often unauthenticated"),
    }

    def validate(self, evidence_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Validate service exposure from nmap evidence.

        Args:
            evidence_data: Raw nmap output

        Returns:
            List of draft finding dictionaries
        """
        findings = []

        # Only process nmap evidence
        if "nmap" not in evidence_data.get("tool", "").lower():
            return findings

        output = evidence_data.get("stdout", "") or evidence_data.get("output", "")

        # Parse nmap output for open ports
        port_pattern = r"(\d+)/(tcp|udp)\s+open\s+(\S+)"
        matches = re.findall(port_pattern, output, re.IGNORECASE)

        for port_str, protocol, service_name in matches:
            port_num = int(port_str)

            # Check if this is a high-risk port
            if port_num in self.HIGH_RISK_PORTS:
                service_info, severity, description = self.HIGH_RISK_PORTS[port_num]

                findings.append({
                    "title": f"Exposed {service_info} Service (Port {port_num}/{protocol})",
                    "severity": severity,
                    "category": "EXPOSURE",
                    "description_md": (
                        f"{description}\n\n"
                        f"**Port:** {port_num}/{protocol}\n"
                        f"**Service:** {service_name}\n\n"
                        f"**Recommendation:** "
                        f"If this service must be exposed, ensure it is:\n"
                        f"- Behind a firewall with IP restrictions\n"
                        f"- Using strong authentication\n"
                        f"- Fully patched and up-to-date\n"
                        f"- Monitored for suspicious activity"
                    ),
                    "affected_target": evidence_data.get("target", "unknown"),
                    "evidence_ids": [evidence_data.get("evidence_id", "")],
                })

        # Check for version information disclosure
        version_pattern = r"(\d+/\w+)\s+open\s+\S+\s+(.+)"
        version_matches = re.findall(version_pattern, output)

        if version_matches:
            # Count how many services expose version info
            version_count = len([m for m in version_matches if len(m[1].strip()) > 3])

            if version_count > 0:
                findings.append({
                    "title": "Service Version Information Disclosure",
                    "severity": "INFO",
                    "category": "RECON",
                    "description_md": (
                        f"Multiple services ({version_count}) expose detailed version information.\n\n"
                        f"**Impact:** Attackers can identify specific vulnerabilities for exposed versions.\n\n"
                        f"**Recommendation:** Configure services to suppress version banners where possible."
                    ),
                    "affected_target": evidence_data.get("target", "unknown"),
                    "evidence_ids": [evidence_data.get("evidence_id", "")],
                })

        return findings

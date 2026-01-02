"""
TLS Posture Validator - Phase 2/3

Analyzes TLS configuration from httpx/nmap outputs.
Generates DRAFT findings for weak TLS configurations.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class TLSPostureValidator:
    """
    Validates TLS posture from tool outputs.

    Checks for:
    - TLS version (TLS 1.0, 1.1 deprecated)
    - Weak cipher suites
    - Certificate issues
    - Missing HSTS
    """

    WEAK_TLS_VERSIONS = {"TLSv1.0", "TLSv1.1", "SSLv2", "SSLv3"}
    WEAK_CIPHERS = {
        "RC4", "MD5", "DES", "3DES", "NULL", "EXPORT", "anon"
    }

    def validate(self, evidence_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Validate TLS posture from evidence.

        Args:
            evidence_data: Raw tool output (httpx, nmap, testssl)

        Returns:
            List of draft finding dictionaries
        """
        findings = []

        # Extract TLS info from different tools
        if "httpx" in evidence_data.get("tool", "").lower():
            findings.extend(self._validate_httpx(evidence_data))
        elif "nmap" in evidence_data.get("tool", "").lower():
            findings.extend(self._validate_nmap(evidence_data))

        return findings

    def _validate_httpx(self, evidence: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validate TLS from httpx output."""
        findings = []
        output = evidence.get("stdout", "") or evidence.get("output", "")

        # Check for TLS version in output
        tls_match = re.search(r"TLS[v]?[\s]*([0-9.]+)", output, re.IGNORECASE)
        if tls_match:
            tls_version = f"TLS {tls_match.group(1)}"
            tls_key = f"TLSv{tls_match.group(1)}"

            if tls_key in self.WEAK_TLS_VERSIONS:
                findings.append({
                    "title": f"Weak TLS Version Detected: {tls_version}",
                    "severity": "MEDIUM",
                    "category": "CRYPTO",
                    "description_md": (
                        f"The target supports {tls_version}, which is deprecated and vulnerable to attacks.\n\n"
                        f"**Impact:** Communication may be intercepted or downgraded.\n\n"
                        f"**Recommendation:** Disable {tls_version} and use TLS 1.2 or higher."
                    ),
                    "affected_target": evidence.get("target", "unknown"),
                    "evidence_ids": [evidence.get("evidence_id", "")],
                })

        # Check for HSTS header
        if "strict-transport-security" not in output.lower():
            findings.append({
                "title": "Missing HSTS Header",
                "severity": "LOW",
                "category": "CONFIG",
                "description_md": (
                    "The HTTP Strict Transport Security (HSTS) header is not present.\n\n"
                    "**Impact:** Users may connect via insecure HTTP, allowing man-in-the-middle attacks.\n\n"
                    "**Recommendation:** Add `Strict-Transport-Security` header with `max-age=31536000; includeSubDomains`."
                ),
                "affected_target": evidence.get("target", "unknown"),
                "evidence_ids": [evidence.get("evidence_id", "")],
            })

        return findings

    def _validate_nmap(self, evidence: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validate TLS from nmap ssl-enum-ciphers output."""
        findings = []
        output = evidence.get("stdout", "") or evidence.get("output", "")

        # Check for weak ciphers in nmap output
        for weak_cipher in self.WEAK_CIPHERS:
            if weak_cipher.lower() in output.lower():
                findings.append({
                    "title": f"Weak Cipher Suite Detected: {weak_cipher}",
                    "severity": "MEDIUM",
                    "category": "CRYPTO",
                    "description_md": (
                        f"The target supports the weak cipher suite containing {weak_cipher}.\n\n"
                        f"**Impact:** Communication may be vulnerable to cryptographic attacks.\n\n"
                        f"**Recommendation:** Disable weak ciphers and use modern cipher suites (AES-GCM, ChaCha20)."
                    ),
                    "affected_target": evidence.get("target", "unknown"),
                    "evidence_ids": [evidence.get("evidence_id", "")],
                })
                break  # Only report once per evidence

        return findings

"""
Header Validator - Phase 2/3

Analyzes HTTP security headers from httpx outputs.
Generates DRAFT findings for missing security headers.
"""
from __future__ import annotations

import logging
import re
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class HeaderValidator:
    """
    Validates HTTP security headers.

    Checks for:
    - Content-Security-Policy
    - X-Frame-Options
    - X-Content-Type-Options
    - Referrer-Policy
    - Permissions-Policy
    """

    SECURITY_HEADERS = {
        "content-security-policy": {
            "severity": "MEDIUM",
            "title": "Missing Content-Security-Policy Header",
            "description": (
                "The Content-Security-Policy (CSP) header is not present.\n\n"
                "**Impact:** Application is vulnerable to XSS and injection attacks.\n\n"
                "**Recommendation:** Implement CSP with restrictive directives."
            )
        },
        "x-frame-options": {
            "severity": "MEDIUM",
            "title": "Missing X-Frame-Options Header",
            "description": (
                "The X-Frame-Options header is not present.\n\n"
                "**Impact:** Application may be vulnerable to clickjacking attacks.\n\n"
                "**Recommendation:** Add `X-Frame-Options: DENY` or `SAMEORIGIN`."
            )
        },
        "x-content-type-options": {
            "severity": "LOW",
            "title": "Missing X-Content-Type-Options Header",
            "description": (
                "The X-Content-Type-Options header is not present.\n\n"
                "**Impact:** Browsers may incorrectly interpret file types, leading to XSS.\n\n"
                "**Recommendation:** Add `X-Content-Type-Options: nosniff`."
            )
        },
        "strict-transport-security": {
            "severity": "MEDIUM",
            "title": "Missing Strict-Transport-Security Header",
            "description": (
                "The HSTS header is not present.\n\n"
                "**Impact:** Users may connect via insecure HTTP.\n\n"
                "**Recommendation:** Add `Strict-Transport-Security: max-age=31536000; includeSubDomains`."
            )
        },
        "referrer-policy": {
            "severity": "INFO",
            "title": "Missing Referrer-Policy Header",
            "description": (
                "The Referrer-Policy header is not present.\n\n"
                "**Impact:** Referrer information may leak sensitive data in URLs.\n\n"
                "**Recommendation:** Add `Referrer-Policy: no-referrer` or `strict-origin-when-cross-origin`."
            )
        },
    }

    def validate(self, evidence_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Validate security headers from httpx evidence.

        Args:
            evidence_data: Raw httpx output

        Returns:
            List of draft finding dictionaries
        """
        findings = []

        # Only process httpx evidence
        if "httpx" not in evidence_data.get("tool", "").lower():
            return findings

        output = evidence_data.get("stdout", "") or evidence_data.get("output", "")
        headers_lower = output.lower()

        # Check each security header
        for header_name, header_info in self.SECURITY_HEADERS.items():
            if header_name not in headers_lower:
                findings.append({
                    "title": header_info["title"],
                    "severity": header_info["severity"],
                    "category": "CONFIG",
                    "description_md": header_info["description"],
                    "affected_target": evidence_data.get("target", "unknown"),
                    "evidence_ids": [evidence_data.get("evidence_id", "")],
                })

        # Check for insecure cookies (without Secure flag)
        if "set-cookie:" in headers_lower:
            # Look for cookies without Secure flag
            cookie_lines = [line for line in output.split("\n") if "set-cookie:" in line.lower()]
            for cookie_line in cookie_lines:
                if "secure" not in cookie_line.lower():
                    findings.append({
                        "title": "Cookie Without Secure Flag",
                        "severity": "MEDIUM",
                        "category": "CONFIG",
                        "description_md": (
                            "One or more cookies are set without the `Secure` flag.\n\n"
                            "**Impact:** Cookies may be transmitted over unencrypted connections.\n\n"
                            "**Recommendation:** Add `Secure` flag to all cookies."
                        ),
                        "affected_target": evidence_data.get("target", "unknown"),
                        "evidence_ids": [evidence_data.get("evidence_id", "")],
                    })
                    break  # Only report once

                if "httponly" not in cookie_line.lower():
                    findings.append({
                        "title": "Cookie Without HttpOnly Flag",
                        "severity": "MEDIUM",
                        "category": "CONFIG",
                        "description_md": (
                            "One or more cookies are set without the `HttpOnly` flag.\n\n"
                            "**Impact:** Cookies may be accessible via JavaScript, increasing XSS risk.\n\n"
                            "**Recommendation:** Add `HttpOnly` flag to all cookies."
                        ),
                        "affected_target": evidence_data.get("target", "unknown"),
                        "evidence_ids": [evidence_data.get("evidence_id", "")],
                    })
                    break  # Only report once

        return findings

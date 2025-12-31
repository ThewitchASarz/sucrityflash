"""
Tool allowlist enum (Layer 2 enforcement - V2 requirement).

Per spec: "Three-layer enforcement:
1. Policy Engine allowlist (service)
2. Worker Runtime enum (this file)
3. Subprocess validation (tool exists, flags valid)"
"""
from enum import Enum


class AllowedToolV2MVP(str, Enum):
    """
    Stage 1 tools allowlist for V2 MVP.

    CRITICAL: Only these tools can be executed in V2 MVP.
    Stage 2 tools (nuclei, sqlmap, nikto) MUST be rejected.
    """
    HTTPX = "httpx"
    NMAP = "nmap"
    DNSX = "dnsx"
    SUBFINDER = "subfinder"
    KATANA = "katana"
    FFUF = "ffuf"

    @classmethod
    def is_allowed(cls, method: str) -> bool:
        """
        Check if tool method is in allowlist.

        Args:
            method: Tool method name

        Returns:
            bool: True if allowed
        """
        try:
            cls(method.lower())
            return True
        except ValueError:
            return False

    @classmethod
    def get_allowed_tools(cls) -> list[str]:
        """Get list of allowed tool names."""
        return [tool.value for tool in cls]


# Rejected tools (Stage 2 - not in V2 MVP)
STAGE_2_TOOLS_REJECTED = {
    "nuclei": "Stage 2 tool - not allowed in V2 MVP",
    "sqlmap": "Stage 2 tool - not allowed in V2 MVP",
    "nikto": "Stage 2 tool - not allowed in V2 MVP"
}


def validate_tool_allowlist(method: str) -> tuple[bool, str]:
    """
    Validate tool against allowlist (Layer 2 enforcement).

    Args:
        method: Tool method name

    Returns:
        tuple[bool, str]: (is_allowed, error_or_success_message)
    """
    method_lower = method.lower()

    # Check if Stage 2 tool (explicitly rejected)
    if method_lower in STAGE_2_TOOLS_REJECTED:
        return False, STAGE_2_TOOLS_REJECTED[method_lower]

    # Check if in Stage 1 allowlist
    if not AllowedToolV2MVP.is_allowed(method_lower):
        allowed_list = ", ".join(AllowedToolV2MVP.get_allowed_tools())
        return False, f"Tool '{method}' not in allowlist. Allowed: {allowed_list}"

    return True, f"Tool '{method}' is allowed (Stage 1)"

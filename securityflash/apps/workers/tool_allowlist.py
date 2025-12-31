"""
Tool allowlist - V1 hardcoded to httpx and nmap only.
"""
from enum import Enum


class AllowedTool(str, Enum):
    """V1 tool allowlist."""
    HTTPX = "httpx"
    NMAP = "nmap"


def is_tool_allowed(tool: str) -> bool:
    """Check if tool is in V1 allowlist."""
    try:
        AllowedTool(tool)
        return True
    except ValueError:
        return False


def get_allowed_tools() -> list[str]:
    """Get list of allowed tools."""
    return [t.value for t in AllowedTool]

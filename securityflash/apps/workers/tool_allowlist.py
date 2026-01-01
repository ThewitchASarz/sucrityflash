"""
Tool allowlist

Extended to include NeuroSploit for autonomous recon while still enforcing a
tight, enumerated list of allowed modules. This mirrors the governance model
from xBow-style agentic execution: only pre-approved tools/modules can run.
"""
from enum import Enum
import os
from typing import List


class AllowedTool(str, Enum):
    """V1 tool allowlist."""

    HTTPX = "httpx"
    NMAP = "nmap"
    NEUROSPLOIT = "neurosploit"


def is_tool_allowed(tool: str) -> bool:
    """Check if tool is in allowlist."""

    try:
        AllowedTool(tool)
        return True
    except ValueError:
        return False


def get_allowed_tools() -> list[str]:
    """Get list of allowed tools."""

    return [t.value for t in AllowedTool]


def get_neurosploit_allowed_modules() -> List[str]:
    """Return configured NeuroSploit modules permitted for execution.

    Modules are read from the ``NEUROSPLOIT_ALLOWED_MODULES`` environment variable
    (comma-separated). A conservative default restricts execution to safe recon
    modules only.
    """

    configured = os.getenv(
        "NEUROSPLOIT_ALLOWED_MODULES",
        "recon/portscan,recon/webscan"
    )
    return [m.strip() for m in configured.split(",") if m.strip()]

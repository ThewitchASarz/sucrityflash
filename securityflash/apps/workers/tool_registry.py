"""
Tool Registry for SecurityFlash Worker

Defines available tools, their specifications, and safety controls.
NeuroSploit-like structure with explicit tool specs and runners.
"""
from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum


class ApprovalTier(str, Enum):
    """Approval tier for tool usage."""
    A = "A"  # Auto-approve (safe reconnaissance)
    B = "B"  # Requires reviewer approval
    C = "C"  # Requires senior approval


@dataclass
class ToolSpec:
    """Tool specification with safety controls."""
    name: str
    version: str
    tier: ApprovalTier
    description: str
    allowed_args: List[str]  # Allowed argument patterns
    max_runtime_sec: int
    output_cap_kb: int
    requires_scope_validation: bool = True


# Tool Registry - SAFE RECON ONLY
TOOL_REGISTRY: Dict[str, ToolSpec] = {
    "httpx": ToolSpec(
        name="httpx",
        version="1.0.0",
        tier=ApprovalTier.A,
        description="HTTP probe for active hosts (Python httpx library)",
        allowed_args=["url", "timeout", "follow_redirects", "verify_ssl"],
        max_runtime_sec=60,
        output_cap_kb=100,
        requires_scope_validation=True
    ),
    "nmap": ToolSpec(
        name="nmap",
        version="7.94",
        tier=ApprovalTier.A,
        description="Network scanner (SAFE FLAGS ONLY: -sV -T3 --top-ports 100)",
        allowed_args=["target", "ports", "service_detection"],
        max_runtime_sec=300,  # 5 minutes max
        output_cap_kb=500,
        requires_scope_validation=True
    ),
    "subfinder": ToolSpec(
        name="subfinder",
        version="2.6.0",
        tier=ApprovalTier.A,
        description="Subdomain enumeration tool",
        allowed_args=["domain", "timeout"],
        max_runtime_sec=120,
        output_cap_kb=200,
        requires_scope_validation=True
    ),
    "dnsx": ToolSpec(
        name="dnsx",
        version="1.1.0",
        tier=ApprovalTier.A,
        description="DNS resolution and enumeration",
        allowed_args=["domain", "resolver", "record_type"],
        max_runtime_sec=60,
        output_cap_kb=100,
        requires_scope_validation=True
    ),
    "katana": ToolSpec(
        name="katana",
        version="1.0.0",
        tier=ApprovalTier.A,
        description="Web crawler for URL discovery",
        allowed_args=["url", "depth", "timeout"],
        max_runtime_sec=180,
        output_cap_kb=500,
        requires_scope_validation=True
    ),
}


def get_tool_spec(tool_name: str) -> Optional[ToolSpec]:
    """Get tool specification by name."""
    return TOOL_REGISTRY.get(tool_name)


def is_tool_allowed(tool_name: str) -> bool:
    """Check if tool is in the allowlist."""
    return tool_name in TOOL_REGISTRY


def get_allowed_tools() -> List[str]:
    """Get list of all allowed tool names."""
    return list(TOOL_REGISTRY.keys())

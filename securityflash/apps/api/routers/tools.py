"""
Tools Router - V1 API for tool catalog.

Returns allowlisted tools from tool_registry.
"""
from typing import List, Dict, Any
from fastapi import APIRouter

from apps.workers.tool_registry import TOOL_REGISTRY, ApprovalTier

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("", response_model=List[Dict[str, Any]])
def list_tools():
    """
    Get allowlisted tool catalog.

    Returns tool specifications from tool_registry including:
    - name, version, tier
    - description, allowed_args
    - max_runtime_sec, output_cap_kb
    - requires_scope_validation
    """
    tools = []

    for tool_name, tool_spec in TOOL_REGISTRY.items():
        tools.append({
            "name": tool_spec.name,
            "version": tool_spec.version,
            "tier": tool_spec.tier.value,
            "description": tool_spec.description,
            "allowed_args": tool_spec.allowed_args,
            "max_runtime_sec": tool_spec.max_runtime_sec,
            "output_cap_kb": tool_spec.output_cap_kb,
            "requires_scope_validation": tool_spec.requires_scope_validation,
            "approval_required": tool_spec.tier != ApprovalTier.A
        })

    # Sort by tier (A first) then name
    tier_order = {"A": 0, "B": 1, "C": 2}
    tools.sort(key=lambda t: (tier_order.get(t["tier"], 99), t["name"]))

    return tools

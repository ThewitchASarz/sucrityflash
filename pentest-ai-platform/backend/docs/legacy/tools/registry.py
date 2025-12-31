"""
Tool registry for mapping methods to tool implementations.
V1 MVP: Only nmap allowlisted. Experimental tools moved to tools_experimental/
"""
from typing import Optional
from tools.base import BaseTool
from tools.nmap import nmap_tool


class ToolRegistry:
    """
    Registry for V1 MVP allowlisted security tools.

    CRITICAL: Only tools in this registry can be executed.
    Adding tools requires security review and allowlist update in worker runtime.
    """

    def __init__(self):
        # V1 MVP allowlist - only basic reconnaissance
        self._tools = {
            "nmap": nmap_tool,
            # burpsuite, sqlmap, metasploit moved to tools_experimental/
            # for future V2 implementation after enhanced safety controls
        }

    def get_tool(self, method: str) -> Optional[BaseTool]:
        """Get tool by method name."""
        return self._tools.get(method.lower())

    def is_tool_available(self, method: str) -> bool:
        """Check if tool is available."""
        return method.lower() in self._tools

    def list_tools(self) -> list[str]:
        """List all available tool names."""
        return list(self._tools.keys())


# Global registry instance
tool_registry = ToolRegistry()

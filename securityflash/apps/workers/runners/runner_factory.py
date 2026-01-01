"""
Runner factory for creating tool runners.

Maps tool names to runner instances.
"""
from typing import Optional
from .base import BaseRunner
from .httpx_runner import HttpxRunner
from .nmap_runner import NmapRunner
from .subfinder_runner import SubfinderRunner


class RunnerFactory:
    """Factory for creating tool runners."""

    _runners = {
        "httpx": HttpxRunner,
        "nmap": NmapRunner,
        "subfinder": SubfinderRunner,
    }

    @classmethod
    def get_runner(cls, tool_name: str) -> Optional[BaseRunner]:
        """
        Get runner instance for tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Runner instance or None if tool not supported
        """
        runner_class = cls._runners.get(tool_name)
        if runner_class:
            return runner_class()
        return None

    @classmethod
    def is_tool_supported(cls, tool_name: str) -> bool:
        """Check if tool has a runner implementation."""
        return tool_name in cls._runners

    @classmethod
    def get_supported_tools(cls) -> list:
        """Get list of supported tool names."""
        return list(cls._runners.keys())

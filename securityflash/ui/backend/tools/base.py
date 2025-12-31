"""
Base tool interface for all mock security tools.
"""
from abc import ABC, abstractmethod
from typing import Any, Optional
from pydantic import BaseModel
from datetime import datetime
import uuid


class ToolResult(BaseModel):
    """Standardized tool execution result."""
    tool_name: str
    action_id: str
    target: str
    status: str  # "success", "failed", "error"
    output: dict  # Tool-specific output
    error: Optional[str] = None
    started_at: datetime
    completed_at: datetime
    duration_seconds: float


class BaseTool(ABC):
    """Abstract base class for all security tools."""

    def __init__(self, tool_name: str):
        self.tool_name = tool_name

    @abstractmethod
    async def execute(
        self,
        action_id: str,
        target: str,
        parameters: dict
    ) -> ToolResult:
        """
        Execute the tool with given parameters.

        Args:
            action_id: Unique action identifier
            target: Target system (IP, domain, URL)
            parameters: Tool-specific parameters

        Returns:
            ToolResult with standardized output
        """
        pass

    def _create_result(
        self,
        action_id: str,
        target: str,
        status: str,
        output: dict,
        error: Optional[str],
        started_at: datetime,
        completed_at: datetime
    ) -> ToolResult:
        """Helper to create standardized result."""
        return ToolResult(
            tool_name=self.tool_name,
            action_id=action_id,
            target=target,
            status=status,
            output=output,
            error=error,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=(completed_at - started_at).total_seconds()
        )

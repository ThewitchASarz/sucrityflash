"""
Base runner for tool execution.

Provides common interface and safety controls for all tool runners.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import hashlib
import time


@dataclass
class ToolResult:
    """Result from tool execution."""
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    artifacts: List[Dict[str, Any]]  # List of {filename, content, mime_type}
    execution_time_sec: float
    error_message: Optional[str] = None


class BaseRunner(ABC):
    """Base class for tool runners."""

    def __init__(self, tool_name: str, max_runtime_sec: int, output_cap_kb: int):
        self.tool_name = tool_name
        self.max_runtime_sec = max_runtime_sec
        self.output_cap_kb = output_cap_kb

    @abstractmethod
    def run(self, action_json: Dict[str, Any]) -> ToolResult:
        """
        Execute the tool with given arguments.

        Args:
            action_json: Action specification from ActionSpec.action_json

        Returns:
            ToolResult with stdout, stderr, artifacts, etc.
        """
        pass

    def _cap_output(self, output: str) -> str:
        """Cap output to maximum size."""
        max_bytes = self.output_cap_kb * 1024
        if len(output.encode('utf-8')) > max_bytes:
            return output[:max_bytes] + f"\n\n[OUTPUT TRUNCATED - exceeded {self.output_cap_kb}KB limit]"
        return output

    def _compute_hash(self, content: str) -> str:
        """Compute SHA256 hash of content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def _create_artifact(self, filename: str, content: str, mime_type: str = "text/plain") -> Dict[str, Any]:
        """Create artifact dictionary."""
        return {
            "filename": filename,
            "content": content,
            "mime_type": mime_type,
            "size_bytes": len(content.encode('utf-8')),
            "sha256": self._compute_hash(content)
        }

    def _validate_target_in_scope(self, target: str, scope_targets: List[str]) -> bool:
        """
        Validate that target is within scope.

        Args:
            target: Target to validate
            scope_targets: List of allowed targets from scope

        Returns:
            True if target is in scope
        """
        # Simple substring match for now
        # In production, use proper domain/IP matching logic
        for scope_target in scope_targets:
            if scope_target in target or target in scope_target:
                return True
        return False

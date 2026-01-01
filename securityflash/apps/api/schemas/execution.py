"""
Execution schemas for API requests/responses.
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from apps.api.models.execution import ExecutionStatus


class ExecutionResponse(BaseModel):
    """Execution response schema."""
    id: str
    run_id: str
    project_id: str
    scope_id: str
    action_spec_id: Optional[str]
    tool_name: str
    tool_version: Optional[str]
    status: ExecutionStatus
    started_at: datetime
    finished_at: Optional[datetime]
    exit_code: Optional[int]
    stdout_evidence_id: Optional[str]
    stderr_evidence_id: Optional[str]
    summary_json: Optional[Dict[str, Any]]
    metadata_json: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True
        use_enum_values = True

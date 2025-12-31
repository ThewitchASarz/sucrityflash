"""
Run schemas (Pydantic).
"""
from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import Optional


class RunCreate(BaseModel):
    scope_id: UUID4
    policy_version: str = "1.0.0"
    max_iterations: int = 100
    created_by: str = "system"


class RunStart(BaseModel):
    """MUST-FIX A: Explicit run start request."""
    pass  # No fields needed, just POST to trigger transition


class RunResponse(BaseModel):
    id: UUID4
    project_id: UUID4
    scope_id: UUID4
    policy_version: str
    status: str  # CREATED, RUNNING, COMPLETED, FAILED
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    iteration_count: int
    max_iterations: int
    created_at: datetime
    created_by: str

    class Config:
        from_attributes = True

"""
Pydantic schemas for run-related requests and responses.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# Request schemas
class RunCreate(BaseModel):
    """Run creation request."""
    plan_id: str = Field(..., description="Approved test plan ID")


class RunControl(BaseModel):
    """Run control request (halt, resume)."""
    reason: Optional[str] = Field(None, description="Reason for halt")


# Response schemas
class RunResponse(BaseModel):
    """Run response."""
    id: str
    plan_id: str
    status: str
    halt_reason: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    # Statistics
    total_actions: Optional[int] = None
    completed_actions: Optional[int] = None
    failed_actions: Optional[int] = None
    pending_approvals: Optional[int] = None

    class Config:
        from_attributes = True


class RunListResponse(BaseModel):
    """List of runs response."""
    runs: list[RunResponse]
    total: int

"""
Approval schemas (Pydantic).
"""
from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import Optional, List


class ApprovalRequest(BaseModel):
    approved_by: str
    reason: Optional[str] = None
    signature: str


class ApprovalResponse(BaseModel):
    id: UUID4
    action_spec_id: UUID4
    approval_tier: str
    decision: str
    approved_by: Optional[str]
    approved_at: Optional[datetime]
    reason: Optional[str]
    signature: Optional[str]
    policy_version: str
    created_at: datetime

    class Config:
        from_attributes = True


class PendingApproval(BaseModel):
    """Pending approval for reviewer queue."""
    action_id: UUID4
    run_id: UUID4
    tool: str
    target: str
    arguments: List[str]
    risk_score: float
    approval_tier: str
    proposed_by: str
    proposed_at: datetime
    justification: Optional[str]

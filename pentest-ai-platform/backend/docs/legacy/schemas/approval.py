"""
Pydantic schemas for approval-related requests and responses.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# Request schemas
class ApprovalRequest(BaseModel):
    """Approval request creation."""
    action_id: str = Field(..., description="Action ID requiring approval")
    justification: str = Field(..., description="Why this action is necessary")
    evidence_references: list[str] = Field([], description="Prior evidence IDs")


class ApprovalDecision(BaseModel):
    """Approval decision (approve or reject)."""
    signature: Optional[str] = Field(None, description="RSA-SHA256 signature (for approval)")
    notes: Optional[str] = Field(None, description="Decision notes")
    reason: Optional[str] = Field(None, description="Rejection reason (for rejection)")


# Response schemas
class ApprovalResponse(BaseModel):
    """Approval response."""
    id: str
    action_id: str
    run_id: str
    risk_level: str
    justification: str
    evidence_references: list[str]
    status: str
    requested_at: datetime
    requested_by: str
    expiry_at: datetime
    decided_at: Optional[datetime]
    decided_by: Optional[str]
    approver_signature: Optional[str]
    decision_notes: Optional[str]

    # Computed fields
    is_expired: bool
    time_remaining_minutes: Optional[int]

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_computed(cls, obj):
        """Create response with computed fields."""
        now = datetime.utcnow()
        is_expired = obj.status == "EXPIRED" or (obj.status == "PENDING" and now > obj.expiry_at)

        time_remaining = None
        if obj.status == "PENDING" and not is_expired:
            time_remaining = int((obj.expiry_at - now).total_seconds() / 60)

        return cls(
            id=str(obj.id),
            action_id=str(obj.action_id),
            run_id=str(obj.run_id),
            risk_level=obj.risk_level,
            justification=obj.justification,
            evidence_references=obj.evidence_references,
            status=obj.status,
            requested_at=obj.requested_at,
            requested_by=str(obj.requested_by),
            expiry_at=obj.expiry_at,
            decided_at=obj.decided_at,
            decided_by=str(obj.decided_by) if obj.decided_by else None,
            approver_signature=obj.approver_signature,
            decision_notes=obj.decision_notes,
            is_expired=is_expired,
            time_remaining_minutes=time_remaining
        )


class ApprovalListResponse(BaseModel):
    """List of approvals response."""
    approvals: list[ApprovalResponse]
    total: int

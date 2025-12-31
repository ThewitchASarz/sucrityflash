"""
Pydantic schemas for test plan-related requests and responses.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# Request schemas
class TestPlanGenerate(BaseModel):
    """Test plan generation request."""
    scope_id: str = Field(..., description="Scope ID (must be locked)")
    additional_instructions: Optional[str] = Field(None, description="Custom instructions for plan generation")


class TestPlanApprove(BaseModel):
    """Test plan approval request (digital signature)."""
    signature: str = Field(..., description="RSA-SHA256 signature of plan hash")


# Response schemas
class ActionResponse(BaseModel):
    """Action response."""
    id: str
    test_plan_id: str
    action_id: str
    stage: str
    description: str
    method: str
    target: str
    parameters: dict
    risk_level: str
    prerequisites: list[str]
    status: str
    executed_at: Optional[datetime]
    completed_at: Optional[datetime]
    result: Optional[dict]

    class Config:
        from_attributes = True


class TestPlanResponse(BaseModel):
    """Test plan response."""
    id: str
    scope_id: str
    stages: dict
    framework_mappings: dict
    risk_summary: dict

    # Approval information
    approved_at: Optional[datetime]
    approved_by: Optional[str]
    approver_signature: Optional[str]
    is_approved: bool

    # Timestamps
    created_at: datetime
    updated_at: datetime

    # Actions (optional, for detailed view)
    actions: Optional[list[ActionResponse]] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_approval_status(cls, obj, include_actions: bool = False):
        """Create response with computed is_approved field."""
        data = {
            "id": str(obj.id),
            "scope_id": str(obj.scope_id),
            "stages": obj.stages,
            "framework_mappings": obj.framework_mappings,
            "risk_summary": obj.risk_summary,
            "approved_at": obj.approved_at,
            "approved_by": str(obj.approved_by) if obj.approved_by else None,
            "approver_signature": obj.approver_signature,
            "is_approved": obj.approved_at is not None,
            "created_at": obj.created_at,
            "updated_at": obj.updated_at,
        }

        if include_actions:
            data["actions"] = [
                ActionResponse(
                    id=str(action.id),
                    test_plan_id=str(action.test_plan_id),
                    action_id=action.action_id,
                    stage=action.stage,
                    description=action.description,
                    method=action.method,
                    target=action.target,
                    parameters=action.parameters,
                    risk_level=action.risk_level,
                    prerequisites=action.prerequisites,
                    status=action.status,
                    executed_at=action.executed_at,
                    completed_at=action.completed_at,
                    result=action.result
                )
                for action in obj.actions
            ]

        return cls(**data)


class TestPlanListResponse(BaseModel):
    """List of test plans response."""
    test_plans: list[TestPlanResponse]
    total: int

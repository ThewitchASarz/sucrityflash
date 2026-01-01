"""
Finding schemas for API requests/responses.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from apps.api.models.finding import FindingSeverity, FindingCategory, FindingStatus


class FindingCreate(BaseModel):
    """Create finding request."""
    title: str = Field(..., min_length=1, max_length=500)
    severity: FindingSeverity
    category: FindingCategory
    affected_target: str = Field(..., min_length=1)
    description_md: str = Field(..., min_length=1)
    reproducibility_md: Optional[str] = None
    evidence_ids: Optional[List[str]] = Field(default_factory=list)
    created_by: Optional[str] = None


class FindingUpdate(BaseModel):
    """Update finding request (for DRAFT/NEEDS_REVIEW status)."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    severity: Optional[FindingSeverity] = None
    category: Optional[FindingCategory] = None
    affected_target: Optional[str] = Field(None, min_length=1)
    description_md: Optional[str] = Field(None, min_length=1)
    reproducibility_md: Optional[str] = None
    evidence_ids: Optional[List[str]] = None


class FindingResponse(BaseModel):
    """Finding response schema."""
    id: str
    run_id: str
    project_id: str
    scope_id: str
    title: str
    severity: FindingSeverity
    category: FindingCategory
    affected_target: str
    description_md: str
    reproducibility_md: Optional[str]
    evidence_ids: List[str]
    status: FindingStatus
    created_by: Optional[str]
    reviewer_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        use_enum_values = True


class FindingReview(BaseModel):
    """Finding review action request."""
    reviewer_id: str = Field(..., min_length=1)
    reason: Optional[str] = None

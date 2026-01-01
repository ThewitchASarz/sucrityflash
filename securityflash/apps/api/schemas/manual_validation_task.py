"""
ManualValidationTask schemas for API requests/responses.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from apps.api.models.manual_validation_task import ManualValidationTaskStatus


class ManualValidationTaskCreate(BaseModel):
    """Create manual validation task request."""
    title: str = Field(..., min_length=1, max_length=500)
    instructions_md: str = Field(..., min_length=1)
    required_evidence_types: Optional[List[str]] = Field(default_factory=list)
    created_by: str = Field(..., min_length=1)


class ManualValidationTaskUpdate(BaseModel):
    """Update manual validation task request."""
    status: Optional[ManualValidationTaskStatus] = None
    notes: Optional[str] = None
    completed_by: Optional[str] = None


class ManualValidationTaskAttachEvidence(BaseModel):
    """Attach evidence to manual validation task."""
    evidence_id: str = Field(..., min_length=1)


class ManualValidationTaskResponse(BaseModel):
    """Manual validation task response schema."""
    id: str
    run_id: str
    finding_id: str
    title: str
    instructions_md: str
    required_evidence_types: List[str]
    status: ManualValidationTaskStatus
    created_by: str
    completed_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    evidence_ids: List[str]
    notes: Optional[str]

    class Config:
        from_attributes = True
        use_enum_values = True

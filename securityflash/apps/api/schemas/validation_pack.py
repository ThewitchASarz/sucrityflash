"""ValidationPack Pydantic schemas."""
from pydantic import BaseModel, UUID4
from typing import Optional, List, Dict, Any
from datetime import datetime


class ValidationPackCreate(BaseModel):
    """Create ValidationPack request."""
    finding_id: Optional[UUID4] = None
    action_spec_id: Optional[UUID4] = None
    title: str
    category: str
    risk_level: str
    instructions_md: str
    command_templates: Optional[List[Dict[str, str]]] = None
    required_evidence_types: Optional[List[str]] = None
    evidence_checklist_md: Optional[str] = None
    target_must_match_scope: bool = True
    rate_limit_seconds: Optional[Dict[str, int]] = None
    safety_notes: Optional[str] = None
    created_by: str


class ValidationPackUpdate(BaseModel):
    """Update ValidationPack."""
    completed_by: str
    execution_notes: Optional[str] = None


class AttachEvidenceRequest(BaseModel):
    """Attach evidence to ValidationPack."""
    evidence_ids: List[str]


class ValidationPackResponse(BaseModel):
    """ValidationPack response."""
    id: UUID4
    run_id: UUID4
    finding_id: Optional[UUID4]
    action_spec_id: Optional[UUID4]
    title: str
    category: str
    risk_level: str
    instructions_md: str
    command_templates: Optional[List[Dict[str, str]]]
    required_evidence_types: Optional[List[str]]
    evidence_checklist_md: Optional[str]
    target_must_match_scope: bool
    rate_limit_seconds: Optional[Dict[str, int]]
    safety_notes: Optional[str]
    status: str
    created_by: str
    approved_by: Optional[str]
    assigned_to: Optional[str]
    completed_by: Optional[str]
    created_at: datetime
    approved_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    updated_at: datetime
    evidence_ids: Optional[List[str]]
    execution_notes: Optional[str]

    class Config:
        from_attributes = True

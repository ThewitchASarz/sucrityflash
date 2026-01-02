"""
Pydantic schemas for Validation Packs.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, UUID4, Field
from datetime import datetime
from apps.api.models.validation_pack import ValidationRiskLevel, ValidationStatus


class CommandTemplate(BaseModel):
    label: str
    command: str
    params_schema: Dict[str, Any] = Field(default_factory=dict)
    safety_notes: Optional[str] = None


class ValidationPackCreate(BaseModel):
    title: str
    risk_level: ValidationRiskLevel
    instructions_md: str
    command_templates: List[CommandTemplate]
    stop_conditions: List[str]
    required_evidence: List[str]
    finding_id: Optional[UUID4] = None
    created_by: str


class ValidationPackSubmit(BaseModel):
    actor: str


class ValidationPackApproval(BaseModel):
    approver: str


class ValidationPackAttachEvidence(BaseModel):
    evidence_id: UUID4
    actor: str


class ValidationPackAbort(BaseModel):
    actor: str
    reason: str


class ValidationPackResponse(BaseModel):
    id: UUID4
    run_id: UUID4
    project_id: UUID4
    scope_id: UUID4
    finding_id: Optional[UUID4]
    title: str
    risk_level: ValidationRiskLevel
    instructions_md: str
    command_templates: List[CommandTemplate]
    stop_conditions: List[str]
    required_evidence: List[str]
    status: ValidationStatus
    approved_by_reviewer: Optional[str]
    approved_by_engineer: Optional[str]
    created_by: str
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    abort_reason: Optional[str]

    class Config:
        from_attributes = True

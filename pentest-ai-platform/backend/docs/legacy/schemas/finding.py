"""
Pydantic schemas for finding-related requests and responses.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# Request schemas
class TriageRequest(BaseModel):
    """Triage request."""
    evidence_ids: list[str] = Field(..., description="Evidence IDs to analyze")


# Response schemas
class FindingResponse(BaseModel):
    """Finding response."""
    id: str
    run_id: str
    title: str
    description: str
    severity: str
    cvss_score: float
    cvss_vector: str
    exploitability: str
    evidence_ids: list[str]
    affected_systems: list[str]
    owasp_mappings: list[str]
    nist_mappings: list[str]
    mitre_mappings: list[str]
    remediation: list[str]
    references: list[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_model(cls, obj):
        """Create response from ORM model."""
        return cls(
            id=str(obj.id),
            run_id=str(obj.run_id),
            title=obj.title,
            description=obj.description,
            severity=obj.severity,
            cvss_score=obj.cvss_score,
            cvss_vector=obj.cvss_vector,
            exploitability=obj.exploitability,
            evidence_ids=obj.evidence_ids,
            affected_systems=obj.affected_systems,
            owasp_mappings=obj.owasp_mappings,
            nist_mappings=obj.nist_mappings,
            mitre_mappings=obj.mitre_mappings,
            remediation=obj.remediation,
            references=obj.references,
            created_at=obj.created_at,
            updated_at=obj.updated_at
        )


class FindingListResponse(BaseModel):
    """List of findings response."""
    findings: list[FindingResponse]
    total: int


class FindingSummaryResponse(BaseModel):
    """Finding summary statistics."""
    run_id: str
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    info_count: int
    avg_cvss_score: float
    top_owasp: list[str]
    top_mitre: list[str]

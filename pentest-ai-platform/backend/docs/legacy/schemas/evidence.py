"""
Pydantic schemas for evidence-related requests and responses.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# Response schemas
class EvidenceResponse(BaseModel):
    """Evidence response."""
    id: str
    run_id: str
    action_id: str
    evidence_type: str
    content_hash: str
    prior_evidence_hash: Optional[str]
    s3_path: str
    metadata: dict
    created_by_actor_type: str
    created_by_actor_id: str
    signature: Optional[str]
    created_at: datetime

    # Computed
    has_prior: bool

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_computed(cls, obj):
        """Create response with computed fields."""
        return cls(
            id=str(obj.id),
            run_id=str(obj.run_id),
            action_id=obj.action_id,
            evidence_type=obj.evidence_type,
            content_hash=obj.content_hash,
            prior_evidence_hash=obj.prior_evidence_hash,
            s3_path=obj.s3_path,
            metadata=obj.metadata,
            created_by_actor_type=obj.created_by_actor_type,
            created_by_actor_id=str(obj.created_by_actor_id),
            signature=obj.signature,
            created_at=obj.created_at,
            has_prior=obj.prior_evidence_hash is not None
        )


class EvidenceWithContent(EvidenceResponse):
    """Evidence response with content."""
    content: dict


class EvidenceListResponse(BaseModel):
    """List of evidence response."""
    evidence: list[EvidenceResponse]
    total: int


class ChainVerificationResponse(BaseModel):
    """Evidence chain verification response."""
    run_id: str
    is_valid: bool
    error: Optional[str]
    evidence_count: int
    verified_at: datetime

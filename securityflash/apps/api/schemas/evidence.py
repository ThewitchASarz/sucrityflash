"""
Evidence schemas (Pydantic).
"""
from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import Dict, Any


class EvidenceCreate(BaseModel):
    evidence_type: str
    artifact_uri: str
    artifact_hash: str
    generated_by: str
    metadata: Dict[str, Any]


class EvidenceResponse(BaseModel):
    id: UUID4
    run_id: UUID4
    evidence_type: str
    artifact_uri: str
    artifact_hash: str
    generated_by: str
    generated_at: datetime
    validation_status: str
    evidence_metadata: Dict[str, Any]  # Renamed from 'metadata' to avoid SQLAlchemy conflict
    created_at: datetime

    class Config:
        from_attributes = True

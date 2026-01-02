"""
Evidence endpoints.

MUST-FIX C: DELETE endpoint ALWAYS returns 403.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List
from apps.api.db.session import get_db
from apps.api.models.evidence import Evidence
from apps.api.schemas.evidence import EvidenceCreate, EvidenceResponse
from apps.api.services.evidence_service import EvidenceService
from apps.api.services.audit_service import audit_log
from apps.api.core.security import block_evidence_delete, get_current_user

router = APIRouter(prefix="/api/v1/runs/{run_id}/evidence", tags=["evidence"])


@router.post("", response_model=EvidenceResponse, status_code=201)
def create_evidence(
    run_id: str,
    evidence_data: EvidenceCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Worker creates evidence after tool execution.

    Evidence is immutable once created.
    """
    evidence = EvidenceService.create(
        db=db,
        run_id=run_id,
        evidence_type=evidence_data.evidence_type,
        artifact_uri=evidence_data.artifact_uri,
        artifact_hash=evidence_data.artifact_hash,
        generated_by=evidence_data.generated_by,
        evidence_metadata=evidence_data.metadata
    )

    # Audit log
    audit_log(
        db=db,
        run_id=run_id,
        event_type="EVIDENCE_STORED",
        actor=evidence_data.generated_by,
        details={
            "evidence_id": str(evidence.id),
            "evidence_type": evidence_data.evidence_type,
            "artifact_hash": evidence_data.artifact_hash,
            "tool_used": evidence_data.metadata.get("tool_used")
        }
    )

    return evidence


@router.get("/{evidence_id}", response_model=EvidenceResponse)
def get_evidence(run_id: str, evidence_id: str, db: Session = Depends(get_db)):
    """Get evidence by ID."""
    evidence = EvidenceService.get(db=db, evidence_id=evidence_id)

    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")

    if str(evidence.run_id) != run_id:
        raise HTTPException(status_code=404, detail="Evidence not found for this run")

    return evidence


@router.get("", response_model=List[EvidenceResponse])
def list_evidence(run_id: str, db: Session = Depends(get_db)):
    """List all evidence for a run."""
    return EvidenceService.list_by_run(db=db, run_id=run_id)


@router.get("/{evidence_id}/download")
def download_evidence(run_id: str, evidence_id: str, db: Session = Depends(get_db)):
    """
    Get presigned download URL for evidence artifact.

    For REPORT type evidence, returns content directly.
    For other evidence, returns presigned MinIO URL.
    """
    from fastapi.responses import Response

    evidence = EvidenceService.get(db=db, evidence_id=evidence_id)

    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")

    if str(evidence.run_id) != run_id:
        raise HTTPException(status_code=404, detail="Evidence not found for this run")

    # Special handling for REPORT type - content stored in metadata
    if evidence.evidence_type == "REPORT":
        content = evidence.evidence_metadata.get("content")
        mime_type = evidence.evidence_metadata.get("mime_type", "text/html")
        filename = evidence.evidence_metadata.get("filename", f"report_{evidence_id[:8]}.html")

        if not content:
            raise HTTPException(status_code=404, detail="Report content not found")

        return Response(
            content=content.encode('utf-8'),
            media_type=mime_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    # For other evidence types, generate presigned URL from MinIO
    from apps.api.services.evidence_service import get_download_url
    download_url = get_download_url(evidence.artifact_uri)

    return {
        "evidence_id": str(evidence.id),
        "artifact_uri": evidence.artifact_uri,
        "download_url": download_url,
        "artifact_hash": evidence.artifact_hash,
        "expires_in_seconds": 3600
    }


@router.delete("/{evidence_id}")
def delete_evidence(run_id: str, evidence_id: str):
    """
    MUST-FIX C: Evidence deletion is ALWAYS blocked.

    This is layer 1 of 3-layer enforcement:
    - Layer 1: API returns 403 (this endpoint)
    - Layer 2: No delete() method in EvidenceService
    - Layer 3: MinIO bucket policy denies delete operations

    Raises:
        HTTPException(403): Always
    """
    block_evidence_delete()

"""
ValidationPack API endpoints - Phase 2/3

High-risk validation procedures requiring human execution.
NO AUTONOMOUS EXPLOITATION.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from datetime import datetime

from apps.api.db.session import get_db
from apps.api.models.validation_pack import ValidationPack, ValidationPackStatus
from apps.api.models.run import Run
from apps.api.schemas.validation_pack import (
    ValidationPackCreate,
    ValidationPackResponse,
    ValidationPackUpdate,
    AttachEvidenceRequest
)

router = APIRouter(prefix="/api/v1/runs/{run_id}/validation-packs", tags=["validation-packs"])


@router.post("", response_model=ValidationPackResponse, status_code=201)
def create_validation_pack(
    run_id: UUID,
    pack_data: ValidationPackCreate,
    db: Session = Depends(get_db)
):
    """
    Create a ValidationPack from an approved high-risk ActionSpec.

    CRITICAL: ValidationPacks are HUMAN-ONLY. Worker must refuse execution.
    """
    # Verify run exists
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Create ValidationPack
    pack = ValidationPack(
        run_id=run_id,
        finding_id=pack_data.finding_id,
        action_spec_id=pack_data.action_spec_id,
        title=pack_data.title,
        category=pack_data.category,
        risk_level=pack_data.risk_level,
        instructions_md=pack_data.instructions_md,
        command_templates=pack_data.command_templates,
        required_evidence_types=pack_data.required_evidence_types,
        evidence_checklist_md=pack_data.evidence_checklist_md,
        target_must_match_scope=pack_data.target_must_match_scope,
        rate_limit_seconds=pack_data.rate_limit_seconds,
        safety_notes=pack_data.safety_notes,
        created_by=pack_data.created_by,
        status=ValidationPackStatus.PENDING_APPROVAL,
    )

    db.add(pack)
    db.commit()
    db.refresh(pack)

    return pack


@router.get("", response_model=List[ValidationPackResponse])
def list_validation_packs(
    run_id: UUID,
    status: Optional[ValidationPackStatus] = None,
    db: Session = Depends(get_db)
):
    """List all ValidationPacks for a run."""
    query = db.query(ValidationPack).filter(ValidationPack.run_id == run_id)

    if status:
        query = query.filter(ValidationPack.status == status)

    packs = query.order_by(ValidationPack.created_at.desc()).all()
    return packs


@router.get("/{pack_id}", response_model=ValidationPackResponse)
def get_validation_pack(
    run_id: UUID,
    pack_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a specific ValidationPack."""
    pack = db.query(ValidationPack).filter(
        ValidationPack.id == pack_id,
        ValidationPack.run_id == run_id
    ).first()

    if not pack:
        raise HTTPException(status_code=404, detail="ValidationPack not found")

    return pack


@router.post("/{pack_id}/attach-evidence", response_model=ValidationPackResponse)
def attach_evidence(
    run_id: UUID,
    pack_id: UUID,
    evidence_req: AttachEvidenceRequest,
    db: Session = Depends(get_db)
):
    """Attach evidence to a ValidationPack."""
    pack = db.query(ValidationPack).filter(
        ValidationPack.id == pack_id,
        ValidationPack.run_id == run_id
    ).first()

    if not pack:
        raise HTTPException(status_code=404, detail="ValidationPack not found")

    # Add evidence IDs
    current_evidence = pack.evidence_ids or []
    pack.evidence_ids = list(set(current_evidence + evidence_req.evidence_ids))

    db.commit()
    db.refresh(pack)

    return pack


@router.post("/{pack_id}/complete", response_model=ValidationPackResponse)
def complete_validation_pack(
    run_id: UUID,
    pack_id: UUID,
    completion_data: ValidationPackUpdate,
    db: Session = Depends(get_db)
):
    """Mark a ValidationPack as complete."""
    pack = db.query(ValidationPack).filter(
        ValidationPack.id == pack_id,
        ValidationPack.run_id == run_id
    ).first()

    if not pack:
        raise HTTPException(status_code=404, detail="ValidationPack not found")

    if pack.status != ValidationPackStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot complete pack in status {pack.status.value}"
        )

    pack.status = ValidationPackStatus.COMPLETE
    pack.completed_by = completion_data.completed_by
    pack.completed_at = datetime.utcnow()
    pack.execution_notes = completion_data.execution_notes

    db.commit()
    db.refresh(pack)

    return pack

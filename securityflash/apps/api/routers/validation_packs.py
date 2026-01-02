"""
Validation Pack endpoints - manual execution workflow.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from apps.api.db.session import get_db
from apps.api.models.run import Run
from apps.api.models.validation_pack import ValidationPack, ValidationStatus, ValidationRiskLevel
from apps.api.models.evidence import Evidence
from apps.api.schemas.validation_pack import (
    ValidationPackCreate,
    ValidationPackResponse,
    ValidationPackSubmit,
    ValidationPackApproval,
    ValidationPackAttachEvidence,
    ValidationPackAbort,
)
from apps.api.services.audit_service import audit_log

router = APIRouter(prefix="/api/v1", tags=["validation_packs"])


def _get_pack_or_404(pack_id: str, db: Session) -> ValidationPack:
    pack = db.query(ValidationPack).filter(ValidationPack.id == pack_id).first()
    if not pack:
        raise HTTPException(status_code=404, detail="Validation pack not found")
    return pack


@router.post("/runs/{run_id}/validation-packs", response_model=ValidationPackResponse, status_code=201)
def create_validation_pack(run_id: str, payload: ValidationPackCreate, db: Session = Depends(get_db)):
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    pack = ValidationPack(
        run_id=run.id,
        project_id=run.project_id,
        scope_id=run.scope_id,
        finding_id=payload.finding_id,
        title=payload.title,
        risk_level=payload.risk_level,
        instructions_md=payload.instructions_md,
        command_templates=[ct.model_dump() for ct in payload.command_templates],
        stop_conditions=payload.stop_conditions,
        required_evidence=payload.required_evidence,
        status=ValidationStatus.DRAFT,
        created_by=payload.created_by
    )

    db.add(pack)
    db.commit()
    db.refresh(pack)

    audit_log(
        db=db,
        run_id=run.id,
        event_type="VALIDATION_PACK_CREATED",
        actor=payload.created_by,
        details={"pack_id": str(pack.id), "status": pack.status.value, "risk_level": pack.risk_level.value}
    )
    return pack


@router.get("/runs/{run_id}/validation-packs", response_model=List[ValidationPackResponse])
def list_validation_packs(run_id: str, db: Session = Depends(get_db)):
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return db.query(ValidationPack).filter(ValidationPack.run_id == run_id).order_by(ValidationPack.created_at.asc()).all()


@router.get("/validation-packs/{pack_id}", response_model=ValidationPackResponse)
def get_validation_pack(pack_id: str, db: Session = Depends(get_db)):
    pack = _get_pack_or_404(pack_id, db)
    return pack


@router.post("/validation-packs/{pack_id}/submit", response_model=ValidationPackResponse)
def submit_validation_pack(pack_id: str, payload: ValidationPackSubmit, db: Session = Depends(get_db)):
    pack = _get_pack_or_404(pack_id, db)
    if pack.status != ValidationStatus.DRAFT:
        raise HTTPException(status_code=400, detail=f"Pack must be DRAFT to submit (current: {pack.status.value})")

    pack.status = ValidationStatus.READY
    pack.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(pack)

    audit_log(
        db=db,
        run_id=pack.run_id,
        event_type="VALIDATION_PACK_SUBMITTED",
        actor=payload.actor,
        details={"pack_id": str(pack.id), "status": pack.status.value}
    )
    return pack


@router.post("/validation-packs/{pack_id}/approve/reviewer", response_model=ValidationPackResponse)
def approve_validation_pack_reviewer(pack_id: str, payload: ValidationPackApproval, db: Session = Depends(get_db)):
    pack = _get_pack_or_404(pack_id, db)
    if pack.status not in [ValidationStatus.READY, ValidationStatus.DRAFT]:
        raise HTTPException(status_code=400, detail=f"Pack must be READY or DRAFT to approve (current: {pack.status.value})")

    pack.approved_by_reviewer = payload.approver
    pack.updated_at = datetime.utcnow()

    # Risk enforcement: HIGH requires engineer approval before IN_PROGRESS
    if pack.status == ValidationStatus.DRAFT:
        pack.status = ValidationStatus.READY
    if pack.risk_level != ValidationRiskLevel.HIGH:
        pack.status = ValidationStatus.IN_PROGRESS
        pack.completed_at = None

    db.commit()
    db.refresh(pack)

    audit_log(
        db=db,
        run_id=pack.run_id,
        event_type="VALIDATION_PACK_APPROVED_REVIEWER",
        actor=payload.approver,
        details={"pack_id": str(pack.id), "status": pack.status.value, "risk_level": pack.risk_level.value}
    )
    return pack


@router.post("/validation-packs/{pack_id}/approve/engineer", response_model=ValidationPackResponse)
def approve_validation_pack_engineer(pack_id: str, payload: ValidationPackApproval, db: Session = Depends(get_db)):
    pack = _get_pack_or_404(pack_id, db)
    if not pack.approved_by_reviewer:
        raise HTTPException(status_code=400, detail="Reviewer approval required before engineer approval")

    if pack.status == ValidationStatus.COMPLETE or pack.status == ValidationStatus.ABORTED:
        raise HTTPException(status_code=400, detail=f"Pack is {pack.status.value} and cannot be approved")

    pack.approved_by_engineer = payload.approver
    pack.updated_at = datetime.utcnow()

    # Transition to IN_PROGRESS once both approvals are present
    if pack.status != ValidationStatus.IN_PROGRESS:
        pack.status = ValidationStatus.IN_PROGRESS
        pack.completed_at = None

    db.commit()
    db.refresh(pack)

    audit_log(
        db=db,
        run_id=pack.run_id,
        event_type="VALIDATION_PACK_APPROVED_ENGINEER",
        actor=payload.approver,
        details={"pack_id": str(pack.id), "status": pack.status.value}
    )
    return pack


@router.post("/validation-packs/{pack_id}/attach-evidence", response_model=ValidationPackResponse)
def attach_evidence(pack_id: str, payload: ValidationPackAttachEvidence, db: Session = Depends(get_db)):
    pack = _get_pack_or_404(pack_id, db)
    if pack.status in [ValidationStatus.COMPLETE, ValidationStatus.ABORTED]:
        raise HTTPException(status_code=400, detail=f"Cannot attach evidence to a {pack.status.value} pack")
    evidence = db.query(Evidence).filter(Evidence.id == payload.evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    if str(evidence.run_id) != str(pack.run_id):
        raise HTTPException(status_code=400, detail="Evidence must belong to the same run")

    evidence.validation_pack_id = pack.id
    pack.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(pack)

    audit_log(
        db=db,
        run_id=pack.run_id,
        event_type="VALIDATION_PACK_EVIDENCE_ATTACHED",
        actor=payload.actor,
        details={"pack_id": str(pack.id), "evidence_id": str(evidence.id)}
    )
    return pack


@router.post("/validation-packs/{pack_id}/complete", response_model=ValidationPackResponse)
def complete_validation_pack(pack_id: str, payload: ValidationPackSubmit, db: Session = Depends(get_db)):
    pack = _get_pack_or_404(pack_id, db)
    if pack.status != ValidationStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail=f"Pack must be IN_PROGRESS to complete (current: {pack.status.value})")

    evidence_count = db.query(Evidence).filter(Evidence.validation_pack_id == pack.id).count()
    if evidence_count == 0:
        raise HTTPException(status_code=400, detail="At least one evidence item is required to complete the pack")

    pack.status = ValidationStatus.COMPLETE
    pack.completed_at = datetime.utcnow()
    pack.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(pack)

    audit_log(
        db=db,
        run_id=pack.run_id,
        event_type="VALIDATION_PACK_COMPLETED",
        actor=payload.actor,
        details={"pack_id": str(pack.id), "evidence_count": evidence_count}
    )
    return pack


@router.post("/validation-packs/{pack_id}/abort", response_model=ValidationPackResponse)
def abort_validation_pack(pack_id: str, payload: ValidationPackAbort, db: Session = Depends(get_db)):
    pack = _get_pack_or_404(pack_id, db)
    if pack.status == ValidationStatus.COMPLETE:
        raise HTTPException(status_code=400, detail="Cannot abort a completed pack")

    pack.status = ValidationStatus.ABORTED
    pack.abort_reason = payload.reason
    pack.completed_at = datetime.utcnow()
    pack.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(pack)

    audit_log(
        db=db,
        run_id=pack.run_id,
        event_type="VALIDATION_PACK_ABORTED",
        actor=payload.actor,
        details={"pack_id": str(pack.id), "reason": payload.reason}
    )
    return pack


@router.post("/findings/{finding_id}/validation-pack", response_model=ValidationPackResponse, status_code=201)
def create_validation_pack_for_finding(finding_id: str, payload: ValidationPackCreate, db: Session = Depends(get_db)):
    from apps.api.models.finding import Finding
    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    if str(finding.id) != str(payload.finding_id or finding_id):
        payload.finding_id = finding.id

    run = db.query(Run).filter(Run.id == finding.run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found for finding")

    pack = ValidationPack(
        run_id=run.id,
        project_id=run.project_id,
        scope_id=run.scope_id,
        finding_id=finding.id,
        title=payload.title,
        risk_level=payload.risk_level,
        instructions_md=payload.instructions_md,
        command_templates=[ct.model_dump() for ct in payload.command_templates],
        stop_conditions=payload.stop_conditions,
        required_evidence=payload.required_evidence,
        status=ValidationStatus.DRAFT,
        created_by=payload.created_by
    )
    db.add(pack)
    db.commit()
    db.refresh(pack)

    audit_log(
        db=db,
        run_id=run.id,
        event_type="VALIDATION_PACK_CREATED_FROM_FINDING",
        actor=payload.created_by,
        details={"pack_id": str(pack.id), "finding_id": str(finding.id)}
    )
    return pack

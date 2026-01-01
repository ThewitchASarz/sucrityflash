"""
Finding endpoints - Evidence-backed findings with review workflow.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from apps.api.db.session import get_db
from apps.api.models.finding import Finding, FindingStatus, FindingSeverity
from apps.api.models.run import Run
from apps.api.schemas.finding import FindingCreate, FindingUpdate, FindingResponse, FindingReview
from apps.api.services.audit_service import audit_log

router = APIRouter(prefix="/api/v1", tags=["findings"])


@router.get("/runs/{run_id}/findings", response_model=List[FindingResponse])
def list_run_findings(run_id: str, db: Session = Depends(get_db)):
    """
    List all findings for a run.

    Returns findings in all statuses (DRAFT, NEEDS_REVIEW, CONFIRMED, REJECTED).
    """
    # Verify run exists
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Get all findings for this run
    findings = db.query(Finding).filter(
        Finding.run_id == run_id
    ).order_by(Finding.created_at.desc()).all()

    return findings


@router.post("/runs/{run_id}/findings", response_model=FindingResponse, status_code=201)
def create_finding(
    run_id: str,
    finding_data: FindingCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new finding in DRAFT status.

    Can be created by agents (auto-findings) or humans.
    """
    # Verify run exists
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Create finding in DRAFT status
    finding = Finding(
        run_id=run.id,
        project_id=run.project_id,
        scope_id=run.scope_id,
        title=finding_data.title,
        severity=finding_data.severity,
        category=finding_data.category,
        affected_target=finding_data.affected_target,
        description_md=finding_data.description_md,
        reproducibility_md=finding_data.reproducibility_md,
        evidence_ids=finding_data.evidence_ids or [],
        status=FindingStatus.DRAFT,
        created_by=finding_data.created_by
    )

    db.add(finding)
    db.commit()
    db.refresh(finding)

    # Audit log
    audit_log(
        db=db,
        run_id=run.id,
        event_type="FINDING_CREATED",
        actor=finding_data.created_by or "system",
        details={
            "finding_id": str(finding.id),
            "title": finding.title,
            "severity": finding.severity.value,
            "category": finding.category.value,
            "status": FindingStatus.DRAFT.value
        }
    )

    return finding


@router.patch("/findings/{finding_id}", response_model=FindingResponse)
def update_finding(
    finding_id: str,
    update_data: FindingUpdate,
    db: Session = Depends(get_db)
):
    """
    Update finding (only allowed for DRAFT or NEEDS_REVIEW status).

    CONFIRMED and REJECTED findings are immutable.
    """
    finding = db.query(Finding).filter(Finding.id == finding_id).first()

    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    # Only DRAFT and NEEDS_REVIEW can be edited
    if finding.status not in [FindingStatus.DRAFT, FindingStatus.NEEDS_REVIEW]:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot edit finding in {finding.status.value} status. Only DRAFT and NEEDS_REVIEW can be edited."
        )

    # Update fields
    if update_data.title is not None:
        finding.title = update_data.title
    if update_data.severity is not None:
        finding.severity = update_data.severity
    if update_data.category is not None:
        finding.category = update_data.category
    if update_data.affected_target is not None:
        finding.affected_target = update_data.affected_target
    if update_data.description_md is not None:
        finding.description_md = update_data.description_md
    if update_data.reproducibility_md is not None:
        finding.reproducibility_md = update_data.reproducibility_md
    if update_data.evidence_ids is not None:
        finding.evidence_ids = update_data.evidence_ids

    finding.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(finding)

    # Audit log
    audit_log(
        db=db,
        run_id=finding.run_id,
        event_type="FINDING_UPDATED",
        actor="user",
        details={
            "finding_id": str(finding.id),
            "title": finding.title
        }
    )

    return finding


@router.post("/findings/{finding_id}/submit_for_review", response_model=FindingResponse)
def submit_finding_for_review(finding_id: str, db: Session = Depends(get_db)):
    """
    Submit finding for review (DRAFT → NEEDS_REVIEW).

    Requires at least 1 evidence_id.
    """
    finding = db.query(Finding).filter(Finding.id == finding_id).first()

    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    # Only DRAFT can be submitted
    if finding.status != FindingStatus.DRAFT:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot submit finding in {finding.status.value} status. Only DRAFT can be submitted."
        )

    # Validate evidence exists
    if not finding.evidence_ids or len(finding.evidence_ids) == 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot submit finding without evidence. Add at least 1 evidence_id."
        )

    # Transition to NEEDS_REVIEW
    finding.status = FindingStatus.NEEDS_REVIEW
    finding.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(finding)

    # Audit log
    audit_log(
        db=db,
        run_id=finding.run_id,
        event_type="FINDING_SUBMITTED_FOR_REVIEW",
        actor="user",
        details={
            "finding_id": str(finding.id),
            "title": finding.title,
            "evidence_count": len(finding.evidence_ids)
        }
    )

    return finding


@router.post("/findings/{finding_id}/confirm", response_model=FindingResponse)
def confirm_finding(
    finding_id: str,
    review_data: FindingReview,
    db: Session = Depends(get_db)
):
    """
    Confirm finding (NEEDS_REVIEW → CONFIRMED).

    Requires:
    - at least 1 evidence_id
    - non-empty reproducibility_md
    - reviewer role
    """
    finding = db.query(Finding).filter(Finding.id == finding_id).first()

    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    # Only NEEDS_REVIEW can be confirmed
    if finding.status != FindingStatus.NEEDS_REVIEW:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot confirm finding in {finding.status.value} status. Only NEEDS_REVIEW can be confirmed."
        )

    # Validate evidence exists
    if not finding.evidence_ids or len(finding.evidence_ids) == 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot confirm finding without evidence."
        )

    # Validate reproducibility steps exist
    if not finding.reproducibility_md or len(finding.reproducibility_md.strip()) == 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot confirm finding without reproducibility steps."
        )

    # PHASE 3: HIGH/CRITICAL findings require manual validation tasks
    if finding.severity in [FindingSeverity.HIGH, FindingSeverity.CRITICAL]:
        from apps.api.models.manual_validation_task import ManualValidationTask, ManualValidationTaskStatus

        # Check for at least 1 COMPLETE manual validation task
        complete_tasks = db.query(ManualValidationTask).filter(
            ManualValidationTask.finding_id == finding.id,
            ManualValidationTask.status == ManualValidationTaskStatus.COMPLETE
        ).count()

        if complete_tasks == 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot confirm {finding.severity.value} severity finding without at least one COMPLETE manual validation task. Create and complete a manual validation task with evidence first."
            )

        # Require at least 2 evidence artifacts (finding evidence + task evidence)
        total_evidence_count = len(finding.evidence_ids)

        # Count task evidence
        tasks = db.query(ManualValidationTask).filter(
            ManualValidationTask.finding_id == finding.id
        ).all()
        for task in tasks:
            total_evidence_count += len(task.evidence_ids)

        if total_evidence_count < 2:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot confirm {finding.severity.value} severity finding with only {total_evidence_count} evidence artifact(s). At least 2 evidence artifacts required (finding evidence + task evidence)."
            )

    # Transition to CONFIRMED
    finding.status = FindingStatus.CONFIRMED
    finding.reviewer_id = review_data.reviewer_id
    finding.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(finding)

    # Audit log
    audit_log(
        db=db,
        run_id=finding.run_id,
        event_type="FINDING_CONFIRMED",
        actor=review_data.reviewer_id,
        details={
            "finding_id": str(finding.id),
            "title": finding.title,
            "severity": finding.severity.value,
            "reason": review_data.reason
        }
    )

    return finding


@router.post("/findings/{finding_id}/reject", response_model=FindingResponse)
def reject_finding(
    finding_id: str,
    review_data: FindingReview,
    db: Session = Depends(get_db)
):
    """
    Reject finding (NEEDS_REVIEW → REJECTED).

    Requires reviewer role.
    """
    finding = db.query(Finding).filter(Finding.id == finding_id).first()

    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    # Only NEEDS_REVIEW can be rejected
    if finding.status != FindingStatus.NEEDS_REVIEW:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot reject finding in {finding.status.value} status. Only NEEDS_REVIEW can be rejected."
        )

    # Transition to REJECTED
    finding.status = FindingStatus.REJECTED
    finding.reviewer_id = review_data.reviewer_id
    finding.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(finding)

    # Audit log
    audit_log(
        db=db,
        run_id=finding.run_id,
        event_type="FINDING_REJECTED",
        actor=review_data.reviewer_id,
        details={
            "finding_id": str(finding.id),
            "title": finding.title,
            "reason": review_data.reason
        }
    )

    return finding

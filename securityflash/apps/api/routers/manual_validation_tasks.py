"""
Manual Validation Task endpoints - Human-executed validation with evidence.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from apps.api.db.session import get_db
from apps.api.models.manual_validation_task import ManualValidationTask, ManualValidationTaskStatus
from apps.api.models.finding import Finding
from apps.api.models.evidence import Evidence
from apps.api.schemas.manual_validation_task import (
    ManualValidationTaskCreate,
    ManualValidationTaskUpdate,
    ManualValidationTaskAttachEvidence,
    ManualValidationTaskResponse
)
from apps.api.services.audit_service import audit_log

router = APIRouter(prefix="/api/v1", tags=["manual_validation_tasks"])


@router.post("/findings/{finding_id}/manual-tasks", response_model=ManualValidationTaskResponse, status_code=201)
def create_manual_task(
    finding_id: str,
    task_data: ManualValidationTaskCreate,
    db: Session = Depends(get_db)
):
    """
    Create a manual validation task for a finding.

    Used for HIGH/CRITICAL findings requiring human validation.
    """
    # Verify finding exists
    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    # Create manual validation task
    task = ManualValidationTask(
        run_id=finding.run_id,
        finding_id=finding.id,
        title=task_data.title,
        instructions_md=task_data.instructions_md,
        required_evidence_types=task_data.required_evidence_types or [],
        status=ManualValidationTaskStatus.OPEN,
        created_by=task_data.created_by,
        evidence_ids=[]
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    # Audit log
    audit_log(
        db=db,
        run_id=finding.run_id,
        event_type="MANUAL_TASK_CREATED",
        actor=task_data.created_by,
        details={
            "task_id": str(task.id),
            "finding_id": str(finding.id),
            "title": task.title,
            "severity": finding.severity.value
        }
    )

    return task


@router.get("/findings/{finding_id}/manual-tasks", response_model=List[ManualValidationTaskResponse])
def list_finding_tasks(finding_id: str, db: Session = Depends(get_db)):
    """
    List all manual validation tasks for a finding.
    """
    # Verify finding exists
    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    # Get all tasks for this finding
    tasks = db.query(ManualValidationTask).filter(
        ManualValidationTask.finding_id == finding_id
    ).order_by(ManualValidationTask.created_at.desc()).all()

    return tasks


@router.get("/manual-tasks/{task_id}", response_model=ManualValidationTaskResponse)
def get_manual_task(task_id: str, db: Session = Depends(get_db)):
    """
    Get manual validation task by ID.
    """
    task = db.query(ManualValidationTask).filter(ManualValidationTask.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Manual validation task not found")

    return task


@router.patch("/manual-tasks/{task_id}", response_model=ManualValidationTaskResponse)
def update_manual_task(
    task_id: str,
    update_data: ManualValidationTaskUpdate,
    db: Session = Depends(get_db)
):
    """
    Update manual validation task.

    Only OPEN/IN_PROGRESS tasks can be edited.
    """
    task = db.query(ManualValidationTask).filter(ManualValidationTask.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Manual validation task not found")

    # Only OPEN and IN_PROGRESS can be edited
    if task.status == ManualValidationTaskStatus.COMPLETE:
        raise HTTPException(
            status_code=409,
            detail="Cannot edit COMPLETE task. Task is immutable once completed."
        )

    # Update fields
    if update_data.status is not None:
        old_status = task.status
        task.status = update_data.status

        # Set completed_at if transitioning to COMPLETE
        if update_data.status == ManualValidationTaskStatus.COMPLETE:
            # Validate completion requirements
            if not task.evidence_ids or len(task.evidence_ids) == 0:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot complete task without evidence. Attach at least one evidence artifact."
                )

            if not update_data.completed_by:
                raise HTTPException(
                    status_code=400,
                    detail="completed_by is required when marking task as COMPLETE."
                )

            task.completed_at = datetime.utcnow()
            task.completed_by = update_data.completed_by

            # Audit log for completion
            audit_log(
                db=db,
                run_id=task.run_id,
                event_type="MANUAL_TASK_COMPLETED",
                actor=update_data.completed_by,
                details={
                    "task_id": str(task.id),
                    "finding_id": str(task.finding_id),
                    "evidence_count": len(task.evidence_ids)
                }
            )

    if update_data.notes is not None:
        task.notes = update_data.notes

    if update_data.completed_by is not None and task.status == ManualValidationTaskStatus.COMPLETE:
        task.completed_by = update_data.completed_by

    task.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(task)

    return task


@router.post("/manual-tasks/{task_id}/attach-evidence", response_model=ManualValidationTaskResponse)
def attach_evidence_to_task(
    task_id: str,
    evidence_data: ManualValidationTaskAttachEvidence,
    db: Session = Depends(get_db)
):
    """
    Attach evidence to a manual validation task.

    Evidence must exist in the database.
    """
    task = db.query(ManualValidationTask).filter(ManualValidationTask.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Manual validation task not found")

    # Verify evidence exists
    evidence = db.query(Evidence).filter(Evidence.id == evidence_data.evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")

    # Add evidence_id to task if not already attached
    if evidence_data.evidence_id not in task.evidence_ids:
        task.evidence_ids.append(evidence_data.evidence_id)
        task.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(task)

        # Audit log
        audit_log(
            db=db,
            run_id=task.run_id,
            event_type="EVIDENCE_ATTACHED_TO_TASK",
            actor="user",
            details={
                "task_id": str(task.id),
                "evidence_id": evidence_data.evidence_id,
                "finding_id": str(task.finding_id)
            }
        )

    return task

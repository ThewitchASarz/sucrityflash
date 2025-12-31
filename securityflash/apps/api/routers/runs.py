"""
Run management endpoints.

MUST-FIX A: POST /runs/{run_id}/start endpoint for explicit state transition.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
from apps.api.db.session import get_db
from apps.api.models.run import Run, RunStatus
from apps.api.models.scope import Scope
from apps.api.models.project import Project
from apps.api.schemas.run import RunCreate, RunStart, RunResponse
from apps.api.services.audit_service import audit_log
from apps.api.services.status_fsm import transition_run_status
from apps.api.services.scope_lock_service import ScopeLockService
from apps.api.core.security import get_current_user

router = APIRouter(prefix="/api/v1", tags=["runs"])


@router.post("/projects/{project_id}/runs", response_model=RunResponse, status_code=201)
def create_run(
    project_id: str,
    run_data: RunCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Create a new run.

    MUST-FIX A: Run is created in CREATED state.
    Agent will NOT start until POST /runs/{run_id}/start is called.
    """
    # Verify project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Verify scope exists and is locked
    scope = db.query(Scope).filter(Scope.id == run_data.scope_id).first()
    if not scope:
        raise HTTPException(status_code=404, detail="Scope not found")

    ScopeLockService.enforce_locked(scope)

    # Create run in CREATED state (MUST-FIX A)
    run = Run(
        project_id=project_id,
        scope_id=run_data.scope_id,
        policy_version=run_data.policy_version,
        status=RunStatus.CREATED,  # MUST-FIX A
        max_iterations=run_data.max_iterations,
        created_by=run_data.created_by
    )

    db.add(run)
    db.commit()
    db.refresh(run)

    # Audit log
    audit_log(
        db=db,
        run_id=run.id,
        event_type="RUN_CREATED",
        actor=run_data.created_by,
        details={
            "run_id": str(run.id),
            "scope_id": str(run_data.scope_id),
            "status": RunStatus.CREATED.value
        }
    )

    return run


@router.post("/runs/{run_id}/start", response_model=RunResponse)
def start_run(
    run_id: str,
    run_start: RunStart,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    MUST-FIX A: Explicit run start endpoint.

    Transitions run from CREATED → RUNNING.
    Only after this transition can:
    - Agent begin proposing actions
    - Worker execute approved actions

    Only project owner/reviewer can call this endpoint.
    """
    run = db.query(Run).filter(Run.id == run_id).first()

    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Use FSM to transition (MUST-FIX B)
    current_user = get_current_user(request)
    transition_run_status(run, RunStatus.RUNNING, current_user, db)

    # Set started_at timestamp
    run.started_at = datetime.utcnow()
    db.commit()
    db.refresh(run)

    # Audit log
    audit_log(
        db=db,
        run_id=run.id,
        event_type="RUN_STARTED",
        actor=current_user,
        details={
            "run_id": str(run.id),
            "started_at": run.started_at.isoformat()
        }
    )

    return run


@router.get("/runs/{run_id}", response_model=RunResponse)
def get_run(run_id: str, db: Session = Depends(get_db)):
    """Get run status and details."""
    run = db.query(Run).filter(Run.id == run_id).first()

    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    return run


@router.get("/projects/{project_id}/runs", response_model=List[RunResponse])
def list_runs(project_id: str, db: Session = Depends(get_db)):
    """List all runs for a project."""
    return db.query(Run).filter(Run.project_id == project_id).all()


@router.get("/runs/{run_id}/timeline")
def get_run_timeline(run_id: str, db: Session = Depends(get_db)):
    """
    Get timeline of events for a run.

    Returns chronological activity from audit_log for UI display.
    """
    from apps.api.models.audit_log import AuditLog

    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Get audit log events for this run
    events = db.query(AuditLog).filter(
        AuditLog.run_id == run_id
    ).order_by(AuditLog.timestamp.asc()).all()

    # Format for UI
    timeline = []
    for event in events:
        timeline.append({
            "timestamp": event.timestamp.isoformat(),
            "event_type": event.event_type,
            "actor": event.actor,
            "details": event.details
        })

    return timeline


@router.get("/runs/{run_id}/stats")
def get_run_stats(run_id: str, db: Session = Depends(get_db)):
    """
    Get statistics for a run.

    Returns counts and metrics for UI dashboard.
    """
    from apps.api.models.action_spec import ActionSpec
    from apps.api.models.evidence import Evidence

    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Count action specs by status
    action_specs = db.query(ActionSpec).filter(ActionSpec.run_id == run_id).all()
    pending_approvals = len([a for a in action_specs if a.status == "PENDING_APPROVAL"])
    approved = len([a for a in action_specs if a.status == "APPROVED"])
    executed = len([a for a in action_specs if a.status == "EXECUTED"])

    # Count evidence
    evidence_count = db.query(Evidence).filter(Evidence.run_id == run_id).count()

    # Get last activity timestamp
    from apps.api.models.audit_log import AuditLog
    last_event = db.query(AuditLog).filter(
        AuditLog.run_id == run_id
    ).order_by(AuditLog.timestamp.desc()).first()

    return {
        "action_specs_count": len(action_specs),
        "pending_approvals_count": pending_approvals,
        "approved_count": approved,
        "executed_count": executed,
        "evidence_count": evidence_count,
        "last_activity_at": last_event.timestamp.isoformat() if last_event else None
    }


@router.get("/runs/{run_id}/executions")
def get_run_executions(run_id: str, db: Session = Depends(get_db)):
    """
    Get all executed actions for a run.

    Returns action specs with status=EXECUTED, showing what the agent actually did.
    """
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    executions = db.query(ActionSpec).filter(
        ActionSpec.run_id == run_id,
        ActionSpec.status == "EXECUTED"
    ).order_by(ActionSpec.created_at.asc()).all()

    # Format for UI
    result = []
    for action in executions:
        result.append({
            "id": str(action.id),
            "tool": action.action_json.get("tool"),
            "target": action.action_json.get("target"),
            "arguments": action.action_json.get("arguments"),
            "proposed_by": action.proposed_by,
            "risk_score": action.risk_score,
            "approval_tier": action.approval_tier,
            "created_at": action.created_at.isoformat(),
            "executed_at": action.updated_at.isoformat() if action.updated_at else None
        })

    return result


@router.post("/runs/{run_id}/report/generate")
def generate_run_report(run_id: str, db: Session = Depends(get_db)):
    """
    Generate report for a run.

    Creates a summary report with all findings, evidence, and audit trail.
    """
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # TODO: Implement actual report generation logic
    # For now, return a placeholder
    return {
        "run_id": str(run.id),
        "status": "generating",
        "message": "Report generation started. Poll GET /runs/{run_id}/report for status."
    }


@router.get("/runs/{run_id}/report")
def get_run_report(run_id: str, db: Session = Depends(get_db)):
    """
    Get generated report for a run.

    Returns report metadata and download link if available.
    """
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # TODO: Implement actual report retrieval logic
    # For now, return a placeholder
    return {
        "run_id": str(run.id),
        "status": "not_implemented",
        "message": "Report generation not yet implemented"
    }

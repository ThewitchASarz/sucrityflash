"""
Approval endpoints for human reviewers.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
from apps.api.db.session import get_db
from apps.api.models.action_spec import ActionSpec, ActionStatus
from apps.api.models.approval import Approval
from apps.api.models.run import Run, RunStatus
from apps.api.models.scope import Scope
from apps.api.schemas.approval import ApprovalRequest, ApprovalResponse, PendingApproval
from apps.api.schemas.action_spec import ActionSpecResponse
from apps.api.services.policy_engine import PolicyEvaluator
from apps.api.services.audit_service import audit_log
from apps.api.services.status_fsm import transition_action_status
from apps.api.core.security import get_current_user
from apps.observability.metrics import record_approval_latency

router = APIRouter(prefix="/api/v1/runs/{run_id}/approvals", tags=["approvals"])


@router.get("/pending", response_model=List[PendingApproval])
def get_pending_approvals(run_id: str, db: Session = Depends(get_db)):
    """
    Get all pending approvals for a run.

    Used by reviewer CLI and UI to show pending actions.
    """
    pending_actions = db.query(ActionSpec).filter(
        ActionSpec.run_id == run_id,
        ActionSpec.status == ActionStatus.PENDING_APPROVAL
    ).all()

    result = []
    for action in pending_actions:
        result.append(PendingApproval(
            action_id=action.id,
            run_id=action.run_id,
            tool=action.action_json["tool"],
            target=action.action_json["target"],
            arguments=action.action_json["arguments"],
            risk_score=action.risk_score,
            approval_tier=action.approval_tier,
            proposed_by=action.proposed_by,
            proposed_at=action.created_at,
            justification=action.action_json.get("justification")
        ))

    return result


@router.post("/{action_id}/approve", response_model=ActionSpecResponse)
def approve_action(
    run_id: str,
    action_id: str,
    approval_data: ApprovalRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Approve an ActionSpec.

    Flow:
    1. Verify action is PENDING_APPROVAL
    2. Create Approval record
    3. Issue JWT token
    4. Transition action to APPROVED
    5. Worker can now execute
    """
    action = db.query(ActionSpec).filter(
        ActionSpec.id == action_id,
        ActionSpec.run_id == run_id
    ).first()

    if not action:
        raise HTTPException(status_code=404, detail="ActionSpec not found")

    if action.status != ActionStatus.PENDING_APPROVAL:
        raise HTTPException(
            status_code=400,
            detail=f"ActionSpec must be PENDING_APPROVAL to approve (current: {action.status.value})"
        )

    # Get run and scope for token issuance
    run = db.query(Run).filter(Run.id == run_id).first()
    scope = db.query(Scope).filter(Scope.id == run.scope_id).first()

    # Issue token via Policy Engine
    policy_evaluator = PolicyEvaluator(db)
    token = policy_evaluator._issue_token(
        run_id=str(run_id),
        action_spec=action.action_json,
        policy_version=run.policy_version,
        risk_score=action.risk_score,
        approval_tier=action.approval_tier
    )

    # Create Approval record
    approval = Approval(
        action_spec_id=action_id,
        approval_tier=action.approval_tier,
        approved_at=datetime.utcnow(),
        approved_by=approval_data.approved_by,
        reason=approval_data.reason,
        decision="approved",
        signature=approval_data.signature,
        policy_version=run.policy_version
    )
    db.add(approval)

    # Transition action status (MUST-FIX B)
    transition_action_status(action, ActionStatus.APPROVED, approval_data.approved_by, db)

    # Update action with approval details
    action.approval_token = token
    action.approved_at = datetime.utcnow()
    action.approved_by = approval_data.approved_by

    db.commit()
    db.refresh(action)

    # Observability
    if action.created_at:
        record_approval_latency(action.created_at)

    # Audit log
    audit_log(
        db=db,
        run_id=run.id,
        event_type="ACTION_APPROVED",
        actor=approval_data.approved_by,
        details={
            "action_id": str(action_id),
            "approval_tier": action.approval_tier,
            "reason": approval_data.reason
        }
    )

    return action


@router.post("/{action_id}/reject", response_model=ActionSpecResponse)
def reject_action(
    run_id: str,
    action_id: str,
    approval_data: ApprovalRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Reject an ActionSpec.

    Action transitions to REJECTED (terminal state).
    """
    action = db.query(ActionSpec).filter(
        ActionSpec.id == action_id,
        ActionSpec.run_id == run_id
    ).first()

    if not action:
        raise HTTPException(status_code=404, detail="ActionSpec not found")

    if action.status != ActionStatus.PENDING_APPROVAL:
        raise HTTPException(
            status_code=400,
            detail=f"ActionSpec must be PENDING_APPROVAL to reject (current: {action.status.value})"
        )

    # Get run
    run = db.query(Run).filter(Run.id == run_id).first()

    # Create Approval record
    approval = Approval(
        action_spec_id=action_id,
        approval_tier=action.approval_tier,
        approved_at=datetime.utcnow(),
        approved_by=approval_data.approved_by,
        reason=approval_data.reason,
        decision="rejected",
        signature=approval_data.signature,
        policy_version=run.policy_version
    )
    db.add(approval)

    # Transition action status (MUST-FIX B)
    transition_action_status(action, ActionStatus.REJECTED, approval_data.approved_by, db)

    db.commit()
    db.refresh(action)

    # Audit log
    audit_log(
        db=db,
        run_id=run.id,
        event_type="ACTION_REJECTED",
        actor=approval_data.approved_by,
        details={
            "action_id": str(action_id),
            "reason": approval_data.reason
        }
    )

    return action

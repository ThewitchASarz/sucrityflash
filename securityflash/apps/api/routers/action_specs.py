"""
ActionSpec management endpoints.

Agents POST proposed actions here. Policy Engine evaluates them.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List
from apps.api.db.session import get_db
from apps.api.models.action_spec import ActionSpec, ActionStatus
from apps.api.models.run import Run, RunStatus
from apps.api.models.scope import Scope
from apps.api.schemas.action_spec import ActionSpecCreate, ActionSpecResponse
from apps.api.services.policy_engine import PolicyEvaluator
from apps.api.services.audit_service import audit_log
from apps.api.core.security import get_current_user

router = APIRouter(tags=["action_specs"])

# Global action-specs router (for worker queries)
global_router = APIRouter(prefix="/api/v1/action-specs", tags=["action_specs"])


@router.post("", response_model=ActionSpecResponse, status_code=201)
def propose_action(
    run_id: str,
    action_data: ActionSpecCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Agent proposes an ActionSpec.

    Flow:
    1. Validate run exists and is RUNNING
    2. Route to Policy Engine for evaluation
    3. Store with policy evaluation results
    4. Auto-approve if low risk, or route to reviewer
    """
    # Verify run exists and is RUNNING
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if run.status != RunStatus.RUNNING:
        raise HTTPException(
            status_code=400,
            detail=f"Run must be in RUNNING state to accept actions (current: {run.status.value})"
        )

    # Get scope
    scope = db.query(Scope).filter(Scope.id == run.scope_id).first()

    # Build action_json
    action_json = {
        "tool": action_data.tool,
        "arguments": action_data.arguments,
        "target": action_data.target,
        "proposed_by": action_data.proposed_by,
        "justification": action_data.justification,
        "expected_evidence_type": action_data.expected_evidence_type
    }

    # Evaluate with Policy Engine
    policy_evaluator = PolicyEvaluator(db)
    decision = policy_evaluator.evaluate(
        run_id=str(run_id),
        scope=scope,
        action_spec=action_json,
        policy_version=run.policy_version
    )

    # Determine status based on decision
    if decision.approved:
        status = ActionStatus.APPROVED
    elif decision.approval_tier == "C" or decision.risk_score >= 0.4:
        status = ActionStatus.PENDING_APPROVAL
    else:
        status = ActionStatus.REJECTED

    # Create ActionSpec
    action_spec = ActionSpec(
        run_id=run_id,
        proposed_by=action_data.proposed_by,
        action_json=action_json,
        status=status,
        risk_score=decision.risk_score,
        approval_tier=decision.approval_tier,
        policy_check_result=decision.policy_checks,
        approval_token=decision.auth_token
    )

    db.add(action_spec)
    db.commit()
    db.refresh(action_spec)

    # Audit log
    audit_log(
        db=db,
        run_id=run.id,
        event_type="ACTION_PROPOSED",
        actor=action_data.proposed_by,
        details={
            "action_id": str(action_spec.id),
            "tool": action_data.tool,
            "target": action_data.target,
            "risk_score": decision.risk_score,
            "approval_tier": decision.approval_tier,
            "status": status.value
        }
    )

    return action_spec


@router.get("", response_model=List[ActionSpecResponse])
def list_action_specs(
    run_id: str,
    status: str = None,
    db: Session = Depends(get_db)
):
    """List ActionSpecs for a run, optionally filtered by status."""
    query = db.query(ActionSpec).filter(ActionSpec.run_id == run_id)

    if status:
        query = query.filter(ActionSpec.status == status)

    return query.all()


@router.get("/{action_id}", response_model=ActionSpecResponse)
def get_action_spec(run_id: str, action_id: str, db: Session = Depends(get_db)):
    """Get ActionSpec by ID."""
    action_spec = db.query(ActionSpec).filter(
        ActionSpec.id == action_id,
        ActionSpec.run_id == run_id
    ).first()

    if not action_spec:
        raise HTTPException(status_code=404, detail="ActionSpec not found")

    return action_spec


# Global query endpoint for workers
@global_router.get("", response_model=List[ActionSpecResponse])
def query_action_specs_global(
    status: str = None,
    run_status: str = None,
    db: Session = Depends(get_db)
):
    """
    Query ActionSpecs across all runs (for worker polling).

    Workers poll this endpoint to find APPROVED actions ready for execution.
    """
    query = db.query(ActionSpec)

    if status:
        query = query.filter(ActionSpec.status == status)

    if run_status:
        # Join with Run table to filter by run status
        query = query.join(Run).filter(Run.status == run_status)

    return query.all()

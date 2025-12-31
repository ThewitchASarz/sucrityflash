"""
Status Finite State Machine - MUST-FIX B.

Enforces valid state transitions for runs and action_specs.
Invalid transitions raise HTTPException(400).
"""
from typing import Dict, List
from fastapi import HTTPException
from apps.api.models.action_spec import ActionStatus
from apps.api.models.run import RunStatus


class StatusTransitions:
    """
    Defines allowed state transitions.

    MUST-FIX B: Enforce these transitions everywhere.
    No exceptions. Fail closed, not open.
    """

    ACTION_SPEC_ALLOWED: Dict[ActionStatus, List[ActionStatus]] = {
        ActionStatus.PROPOSED: [ActionStatus.PENDING_APPROVAL, ActionStatus.REJECTED],
        ActionStatus.PENDING_APPROVAL: [ActionStatus.APPROVED, ActionStatus.REJECTED],
        ActionStatus.APPROVED: [ActionStatus.EXECUTING],
        ActionStatus.EXECUTING: [ActionStatus.EXECUTED, ActionStatus.FAILED],
        # EXECUTED, REJECTED, FAILED are terminal states (no transitions)
    }

    RUN_ALLOWED: Dict[RunStatus, List[RunStatus]] = {
        RunStatus.CREATED: [RunStatus.RUNNING],
        RunStatus.RUNNING: [RunStatus.COMPLETED, RunStatus.FAILED],
        # COMPLETED, FAILED are terminal states (no transitions)
    }


def validate_action_transition(
    current: ActionStatus,
    new: ActionStatus,
    action_id: str
) -> None:
    """
    Validate action_spec status transition.

    Args:
        current: Current status
        new: Desired new status
        action_id: Action ID for error message

    Raises:
        HTTPException(400): If transition is invalid
    """
    allowed = StatusTransitions.ACTION_SPEC_ALLOWED.get(current, [])

    if new not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid state transition for action {action_id}: "
                   f"{current.value} → {new.value} not allowed. "
                   f"Allowed transitions from {current.value}: {[s.value for s in allowed]}"
        )


def validate_run_transition(
    current: RunStatus,
    new: RunStatus,
    run_id: str
) -> None:
    """
    Validate run status transition.

    Args:
        current: Current status
        new: Desired new status
        run_id: Run ID for error message

    Raises:
        HTTPException(400): If transition is invalid
    """
    allowed = StatusTransitions.RUN_ALLOWED.get(current, [])

    if new not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid state transition for run {run_id}: "
                   f"{current.value} → {new.value} not allowed. "
                   f"Allowed transitions from {current.value}: {[s.value for s in allowed]}"
        )


def transition_action_status(
    action,
    new_status: ActionStatus,
    actor: str,
    db
) -> None:
    """
    Safely transition action_spec status with FSM validation.

    Args:
        action: ActionSpec SQLAlchemy model instance
        new_status: Target status
        actor: Actor performing transition (for audit)
        db: Database session

    Raises:
        HTTPException(400): If transition is invalid
    """
    # Validate transition
    validate_action_transition(action.status, new_status, str(action.id))

    # Perform transition
    old_status = action.status
    action.status = new_status
    db.commit()

    # Log to audit (will be implemented in audit_service.py)
    # audit_log(action.run_id, f"ACTION_STATUS_CHANGED", actor, {
    #     "action_id": str(action.id),
    #     "old_status": old_status.value,
    #     "new_status": new_status.value
    # })


def transition_run_status(
    run,
    new_status: RunStatus,
    actor: str,
    db
) -> None:
    """
    Safely transition run status with FSM validation.

    Args:
        run: Run SQLAlchemy model instance
        new_status: Target status
        actor: Actor performing transition (for audit)
        db: Database session

    Raises:
        HTTPException(400): If transition is invalid
    """
    # Validate transition
    validate_run_transition(run.status, new_status, str(run.id))

    # Perform transition
    old_status = run.status
    run.status = new_status
    db.commit()

    # Log to audit (will be implemented in audit_service.py)
    # audit_log(run.id, f"RUN_STATUS_CHANGED", actor, {
    #     "old_status": old_status.value,
    #     "new_status": new_status.value
    # })

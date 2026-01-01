"""
Execution endpoints - First-class tool execution records.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from apps.api.db.session import get_db
from apps.api.models.execution import Execution
from apps.api.models.run import Run
from apps.api.schemas.execution import ExecutionResponse

router = APIRouter(prefix="/api/v1", tags=["executions"])


@router.get("/runs/{run_id}/executions", response_model=List[ExecutionResponse])
def list_run_executions(run_id: str, db: Session = Depends(get_db)):
    """
    List all executions for a run.

    Returns chronological list of tool invocations with status and artifacts.
    """
    # Verify run exists
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Get all executions for this run
    executions = db.query(Execution).filter(
        Execution.run_id == run_id
    ).order_by(Execution.started_at.asc()).all()

    return executions


@router.get("/executions/{execution_id}", response_model=ExecutionResponse)
def get_execution(execution_id: str, db: Session = Depends(get_db)):
    """
    Get execution by ID.

    Returns detailed execution record with artifacts and summary.
    """
    execution = db.query(Execution).filter(Execution.id == execution_id).first()

    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    return execution

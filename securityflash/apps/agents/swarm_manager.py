"""
Swarm Manager - coordinates multi-agent task queues with safety controls.
"""
from datetime import datetime, timedelta
from typing import Optional
import logging
import uuid

from sqlalchemy.orm import Session

from apps.api.models.swarm_task import SwarmTask, SwarmTaskStatus
from apps.api.models.swarm_lock import SwarmLock
from apps.api.models.swarm_budget import SwarmBudget
from apps.api.models.run import Run, RunStatus
from apps.api.services.audit_service import audit_log

logger = logging.getLogger(__name__)


class SwarmManager:
    """Lightweight task coordinator enforcing budgets and kill-switches."""

    def __init__(self, db: Session, agent_id: str):
        self.db = db
        self.agent_id = agent_id

    def _get_or_create_budget(self, run_id: str) -> SwarmBudget:
        budget = self.db.query(SwarmBudget).filter(SwarmBudget.run_id == run_id).first()
        if not budget:
            budget = SwarmBudget(run_id=run_id)
            self.db.add(budget)
            self.db.commit()
            self.db.refresh(budget)
        return budget

    def _acquire_lock(self, run_id: str, lock_key: str, ttl_seconds: int = 120) -> bool:
        existing = self.db.query(SwarmLock).filter(SwarmLock.lock_key == lock_key).first()
        now = datetime.utcnow()
        if existing and existing.expires_at > now:
            return False
        if existing:
            self.db.delete(existing)
            self.db.commit()
        lock = SwarmLock(
            id=uuid.uuid4(),
            lock_key=lock_key,
            run_id=run_id,
            owner_agent_id=self.agent_id,
            expires_at=now + timedelta(seconds=ttl_seconds),
        )
        self.db.add(lock)
        self.db.commit()
        return True

    def tick(self, run_id: str):
        """Assign queued tasks up to budget and respect kill switch."""
        run = self.db.query(Run).filter(Run.id == run_id).first()
        if not run:
            logger.warning(f"Run {run_id} not found; skipping swarm tick")
            return

        if run.kill_switch_activated_at or run.status == RunStatus.ABORTED:
            # Cancel queued tasks
            queued = self.db.query(SwarmTask).filter(
                SwarmTask.run_id == run_id,
                SwarmTask.status == SwarmTaskStatus.QUEUED
            ).all()
            for task in queued:
                task.status = SwarmTaskStatus.CANCELLED
            self.db.commit()
            if queued:
                audit_log(
                    db=self.db,
                    run_id=run.id,
                    event_type="SWARM_TASKS_CANCELLED_KILL_SWITCH",
                    actor=self.agent_id,
                    details={"count": len(queued)}
                )
            logger.warning(f"Kill switch active; cancelled {len(queued)} queued swarm tasks for run {run_id}")
            return

        budget = self._get_or_create_budget(run_id)
        running_count = self.db.query(SwarmTask).filter(
            SwarmTask.run_id == run_id,
            SwarmTask.status == SwarmTaskStatus.RUNNING
        ).count()
        available_slots = max(budget.max_tasks_running - running_count, 0)
        if available_slots <= 0:
            return

        queued_tasks = self.db.query(SwarmTask).filter(
            SwarmTask.run_id == run_id,
            SwarmTask.status == SwarmTaskStatus.QUEUED
        ).order_by(SwarmTask.created_at.asc()).limit(available_slots).all()

        for task in queued_tasks:
            lock_key = f"{task.run_id}:{task.dedupe_key}"
            if not self._acquire_lock(run_id, lock_key):
                continue
            task.status = SwarmTaskStatus.RUNNING
            task.assigned_agent_id = self.agent_id
            task.updated_at = datetime.utcnow()
            audit_log(
                db=self.db,
                run_id=run.id,
                event_type="SWARM_TASK_ASSIGNED",
                actor=self.agent_id,
                details={
                    "task_id": str(task.id),
                    "task_type": task.task_type.value,
                    "target_key": task.target_key
                }
            )

        self.db.commit()

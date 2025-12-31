"""
Background orchestrator: Autonomous execution of test plans.
"""
import asyncio
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from models.run import Run
from models.test_plan import TestPlan, Action
from models.approval import Approval
from services.executor import action_executor
from services.approval_manager import approval_manager
from services.audit_log_service import audit_log_service
from database import AsyncSessionLocal


class RunOrchestrator:
    """Orchestrates autonomous test execution."""

    def __init__(self):
        self.running = False
        self.active_runs: set[uuid.UUID] = set()

    async def start(self):
        """Start the orchestrator background task."""
        self.running = True
        asyncio.create_task(self._run_loop())
        asyncio.create_task(self._expire_approvals_loop())

    async def stop(self):
        """Stop the orchestrator."""
        self.running = False

    async def _run_loop(self):
        """Main execution loop."""
        while self.running:
            try:
                async with AsyncSessionLocal() as db:
                    # Find pending runs
                    result = await db.execute(
                        select(Run).where(Run.status == "PENDING")
                    )
                    pending_runs = result.scalars().all()

                    for run in pending_runs:
                        if run.id not in self.active_runs:
                            # Start run execution
                            asyncio.create_task(self._execute_run(run.id))
                            self.active_runs.add(run.id)

                    # Check executing runs for completion
                    result = await db.execute(
                        select(Run).where(Run.status == "EXECUTING")
                    )
                    executing_runs = result.scalars().all()

                    for run in executing_runs:
                        if run.id not in self.active_runs:
                            # Resume run execution
                            asyncio.create_task(self._execute_run(run.id))
                            self.active_runs.add(run.id)

            except Exception as e:
                print(f"Error in orchestrator run loop: {str(e)}")

            await asyncio.sleep(5)  # Check every 5 seconds

    async def _expire_approvals_loop(self):
        """Background task to expire stale approvals."""
        while self.running:
            try:
                async with AsyncSessionLocal() as db:
                    expired_count = await approval_manager.expire_stale_approvals(db)
                    if expired_count > 0:
                        print(f"Expired {expired_count} stale approvals")
            except Exception as e:
                print(f"Error expiring approvals: {str(e)}")

            await asyncio.sleep(60)  # Check every minute

    async def _execute_run(self, run_id: uuid.UUID):
        """Execute a single run."""
        try:
            async with AsyncSessionLocal() as db:
                # Fetch run
                result = await db.execute(
                    select(Run).where(Run.id == run_id)
                )
                run = result.scalar_one_or_none()

                if not run:
                    self.active_runs.discard(run_id)
                    return

                # Update to EXECUTING if PENDING
                if run.status == "PENDING":
                    run.status = "EXECUTING"
                    run.started_at = datetime.utcnow()
                    await db.commit()

                # Fetch test plan and actions
                result = await db.execute(
                    select(TestPlan).where(TestPlan.id == run.plan_id)
                )
                test_plan = result.scalar_one_or_none()

                if not test_plan:
                    run.status = "FAILED"
                    run.completed_at = datetime.utcnow()
                    run.halt_reason = "Test plan not found"
                    await db.commit()
                    self.active_runs.discard(run_id)
                    return

                # Fetch all actions
                result = await db.execute(
                    select(Action)
                    .where(Action.test_plan_id == test_plan.id)
                    .order_by(Action.created_at)
                )
                actions = result.scalars().all()

                # Execute actions in order
                for action in actions:
                    # Check if run was halted
                    await db.refresh(run)
                    if run.status in ["HALTED_SCOPE_VIOLATION", "HALTED_EMERGENCY"]:
                        print(f"Run {run_id} halted: {run.halt_reason}")
                        break

                    # Skip already completed/failed actions
                    if action.status in ["completed", "failed"]:
                        continue

                    # Check if autonomous or requires approval
                    can_execute = await action_executor.can_execute_autonomously(action)

                    if can_execute:
                        # L0/L1: Execute autonomously
                        try:
                            success, error = await action_executor.execute_action(
                                db=db,
                                action=action,
                                run=run,
                                actor_type="AGENT",
                                actor_id=None
                            )

                            if not success:
                                print(f"Action {action.action_id} failed: {error}")

                        except Exception as e:
                            print(f"Error executing action {action.action_id}: {str(e)}")

                    else:
                        # L2/L3: Check for approval
                        result = await db.execute(
                            select(Approval)
                            .where(
                                and_(
                                    Approval.action_id == action.id,
                                    Approval.run_id == run_id
                                )
                            )
                        )
                        approval = result.scalar_one_or_none()

                        if not approval:
                            # No approval request yet - create one
                            approval = await approval_manager.create_approval_request(
                                db=db,
                                action=action,
                                run_id=run_id,
                                justification=f"Automated request for {action.risk_level} action: {action.description}",
                                evidence_references=[],
                                requested_by=uuid.UUID("00000000-0000-0000-0000-000000000000")  # System
                            )
                            print(f"Created approval request for action {action.action_id} ({action.risk_level})")

                        elif approval.status == "APPROVED":
                            # Execute approved action
                            try:
                                success, error = await action_executor.execute_action(
                                    db=db,
                                    action=action,
                                    run=run,
                                    actor_type="AGENT",
                                    actor_id=None
                                )

                                if not success:
                                    print(f"Action {action.action_id} failed: {error}")

                            except Exception as e:
                                print(f"Error executing action {action.action_id}: {str(e)}")

                        elif approval.status == "REJECTED":
                            # Skip rejected action
                            action.status = "skipped"
                            await db.commit()
                            print(f"Action {action.action_id} skipped (rejected)")

                        elif approval.status == "EXPIRED":
                            # Skip expired action
                            action.status = "skipped"
                            await db.commit()
                            print(f"Action {action.action_id} skipped (approval expired)")

                        else:
                            # Still pending - wait
                            print(f"Waiting for approval of action {action.action_id}")
                            await asyncio.sleep(10)

                # Check if all actions complete
                await db.refresh(run)
                if run.status == "EXECUTING":
                    result = await db.execute(
                        select(Action)
                        .where(
                            and_(
                                Action.test_plan_id == test_plan.id,
                                Action.status.notin_(["completed", "failed", "skipped"])
                            )
                        )
                    )
                    pending_actions = result.scalars().all()

                    if not pending_actions:
                        # All done
                        run.status = "COMPLETED"
                        run.completed_at = datetime.utcnow()
                        await db.commit()

                        await audit_log_service.create(
                            db=db,
                            actor_type="SYSTEM",
                            actor_id="SYSTEM",
                            action="RUN_COMPLETED",
                            resource_type="RUN",
                            resource_id=str(run_id),
                            details={
                                "duration_seconds": (run.completed_at - run.started_at).total_seconds()
                            },
                            ip_address=None
                        )

                        print(f"Run {run_id} completed")
                        self.active_runs.discard(run_id)
                    else:
                        # Still has pending actions (waiting for approvals)
                        await asyncio.sleep(10)

        except Exception as e:
            print(f"Error executing run {run_id}: {str(e)}")
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Run).where(Run.id == run_id)
                )
                run = result.scalar_one_or_none()
                if run:
                    run.status = "FAILED"
                    run.halt_reason = str(e)
                    run.completed_at = datetime.utcnow()
                    await db.commit()
            self.active_runs.discard(run_id)


# Global orchestrator instance
orchestrator = RunOrchestrator()

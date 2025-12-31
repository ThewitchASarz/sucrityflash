#!/usr/bin/env python3
"""
AGENT RUNTIME - Proposes ActionSpecs, never executes tools.

Responsibilities:
- Poll for PENDING/EXECUTING runs
- Read run state, scope, test plan
- Propose next ActionSpec based on prerequisites
- Submit ActionSpec for approval (L2/L3) or mark ready (L0/L1)
- Wait for approval events or evidence completion
- NEVER execute tools
- NEVER spawn subprocesses

Run: python -m backend.agents.runner
"""
import asyncio
import sys
import uuid
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Add parent directory to path for imports
sys.path.insert(0, '/Users/annalealayton/PyCharmMiscProject/pentest-ai-platform/backend')

from database import AsyncSessionLocal
from models.run import Run
from models.test_plan import TestPlan, Action
from models.scope import Scope
from services.audit_log_service import audit_log_service


class AgentRuntime:
    """
    Agent Runtime: Proposes ActionSpecs without executing them.
    """

    def __init__(self):
        self.running = False
        self.active_runs: set[uuid.UUID] = set()

    async def start(self):
        """Start agent runtime loop."""
        self.running = True
        print("🤖 AGENT RUNTIME STARTED")
        print("   Role: Propose ActionSpecs only")
        print("   Never executes tools or spawns processes")
        print()

        while self.running:
            try:
                await self._agent_loop()
            except KeyboardInterrupt:
                print("\n🛑 Agent runtime shutting down...")
                self.running = False
            except Exception as e:
                print(f"❌ Error in agent loop: {str(e)}")
                await asyncio.sleep(5)

    async def _agent_loop(self):
        """Main agent loop - proposes actions."""
        async with AsyncSessionLocal() as db:
            # Find pending/executing runs
            result = await db.execute(
                select(Run).where(Run.status.in_(["PENDING", "EXECUTING"]))
            )
            runs = result.scalars().all()

            for run in runs:
                if run.id not in self.active_runs:
                    print(f"📋 Monitoring run: {run.id}")
                    self.active_runs.add(run.id)

                await self._propose_next_action(db, run)

            # Cleanup completed runs
            self.active_runs = {r.id for r in runs}

        await asyncio.sleep(5)  # Poll every 5 seconds

    async def _propose_next_action(self, db: AsyncSession, run: Run):
        """
        Propose next action for a run.

        Logic:
        1. Find next action with status='pending' and prerequisites met
        2. If L0/L1: Mark as 'ready_for_execution' (worker will pick up)
        3. If L2/L3: Create approval request
        4. Never execute the action
        """
        # Fetch test plan
        result = await db.execute(
            select(TestPlan).where(TestPlan.id == run.plan_id)
        )
        test_plan = result.scalar_one_or_none()

        if not test_plan:
            return

        # Update run status if still PENDING
        if run.status == "PENDING":
            run.status = "EXECUTING"
            run.started_at = datetime.utcnow()
            await db.commit()
            print(f"   ▶️  Run {run.id} started")

        # Find next pending action with prerequisites met
        result = await db.execute(
            select(Action)
            .where(Action.test_plan_id == test_plan.id)
            .where(Action.status == "pending")
            .order_by(Action.created_at)
        )
        pending_actions = result.scalars().all()

        for action in pending_actions:
            # Check prerequisites (simplified - in V1, just check if prior actions completed)
            prereqs_met = await self._check_prerequisites(db, action)

            if not prereqs_met:
                continue

            # Propose this action based on risk level
            if action.risk_level in ["L0", "L1"]:
                # Low risk - mark ready for worker execution
                action.status = "ready_for_execution"
                await db.commit()
                print(f"   ✅ Action {action.action_id} ({action.risk_level}) ready for execution")

                # Audit log
                await audit_log_service.create(
                    db=db,
                    actor_type="AGENT",
                    actor_id="agent_runtime",
                    action="ACTION_PROPOSED",
                    resource_type="ACTION",
                    resource_id=str(action.id),
                    details={
                        "action_id": action.action_id,
                        "risk_level": action.risk_level,
                        "method": action.method,
                        "run_id": str(run.id)
                    }
                )
                break  # Process one action at a time

            elif action.risk_level in ["L2", "L3"]:
                # High risk - needs approval
                # In V1, agent just marks it as 'awaiting_approval'
                # Actual approval request created via API by operator
                action.status = "awaiting_approval"
                await db.commit()
                print(f"   ⏳ Action {action.action_id} ({action.risk_level}) awaiting approval")

                # Audit log
                await audit_log_service.create(
                    db=db,
                    actor_type="AGENT",
                    actor_id="agent_runtime",
                    action="ACTION_REQUIRES_APPROVAL",
                    resource_type="ACTION",
                    resource_id=str(action.id),
                    details={
                        "action_id": action.action_id,
                        "risk_level": action.risk_level,
                        "method": action.method,
                        "run_id": str(run.id)
                    }
                )
                break

        # Check if run is complete
        result = await db.execute(
            select(Action)
            .where(Action.test_plan_id == test_plan.id)
            .where(Action.status.in_(["pending", "ready_for_execution", "awaiting_approval", "executing"]))
        )
        remaining_actions = result.scalars().all()

        if not remaining_actions:
            run.status = "COMPLETED"
            run.completed_at = datetime.utcnow()
            await db.commit()
            print(f"   ✅ Run {run.id} completed")
            self.active_runs.discard(run.id)

    async def _check_prerequisites(self, db: AsyncSession, action: Action) -> bool:
        """Check if action prerequisites are met (simplified)."""
        if not action.prerequisites:
            return True

        # Check if all prerequisite actions are completed
        for prereq_id in action.prerequisites:
            result = await db.execute(
                select(Action)
                .where(Action.test_plan_id == action.test_plan_id)
                .where(Action.action_id == prereq_id)
            )
            prereq_action = result.scalar_one_or_none()

            if not prereq_action or prereq_action.status != "completed":
                return False

        return True


async def main():
    """Main entry point for agent runtime."""
    runtime = AgentRuntime()
    await runtime.start()


if __name__ == "__main__":
    asyncio.run(main())

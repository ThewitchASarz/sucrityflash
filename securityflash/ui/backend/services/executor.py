"""
Autonomous executor: Executes L0-L1 actions without human approval.
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.test_plan import Action, TestPlan
from models.scope import Scope
from models.run import Run
from tools.registry import tool_registry
from services.evidence_service import evidence_service
from services.policy_validator import policy_validator, PolicyViolation
from services.audit_log_service import audit_log_service


class ActionExecutor:
    """Executes actions with policy validation and evidence capture."""

    async def execute_action(
        self,
        db: AsyncSession,
        action: Action,
        run: Run,
        actor_type: str = "AGENT",
        actor_id: Optional[uuid.UUID] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Execute a single action with full governance.

        Args:
            db: Database session
            action: Action to execute
            run: Run context
            actor_type: "AGENT" or "USER"
            actor_id: Actor UUID (None for AGENT)

        Returns:
            tuple[bool, Optional[str]]: (success, error_message)

        Process:
            1. Verify action belongs to approved plan
            2. Verify prerequisites met
            3. Validate against scope and policies
            4. Execute tool
            5. Create evidence with hash chaining
            6. Update action status
            7. Audit log
        """
        started_at = datetime.utcnow()

        try:
            # 1. Fetch test plan and scope
            result = await db.execute(
                select(TestPlan).where(TestPlan.id == action.test_plan_id)
            )
            test_plan = result.scalar_one_or_none()

            if not test_plan:
                return False, "Test plan not found"

            if not test_plan.approved_at:
                return False, "Test plan not approved"

            result = await db.execute(
                select(Scope).where(Scope.id == test_plan.scope_id)
            )
            scope = result.scalar_one_or_none()

            if not scope:
                return False, "Scope not found"

            # 2. Verify prerequisites (simplified)
            prereqs_met, prereq_error = await self._check_prerequisites(db, action)
            if not prereqs_met:
                return False, f"Prerequisites not met: {prereq_error}"

            # 3. Validate against policies
            is_valid, error = await policy_validator.validate_action(db, action, scope, run)
            if not is_valid:
                # Policy violation - halt run
                run.status = "HALTED_SCOPE_VIOLATION"
                run.halt_reason = error
                await db.commit()

                # Audit log
                await audit_log_service.create(
                    db=db,
                    actor_type=actor_type,
                    actor_id=str(actor_id) if actor_id else "SYSTEM",
                    action="ACTION_BLOCKED_POLICY_VIOLATION",
                    resource_type="ACTION",
                    resource_id=str(action.id),
                    details={
                        "action_id": action.action_id,
                        "violation": error,
                        "run_id": str(run.id)
                    },
                    ip_address=None
                )

                raise PolicyViolation(error)

            # 4. Execute tool
            action.status = "executing"
            action.executed_at = started_at
            await db.commit()

            tool = tool_registry.get_tool(action.method)
            if not tool:
                action.status = "failed"
                action.completed_at = datetime.utcnow()
                action.result = {"error": f"Tool {action.method} not available"}
                await db.commit()
                return False, f"Tool {action.method} not available"

            tool_result = await tool.execute(
                action_id=action.action_id,
                target=action.target,
                parameters=action.parameters
            )

            # 5. Create evidence
            evidence = await evidence_service.create_evidence(
                db=db,
                run_id=run.id,
                action_id=action.action_id,
                evidence_type="tool_output",
                content=tool_result.dict(),
                metadata={
                    "action_description": action.description,
                    "method": action.method,
                    "risk_level": action.risk_level
                },
                actor_type=actor_type,
                actor_id=actor_id if actor_id else uuid.UUID("00000000-0000-0000-0000-000000000000")
            )

            # 6. Update action status
            action.status = "completed" if tool_result.status == "success" else "failed"
            action.completed_at = datetime.utcnow()
            action.result = {
                "tool_result": tool_result.dict(),
                "evidence_id": str(evidence.id)
            }

            await db.commit()

            # 7. Audit log
            await audit_log_service.create(
                db=db,
                actor_type=actor_type,
                actor_id=str(actor_id) if actor_id else "SYSTEM",
                action="ACTION_EXECUTED",
                resource_type="ACTION",
                resource_id=str(action.id),
                details={
                    "action_id": action.action_id,
                    "method": action.method,
                    "target": action.target,
                    "risk_level": action.risk_level,
                    "status": action.status,
                    "evidence_id": str(evidence.id),
                    "duration_seconds": (action.completed_at - action.executed_at).total_seconds()
                },
                ip_address=None
            )

            return True, None

        except PolicyViolation as e:
            raise  # Re-raise policy violations
        except Exception as e:
            # Handle unexpected errors
            action.status = "failed"
            action.completed_at = datetime.utcnow()
            action.result = {"error": str(e)}
            await db.commit()

            # Audit log
            await audit_log_service.create(
                db=db,
                actor_type=actor_type,
                actor_id=str(actor_id) if actor_id else "SYSTEM",
                action="ACTION_FAILED",
                resource_type="ACTION",
                resource_id=str(action.id),
                details={
                    "action_id": action.action_id,
                    "error": str(e)
                },
                ip_address=None
            )

            return False, str(e)

    async def _check_prerequisites(
        self,
        db: AsyncSession,
        action: Action
    ) -> tuple[bool, Optional[str]]:
        """
        Check if action prerequisites are met.

        Prerequisites are action_ids that must be completed first.

        Example: ["recon_001", "scan_022"]
        """
        if not action.prerequisites:
            return True, None

        # Fetch prerequisite actions
        for prereq_action_id in action.prerequisites:
            result = await db.execute(
                select(Action)
                .where(
                    Action.test_plan_id == action.test_plan_id,
                    Action.action_id == prereq_action_id
                )
            )
            prereq_action = result.scalar_one_or_none()

            if not prereq_action:
                return False, f"Prerequisite action {prereq_action_id} not found"

            if prereq_action.status != "completed":
                return False, f"Prerequisite action {prereq_action_id} not completed (status: {prereq_action.status})"

        return True, None

    async def can_execute_autonomously(self, action: Action) -> bool:
        """
        Check if action can be executed without human approval.

        L0 and L1 actions are autonomous.
        L2 and L3 require approval.
        """
        return action.risk_level in ["L0", "L1"]


# Global instance
action_executor = ActionExecutor()

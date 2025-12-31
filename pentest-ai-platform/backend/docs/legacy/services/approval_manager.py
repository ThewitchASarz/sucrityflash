"""
Approval manager: Handles L2-L3 approval requests with TTL enforcement.
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from models.approval import Approval
from models.test_plan import Action
from redis_client import redis_client
from services.audit_log_service import audit_log_service


# TTL constants (minutes)
L2_TTL_MINUTES = 15
L3_TTL_MINUTES = 60


class ApprovalManager:
    """Manages approval requests for L2-L3 actions."""

    async def create_approval_request(
        self,
        db: AsyncSession,
        action: Action,
        run_id: uuid.UUID,
        justification: str,
        evidence_references: list[str],
        requested_by: uuid.UUID
    ) -> Approval:
        """
        Create approval request for L2/L3 action.

        Args:
            db: Database session
            action: Action requiring approval
            run_id: Run ID
            justification: Why this action is necessary
            evidence_references: Prior evidence IDs justifying this action
            requested_by: User ID who requested

        Returns:
            Approval: Created approval request

        Process:
            1. Create approval record with TTL
            2. Add to Redis queue for notification
            3. Audit log
        """
        # Calculate TTL based on risk level
        if action.risk_level == "L2":
            ttl_minutes = L2_TTL_MINUTES
        elif action.risk_level == "L3":
            ttl_minutes = L3_TTL_MINUTES
        else:
            raise ValueError(f"Invalid risk level for approval: {action.risk_level}")

        requested_at = datetime.utcnow()
        expiry_at = requested_at + timedelta(minutes=ttl_minutes)

        # Create approval record
        approval = Approval(
            action_id=action.id,
            run_id=run_id,
            risk_level=action.risk_level,
            justification=justification,
            evidence_references=evidence_references,
            status="PENDING",
            requested_at=requested_at,
            requested_by=requested_by,
            expiry_at=expiry_at
        )

        db.add(approval)
        await db.commit()
        await db.refresh(approval)

        # Add to Redis sorted set (score = expiry timestamp)
        await redis_client.zadd(
            "approval_queue",
            {str(approval.id): expiry_at.timestamp()}
        )

        # Audit log
        await audit_log_service.create(
            db=db,
            actor_type="USER",
            actor_id=str(requested_by),
            action="APPROVAL_REQUESTED",
            resource_type="APPROVAL",
            resource_id=str(approval.id),
            details={
                "action_id": str(action.id),
                "action_description": action.description,
                "risk_level": action.risk_level,
                "ttl_minutes": ttl_minutes,
                "expiry_at": expiry_at.isoformat()
            },
            ip_address=None
        )

        return approval

    async def approve_request(
        self,
        db: AsyncSession,
        approval_id: uuid.UUID,
        approved_by: uuid.UUID,
        signature: str,
        notes: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Approve pending request.

        Args:
            db: Database session
            approval_id: Approval ID
            approved_by: User ID who approved
            signature: Digital signature
            notes: Optional approver notes

        Returns:
            tuple[bool, Optional[str]]: (success, error_message)

        Process:
            1. Verify approval exists and is pending
            2. Verify not expired
            3. Mark as approved with signature
            4. Remove from Redis queue
            5. Audit log
        """
        # Fetch approval
        result = await db.execute(
            select(Approval).where(Approval.id == approval_id)
        )
        approval = result.scalar_one_or_none()

        if not approval:
            return False, "Approval request not found"

        if approval.status != "PENDING":
            return False, f"Approval already {approval.status.lower()}"

        # Check expiry
        if datetime.utcnow() > approval.expiry_at:
            approval.status = "EXPIRED"
            approval.decided_at = datetime.utcnow()
            await db.commit()
            return False, "Approval request expired"

        # Approve
        approval.status = "APPROVED"
        approval.decided_at = datetime.utcnow()
        approval.decided_by = approved_by
        approval.approver_signature = signature
        approval.decision_notes = notes

        await db.commit()

        # Remove from Redis queue
        await redis_client.zrem("approval_queue", str(approval_id))

        # Audit log
        await audit_log_service.create(
            db=db,
            actor_type="USER",
            actor_id=str(approved_by),
            action="APPROVAL_GRANTED",
            resource_type="APPROVAL",
            resource_id=str(approval.id),
            details={
                "action_id": str(approval.action_id),
                "risk_level": approval.risk_level,
                "signature": signature,
                "notes": notes
            },
            ip_address=None
        )

        return True, None

    async def reject_request(
        self,
        db: AsyncSession,
        approval_id: uuid.UUID,
        rejected_by: uuid.UUID,
        reason: str
    ) -> tuple[bool, Optional[str]]:
        """
        Reject pending request.

        Args:
            db: Database session
            approval_id: Approval ID
            rejected_by: User ID who rejected
            reason: Rejection reason

        Returns:
            tuple[bool, Optional[str]]: (success, error_message)
        """
        # Fetch approval
        result = await db.execute(
            select(Approval).where(Approval.id == approval_id)
        )
        approval = result.scalar_one_or_none()

        if not approval:
            return False, "Approval request not found"

        if approval.status != "PENDING":
            return False, f"Approval already {approval.status.lower()}"

        # Reject
        approval.status = "REJECTED"
        approval.decided_at = datetime.utcnow()
        approval.decided_by = rejected_by
        approval.decision_notes = reason

        await db.commit()

        # Remove from Redis queue
        await redis_client.zrem("approval_queue", str(approval_id))

        # Audit log
        await audit_log_service.create(
            db=db,
            actor_type="USER",
            actor_id=str(rejected_by),
            action="APPROVAL_REJECTED",
            resource_type="APPROVAL",
            resource_id=str(approval.id),
            details={
                "action_id": str(approval.action_id),
                "risk_level": approval.risk_level,
                "reason": reason
            },
            ip_address=None
        )

        return True, None

    async def expire_stale_approvals(self, db: AsyncSession) -> int:
        """
        Background task: Mark expired approvals as EXPIRED.

        Returns:
            int: Number of approvals expired

        Should be run periodically (e.g., every minute).
        """
        now = datetime.utcnow()

        # Fetch expired pending approvals from Redis
        expired_ids = await redis_client.zrangebyscore(
            "approval_queue",
            min=0,
            max=now.timestamp()
        )

        if not expired_ids:
            return 0

        expired_count = 0
        for approval_id_str in expired_ids:
            approval_id = uuid.UUID(approval_id_str.decode('utf-8') if isinstance(approval_id_str, bytes) else approval_id_str)

            # Fetch and expire
            result = await db.execute(
                select(Approval).where(
                    and_(
                        Approval.id == approval_id,
                        Approval.status == "PENDING"
                    )
                )
            )
            approval = result.scalar_one_or_none()

            if approval:
                approval.status = "EXPIRED"
                approval.decided_at = now
                expired_count += 1

                # Audit log
                await audit_log_service.create(
                    db=db,
                    actor_type="SYSTEM",
                    actor_id="SYSTEM",
                    action="APPROVAL_EXPIRED",
                    resource_type="APPROVAL",
                    resource_id=str(approval.id),
                    details={
                        "action_id": str(approval.action_id),
                        "risk_level": approval.risk_level,
                        "expiry_at": approval.expiry_at.isoformat()
                    },
                    ip_address=None
                )

            # Remove from Redis
            await redis_client.zrem("approval_queue", str(approval_id))

        await db.commit()
        return expired_count

    async def get_pending_approvals(
        self,
        db: AsyncSession,
        run_id: Optional[uuid.UUID] = None
    ) -> list[Approval]:
        """
        Get all pending approval requests.

        Args:
            db: Database session
            run_id: Optional run ID filter

        Returns:
            list[Approval]: Pending approvals
        """
        query = select(Approval).where(Approval.status == "PENDING")

        if run_id:
            query = query.where(Approval.run_id == run_id)

        query = query.order_by(Approval.requested_at)

        result = await db.execute(query)
        return result.scalars().all()


# Global instance
approval_manager = ApprovalManager()

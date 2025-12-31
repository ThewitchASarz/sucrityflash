"""
Audit logging service for UI actions (V2 requirement).

Per spec: "Every UI interaction that changes state (create run, approve action,
delete evidence attempt) must write an audit log entry."
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from datetime import datetime
from typing import Optional
import uuid
import json

from models.audit_log import AuditLog


class AuditService:
    """Service for logging auditable UI actions."""

    @staticmethod
    async def log_action(
        db: AsyncSession,
        user_id: uuid.UUID,
        action: str,
        resource_type: str,
        resource_id: Optional[uuid.UUID],
        details: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """
        Log an auditable UI action.

        Args:
            db: Database session
            user_id: User performing the action
            action: Action name (e.g., "create_run", "approve_action", "delete_evidence_rejected")
            resource_type: Type of resource (e.g., "run", "action", "evidence")
            resource_id: ID of resource (if applicable)
            details: Additional context (serialized to JSONB)
            ip_address: Client IP address
            user_agent: Client User-Agent header

        Returns:
            AuditLog: Created audit log entry
        """
        audit_entry = AuditLog(
            id=uuid.uuid4(),
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.utcnow()
        )

        db.add(audit_entry)
        await db.flush()

        return audit_entry

    @staticmethod
    async def log_create_run(
        db: AsyncSession,
        user_id: uuid.UUID,
        run_id: uuid.UUID,
        test_plan_id: uuid.UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Log run creation."""
        return await AuditService.log_action(
            db=db,
            user_id=user_id,
            action="create_run",
            resource_type="run",
            resource_id=run_id,
            details={"test_plan_id": str(test_plan_id)},
            ip_address=ip_address,
            user_agent=user_agent
        )

    @staticmethod
    async def log_approve_action(
        db: AsyncSession,
        user_id: uuid.UUID,
        action_id: uuid.UUID,
        run_id: uuid.UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Log action approval."""
        return await AuditService.log_action(
            db=db,
            user_id=user_id,
            action="approve_action",
            resource_type="action",
            resource_id=action_id,
            details={"run_id": str(run_id)},
            ip_address=ip_address,
            user_agent=user_agent
        )

    @staticmethod
    async def log_reject_action(
        db: AsyncSession,
        user_id: uuid.UUID,
        action_id: uuid.UUID,
        run_id: uuid.UUID,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Log action rejection."""
        return await AuditService.log_action(
            db=db,
            user_id=user_id,
            action="reject_action",
            resource_type="action",
            resource_id=action_id,
            details={"run_id": str(run_id), "reason": reason},
            ip_address=ip_address,
            user_agent=user_agent
        )

    @staticmethod
    async def log_delete_evidence_rejected(
        db: AsyncSession,
        user_id: uuid.UUID,
        evidence_id: uuid.UUID,
        run_id: uuid.UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """
        Log attempted evidence deletion (always rejected per V2 spec).

        Per spec: "Evidence DELETE must ALWAYS return 403."
        """
        return await AuditService.log_action(
            db=db,
            user_id=user_id,
            action="delete_evidence_rejected",
            resource_type="evidence",
            resource_id=evidence_id,
            details={"run_id": str(run_id), "result": "403_forbidden"},
            ip_address=ip_address,
            user_agent=user_agent
        )

    @staticmethod
    async def log_generate_report(
        db: AsyncSession,
        user_id: uuid.UUID,
        run_id: uuid.UUID,
        report_format: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Log report generation request."""
        return await AuditService.log_action(
            db=db,
            user_id=user_id,
            action="generate_report",
            resource_type="report",
            resource_id=run_id,
            details={"format": report_format},
            ip_address=ip_address,
            user_agent=user_agent
        )

    @staticmethod
    async def log_generate_audit_bundle(
        db: AsyncSession,
        user_id: uuid.UUID,
        run_id: uuid.UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Log audit bundle generation request."""
        return await AuditService.log_action(
            db=db,
            user_id=user_id,
            action="generate_audit_bundle",
            resource_type="audit_bundle",
            resource_id=run_id,
            details={},
            ip_address=ip_address,
            user_agent=user_agent
        )


# Global instance
audit_service = AuditService()

"""
Centralized audit logging service.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from models.audit_log import AuditLog
from datetime import datetime
import uuid
from typing import Optional


class AuditLogService:
    """Service for creating audit log entries."""

    @staticmethod
    async def create(
        db: AsyncSession,
        actor_type: str,
        actor_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        details: dict,
        ip_address: Optional[str] = None
    ) -> AuditLog:
        """
        Create audit log entry.

        Args:
            db: Database session
            actor_type: USER, AGENT, or SYSTEM
            actor_id: User ID, agent name, or "system"
            action: Action performed (e.g., "PROJECT_CREATED", "SCOPE_LOCKED")
            resource_type: Type of resource affected (e.g., "PROJECT", "SCOPE")
            resource_id: ID of resource affected
            details: Additional details (JSONB)
            ip_address: IP address (for user actions)

        Returns:
            AuditLog: Created audit log entry
        """
        log_entry = AuditLog(
            id=uuid.uuid4(),
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            timestamp=datetime.utcnow(),
            ip_address=ip_address
        )

        db.add(log_entry)
        await db.flush()  # Flush to get ID, but don't commit yet

        return log_entry


# Global instance
audit_log_service = AuditLogService()

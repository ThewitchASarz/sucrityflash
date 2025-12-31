"""
Audit logging service.

Every significant action must be logged for compliance.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from apps.api.models.audit_log import AuditLog
import uuid


def audit_log(
    db: Session,
    run_id: Optional[uuid.UUID],
    event_type: str,
    actor: str,
    details: Dict[str, Any],
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> AuditLog:
    """
    Create an audit log entry.

    Args:
        db: Database session
        run_id: Associated run ID (nullable for system events)
        event_type: Event type (RUN_STARTED, ACTION_PROPOSED, etc.)
        actor: Actor performing the action (user_id, agent_id, worker, system)
        details: Event-specific details (JSONB)
        ip_address: Optional IP address
        user_agent: Optional user agent string

    Returns:
        Created AuditLog instance

    Event Types:
        - RUN_STARTED
        - RUN_COMPLETED
        - RUN_FAILED
        - ACTION_PROPOSED
        - ACTION_APPROVED
        - ACTION_REJECTED
        - ACTION_EXECUTED
        - ACTION_FAILED
        - EVIDENCE_STORED
        - SCOPE_LOCKED
        - SCOPE_CREATED
        - PROJECT_CREATED
    """
    log_entry = AuditLog(
        run_id=run_id,
        event_type=event_type,
        actor=actor,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent
    )

    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)

    return log_entry

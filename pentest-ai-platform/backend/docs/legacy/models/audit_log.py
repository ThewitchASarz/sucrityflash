"""
Audit Log model for immutable activity tracking.
"""
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.sql import func
import uuid

from database import Base


class AuditLog(Base):
    """
    Immutable audit log for all system activities.

    Records:
    - All user actions
    - All agent actions
    - All system events
    - All approval decisions
    - All scope locks
    - All policy violations

    Append-only (UPDATE/DELETE triggers prevent modifications).
    """

    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Actor (who did this)
    actor_type = Column(String(50), nullable=False, index=True)  # USER, AGENT, SYSTEM
    actor_id = Column(String(255), nullable=False, index=True)  # user_id, agent name, or "system"

    # Action (what was done)
    action = Column(String(100), nullable=False, index=True)  # ACTION_EXECUTED, APPROVAL_REQUESTED, SCOPE_LOCKED, etc.

    # Resource (what was affected)
    resource_type = Column(String(50), nullable=False, index=True)  # ACTION, APPROVAL, EVIDENCE, RUN, SCOPE, etc.
    resource_id = Column(String(255), nullable=False, index=True)

    # Details (JSONB for flexibility)
    details = Column(JSONB, nullable=False, server_default='{}')

    # Timestamp (immutable)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # IP address (for user actions)
    ip_address = Column(INET, nullable=True)

    def __repr__(self):
        return f"<AuditLog {self.action} by {self.actor_type}:{self.actor_id} at {self.timestamp}>"


# Trigger to prevent audit log modifications (immutability enforcement)
# This will be created via Alembic migration
# CREATE OR REPLACE FUNCTION prevent_audit_log_modification()
# RETURNS TRIGGER AS $$
# BEGIN
#     RAISE EXCEPTION 'Audit log records are immutable and cannot be modified or deleted';
# END;
# $$ LANGUAGE plpgsql;
#
# CREATE TRIGGER audit_log_update_prevention
# BEFORE UPDATE OR DELETE ON audit_log
# FOR EACH ROW
# EXECUTE FUNCTION prevent_audit_log_modification();

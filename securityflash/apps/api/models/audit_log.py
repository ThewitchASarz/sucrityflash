"""
Audit log model - immutable record of all system events.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
from apps.api.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=True, index=True)

    event_type = Column(String(100), nullable=False, index=True)
    # EVENT_TYPES: RUN_STARTED, ACTION_PROPOSED, ACTION_APPROVED, ACTION_EXECUTED,
    #             EVIDENCE_STORED, SCOPE_LOCKED, RUN_FAILED, etc.

    actor = Column(String(255), nullable=False)  # user_id, agent_id, worker, system

    details = Column(JSONB, nullable=False)  # Event-specific data

    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(Text, nullable=True)

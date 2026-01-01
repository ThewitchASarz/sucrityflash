"""
ManualValidationTask Model - Human-validated testing tasks.

For HIGH/CRITICAL findings, requires manual validation with evidence.
NO AUTONOMOUS EXPLOITATION.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from apps.api.db.base import Base


class ManualValidationTaskStatus(str, enum.Enum):
    """Manual validation task lifecycle states."""
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"
    BLOCKED = "BLOCKED"


class ManualValidationTask(Base):
    """
    ManualValidationTask - Human-executed validation with evidence.

    Used for HIGH/CRITICAL findings requiring manual confirmation.
    NO AUTONOMOUS EXPLOITATION - humans execute and attach evidence.
    """
    __tablename__ = "manual_validation_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    finding_id = Column(UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True)

    # Task details
    title = Column(String, nullable=False)
    instructions_md = Column(Text, nullable=False)  # High-level steps, engagement-safe
    required_evidence_types = Column(JSON, nullable=True, default=list)  # ["request_response", "screenshot", "log"]

    # Task lifecycle
    status = Column(SQLEnum(ManualValidationTaskStatus), nullable=False, default=ManualValidationTaskStatus.OPEN, index=True)

    # Ownership and completion
    created_by = Column(String, nullable=False)
    completed_by = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Evidence attachments (stored as JSON array of evidence IDs)
    evidence_ids = Column(JSON, nullable=True, default=list)

    # Notes
    notes = Column(Text, nullable=True)

    # Relationships
    run = relationship("Run", back_populates="manual_tasks")
    finding = relationship("Finding", back_populates="manual_tasks")

    def __repr__(self):
        return f"<ManualValidationTask {self.id} status={self.status.value} title='{self.title}'>"

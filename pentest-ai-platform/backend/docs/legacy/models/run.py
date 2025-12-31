"""
Run model for tracking test execution.
"""
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
import enum

from database import Base


class RunStatus(str, enum.Enum):
    """Run execution status."""
    PENDING = "PENDING"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    HALTED_SCOPE_VIOLATION = "HALTED_SCOPE_VIOLATION"
    HALTED_EMERGENCY = "HALTED_EMERGENCY"
    FAILED = "FAILED"


class Run(Base):
    """
    Test execution run.

    Tracks the execution of an approved test plan.
    """

    __tablename__ = "runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Run state
    status = Column(String(50), default=RunStatus.PENDING.value, nullable=False, index=True)
    halt_reason = Column(Text, nullable=True)
    halt_initiated_by = Column(String(50), nullable=True)  # USER or SYSTEM

    # Timestamps
    started_at = Column(DateTime(timezone=True), nullable=True, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<Run {self.id} ({self.status})>"

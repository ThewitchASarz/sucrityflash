"""
Execution Model - First-class tool execution records.

Tracks every tool invocation with artifacts, timing, and results.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from apps.api.db.base_class import Base


class ExecutionStatus(str, enum.Enum):
    """Execution lifecycle states."""
    STARTED = "STARTED"
    FINISHED = "FINISHED"
    FAILED = "FAILED"


class Execution(Base):
    """
    Execution - First-class record of tool invocation.

    Created BEFORE tool runs, updated after completion.
    Links to Evidence for stdout/stderr artifacts.
    """
    __tablename__ = "executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    scope_id = Column(UUID(as_uuid=True), ForeignKey("scopes.id", ondelete="CASCADE"), nullable=False)
    action_spec_id = Column(UUID(as_uuid=True), ForeignKey("action_specs.id", ondelete="SET NULL"), nullable=True)

    # Tool information
    tool_name = Column(String, nullable=False, index=True)
    tool_version = Column(String, nullable=True)

    # Execution lifecycle
    status = Column(SQLEnum(ExecutionStatus), nullable=False, default=ExecutionStatus.STARTED, index=True)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    exit_code = Column(Integer, nullable=True)

    # Evidence links
    stdout_evidence_id = Column(UUID(as_uuid=True), ForeignKey("evidence.id", ondelete="SET NULL"), nullable=True)
    stderr_evidence_id = Column(UUID(as_uuid=True), ForeignKey("evidence.id", ondelete="SET NULL"), nullable=True)

    # Summary and metadata
    summary_json = Column(JSON, nullable=True)  # {discovered_hosts: 5, status_codes: {200: 3, 404: 1}, ...}
    metadata_json = Column(JSON, nullable=True)  # {args: [...], runtime_sec: 12.5, caps_applied: true, ...}

    # Relationships
    run = relationship("Run", back_populates="executions")
    project = relationship("Project")
    scope = relationship("Scope")
    action_spec = relationship("ActionSpec")
    stdout_evidence = relationship("Evidence", foreign_keys=[stdout_evidence_id])
    stderr_evidence = relationship("Evidence", foreign_keys=[stderr_evidence_id])

    def __repr__(self):
        return f"<Execution {self.id} tool={self.tool_name} status={self.status.value}>"

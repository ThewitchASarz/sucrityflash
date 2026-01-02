"""
Run model - represents an agent execution session.
MUST-FIX A: status field with CREATED, RUNNING, COMPLETED, FAILED states.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Enum as SQLEnum, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum
from apps.api.db.base import Base


class RunStatus(str, enum.Enum):
    """Run status enum - MUST-FIX A."""
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"


class Run(Base):
    __tablename__ = "runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    scope_id = Column(UUID(as_uuid=True), ForeignKey("scopes.id", ondelete="RESTRICT"), nullable=False, index=True)

    policy_version = Column(String(50), nullable=False)

    # MUST-FIX A: Status field
    status = Column(SQLEnum(RunStatus), nullable=False, default=RunStatus.CREATED, index=True)

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    iteration_count = Column(Integer, nullable=False, default=0)
    max_iterations = Column(Integer, nullable=False, default=100)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(String(255), nullable=False)

    # PHASE 2: Agent daemon tracking
    agent_started_at = Column(DateTime(timezone=True), nullable=True)

    # PHASE 3: Monitored mode + kill switch
    monitored_mode_enabled = Column(Boolean, nullable=False, default=False)
    kill_switch_armed = Column(Boolean, nullable=False, default=True)
    kill_switch_activated_at = Column(DateTime(timezone=True), nullable=True)
    monitored_rate_limit_rpm = Column(Integer, nullable=False, default=60)
    monitored_max_concurrency = Column(Integer, nullable=False, default=10)
    monitored_started_by = Column(String(255), nullable=True)
    reviewer_approval = Column(String(255), nullable=True)
    engineer_approval = Column(String(255), nullable=True)
    started_by = Column(String(255), nullable=True)

    # Relationships
    executions = relationship("Execution", back_populates="run", cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="run", cascade="all, delete-orphan")
    manual_tasks = relationship("ManualValidationTask", back_populates="run", cascade="all, delete-orphan")
    validation_packs = relationship("ValidationPack", back_populates="run", cascade="all, delete-orphan")

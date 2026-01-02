"""
Swarm task model - manages queued agent tasks safely.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
import enum
from apps.api.db.base import Base


class SwarmTaskType(str, enum.Enum):
    RECON = "RECON"
    ENUM = "ENUM"
    ANALYZE = "ANALYZE"
    VALIDATE = "VALIDATE"
    WRITE_PACK = "WRITE_PACK"


class SwarmTaskStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class SwarmTask(Base):
    __tablename__ = "swarm_tasks"
    __table_args__ = (
        UniqueConstraint("run_id", "dedupe_key", name="uq_swarm_task_dedupe"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    task_type = Column(SQLEnum(SwarmTaskType), nullable=False)
    target_key = Column(String(255), nullable=False)
    objective = Column(String(2000), nullable=False)
    status = Column(SQLEnum(SwarmTaskStatus), nullable=False, default=SwarmTaskStatus.QUEUED, index=True)
    assigned_agent_id = Column(String(255), nullable=True, index=True)
    dedupe_key = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

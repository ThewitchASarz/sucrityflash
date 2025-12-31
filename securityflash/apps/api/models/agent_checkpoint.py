"""
Agent checkpoint model - stores agent state for recovery.
"""
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
from apps.api.db.base import Base


class AgentCheckpoint(Base):
    __tablename__ = "agent_checkpoints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(String(255), nullable=False, index=True)

    iteration = Column(Integer, nullable=False)
    state = Column(String(50), nullable=False)  # running, paused, completed, failed

    memory_json = Column(JSONB, nullable=False)  # Agent-specific state

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

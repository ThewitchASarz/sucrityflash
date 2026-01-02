"""
Swarm lock model - prevents duplicate work across agents.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from apps.api.db.base import Base


class SwarmLock(Base):
    __tablename__ = "swarm_locks"
    __table_args__ = (
        UniqueConstraint("lock_key", name="uq_swarm_lock_key"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lock_key = Column(String(255), nullable=False)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_agent_id = Column(String(255), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

"""
Swarm budget model - enforces limits for multi-agent coordination.
"""
from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from apps.api.db.base import Base


class SwarmBudget(Base):
    __tablename__ = "swarm_budgets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    max_tasks_total = Column(Integer, nullable=False, default=200)
    max_tasks_running = Column(Integer, nullable=False, default=25)
    max_requests_total = Column(Integer, nullable=False, default=5000)
    max_requests_per_minute = Column(Integer, nullable=False, default=120)
    tokens_budget = Column(Integer, nullable=False, default=0)
    used_tasks = Column(Integer, nullable=False, default=0)
    used_requests = Column(Integer, nullable=False, default=0)
    used_tokens = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

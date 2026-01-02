"""
LLM call model - records all LLM API calls for audit and attribution.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from apps.api.db.base import Base


class LLMCall(Base):
    __tablename__ = "llm_calls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(String(255), nullable=False, index=True)

    provider = Column(String(100), nullable=False)  # openai, anthropic, google
    model = Column(String(100), nullable=False)  # gpt-4, gpt-3.5-turbo, etc.
    role = Column(String(50), nullable=False)  # planner, solver, validator, summarizer, codereview

    prompt_hash = Column(String(64), nullable=False)  # SHA256 of prompt
    response_hash = Column(String(64), nullable=False)  # SHA256 of response
    tokens_est = Column(Integer, nullable=False, default=0)
    latency_ms = Column(Integer, nullable=False, default=0)

    policy_version = Column(String(50), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

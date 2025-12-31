"""
Approval model - records human approval decisions.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from apps.api.db.base import Base


class Approval(Base):
    __tablename__ = "approvals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action_spec_id = Column(UUID(as_uuid=True), ForeignKey("action_specs.id", ondelete="CASCADE"), nullable=False, index=True)

    approval_tier = Column(String(10), nullable=False)  # A, B, C

    requested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(String(255), nullable=True)

    reason = Column(Text, nullable=True)
    decision = Column(String(50), nullable=False)  # approved, rejected
    signature = Column(Text, nullable=True)

    policy_version = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

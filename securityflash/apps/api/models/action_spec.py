"""
ActionSpec model - represents a proposed action from an agent.
MUST-FIX B: Status enum with finite state machine enforcement.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
import enum
from apps.api.db.base import Base


class ActionStatus(str, enum.Enum):
    """ActionSpec status enum - MUST-FIX B."""
    PROPOSED = "PROPOSED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    EXECUTING = "EXECUTING"
    EXECUTED = "EXECUTED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class ActionSpec(Base):
    __tablename__ = "action_specs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)

    proposed_by = Column(String(255), nullable=False)  # agent_id

    # Action definition (JSONB)
    action_json = Column(JSONB, nullable=False)
    # Contains: tool, arguments[], target, justification, expected_evidence_type

    # Status (MUST-FIX B)
    status = Column(SQLEnum(ActionStatus), nullable=False, default=ActionStatus.PROPOSED, index=True)

    # Policy evaluation results
    risk_score = Column(Float, nullable=True)
    approval_tier = Column(String(10), nullable=True)  # A, B, C
    policy_check_result = Column(JSONB, nullable=True)

    # Approval token (JWT)
    approval_token = Column(Text, nullable=True)

    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(String(255), nullable=True)
    executed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

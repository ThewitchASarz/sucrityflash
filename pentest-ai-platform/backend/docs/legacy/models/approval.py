"""
Approval model for L2-L3 action approvals.
"""
from sqlalchemy import Column, String, Text, DateTime, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
import enum

from database import Base


class ApprovalStatus(str, enum.Enum):
    """Approval request status."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class Approval(Base):
    """
    Approval request for L2-L3 high-risk actions.

    L2: 15-minute TTL (team lead approval)
    L3: 60-minute TTL (CISO approval)
    """

    __tablename__ = "approvals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    run_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Approval request details
    risk_level = Column(String(5), nullable=False)  # L2 or L3
    justification = Column(Text, nullable=False)  # Why this action is necessary
    evidence_references = Column(JSONB, nullable=False, server_default='[]')  # [evidence_ids] supporting this request

    # Approval state
    status = Column(String(50), default=ApprovalStatus.PENDING.value, nullable=False, index=True)

    # Timing
    requested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expiry_at = Column(DateTime(timezone=True), nullable=False, index=True)  # 15 min (L2) or 60 min (L3) from requested_at

    # Approval decision
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(UUID(as_uuid=True), nullable=True)
    approval_signature = Column(Text, nullable=True)  # RSA signature proving who approved
    approval_notes = Column(Text, nullable=True)

    # Metadata
    requested_by = Column(String(50), default="AGENT", nullable=False)  # AGENT or USER

    # Constraint: Approval decision fields must be consistent with status
    __table_args__ = (
        CheckConstraint(
            """
            (status = 'PENDING') OR
            (status IN ('APPROVED', 'REJECTED') AND approved_at IS NOT NULL AND approved_by IS NOT NULL) OR
            (status = 'EXPIRED')
            """,
            name="approval_decision_check"
        ),
    )

    def __repr__(self):
        return f"<Approval {self.id} ({self.risk_level}, {self.status})>"

"""
ValidationPack Model - High-risk validation with human execution.

ValidationPacks are human-executed testing procedures for high-risk findings.
They include detailed instructions, evidence requirements, and safety constraints.
NO AUTONOMOUS EXPLOITATION.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum, JSON, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from apps.api.db.base import Base


class ValidationPackStatus(str, enum.Enum):
    """ValidationPack lifecycle states."""
    PENDING_APPROVAL = "PENDING_APPROVAL"  # Awaiting reviewer approval
    OPEN = "OPEN"                          # Approved, ready for execution
    IN_PROGRESS = "IN_PROGRESS"            # Being executed by human
    COMPLETE = "COMPLETE"                  # Execution complete with evidence
    BLOCKED = "BLOCKED"                    # Cannot proceed


class ValidationPack(Base):
    """
    ValidationPack - High-risk validation procedure for human execution.

    Contains:
    - Step-by-step instructions (engagement-safe, no exploit code)
    - Required evidence checklist
    - Parameterized command templates
    - Safety constraints and scope validation

    CRITICAL: Worker MUST refuse to execute. Human-only.
    """
    __tablename__ = "validation_packs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    finding_id = Column(UUID(as_uuid=True), ForeignKey("findings.id", ondelete="SET NULL"), nullable=True, index=True)
    action_spec_id = Column(UUID(as_uuid=True), ForeignKey("action_specs.id", ondelete="SET NULL"), nullable=True)

    # Pack metadata
    title = Column(String, nullable=False)
    category = Column(String, nullable=False)  # "AUTHZ_TEST", "INJECTION_PROBE", etc.
    risk_level = Column(String, nullable=False)  # "HIGH", "CRITICAL"

    # Instructions (human-readable, engagement-safe)
    instructions_md = Column(Text, nullable=False)  # Step-by-step markdown

    # Command templates (parameterized, not executable code)
    command_templates = Column(JSON, nullable=True, default=list)  # [{"tool": "curl", "template": "curl -X POST ..."}]

    # Evidence requirements
    required_evidence_types = Column(JSON, nullable=True, default=list)  # ["request_response", "screenshot"]
    evidence_checklist_md = Column(Text, nullable=True)  # Markdown checklist

    # Safety constraints
    target_must_match_scope = Column(Boolean, default=True, nullable=False)
    rate_limit_seconds = Column(JSON, nullable=True)  # {"requests_per_minute": 10}
    safety_notes = Column(Text, nullable=True)  # Additional safety warnings

    # Execution lifecycle
    status = Column(SQLEnum(ValidationPackStatus), nullable=False, default=ValidationPackStatus.PENDING_APPROVAL, index=True)

    # Ownership
    created_by = Column(String, nullable=False)  # agent_id that created pack
    approved_by = Column(String, nullable=True)  # reviewer who approved
    assigned_to = Column(String, nullable=True)  # human executor
    completed_by = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    approved_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Evidence attachments
    evidence_ids = Column(JSON, nullable=True, default=list)  # List of evidence UUIDs

    # Execution notes
    execution_notes = Column(Text, nullable=True)

    # Relationships
    run = relationship("Run", back_populates="validation_packs")
    finding = relationship("Finding", back_populates="validation_packs")
    action_spec = relationship("ActionSpec")

    def __repr__(self):
        return f"<ValidationPack {self.id} status={self.status.value} title='{self.title}'>"

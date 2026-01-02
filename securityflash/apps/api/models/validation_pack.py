"""
Validation Pack model - manual execution workflow for risky actions.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum
from apps.api.db.base import Base


class ValidationRiskLevel(str, enum.Enum):
    LOW = "LOW"
    MED = "MED"
    HIGH = "HIGH"


class ValidationStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"
    ABORTED = "ABORTED"


class ValidationPack(Base):
    __tablename__ = "validation_packs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    scope_id = Column(UUID(as_uuid=True), ForeignKey("scopes.id", ondelete="CASCADE"), nullable=False, index=True)
    finding_id = Column(UUID(as_uuid=True), ForeignKey("findings.id", ondelete="SET NULL"), nullable=True, index=True)

    title = Column(String(255), nullable=False)
    risk_level = Column(SQLEnum(ValidationRiskLevel), nullable=False)
    instructions_md = Column(Text, nullable=False)
    command_templates = Column(JSONB, nullable=False, default=list)
    stop_conditions = Column(JSONB, nullable=False, default=list)
    required_evidence = Column(JSONB, nullable=False, default=list)
    status = Column(SQLEnum(ValidationStatus), nullable=False, default=ValidationStatus.DRAFT, index=True)
    approved_by_reviewer = Column(String(255), nullable=True)
    approved_by_engineer = Column(String(255), nullable=True)
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    abort_reason = Column(Text, nullable=True)

    run = relationship("Run", back_populates="validation_packs")
    evidence_items = relationship("Evidence", back_populates="validation_pack")

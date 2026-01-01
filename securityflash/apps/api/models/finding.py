"""
Finding Model - Evidence-backed security findings with review workflow.

Findings require evidence and reproducible steps for CONFIRMED status.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from apps.api.db.base import Base


class FindingSeverity(str, enum.Enum):
    """Finding severity levels."""
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FindingCategory(str, enum.Enum):
    """Finding categorization."""
    RECON = "RECON"
    CONFIG = "CONFIG"
    EXPOSURE = "EXPOSURE"
    AUTHZ = "AUTHZ"
    INJECTION = "INJECTION"
    CRYPTO = "CRYPTO"
    NETWORK = "NETWORK"
    OTHER = "OTHER"


class FindingStatus(str, enum.Enum):
    """Finding review workflow states."""
    DRAFT = "DRAFT"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


class Finding(Base):
    """
    Finding - Evidence-backed security finding with review workflow.

    Lifecycle: DRAFT → NEEDS_REVIEW → CONFIRMED/REJECTED
    CONFIRMED requires evidence_ids and reproducibility_md.
    """
    __tablename__ = "findings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    scope_id = Column(UUID(as_uuid=True), ForeignKey("scopes.id", ondelete="CASCADE"), nullable=False)

    # Finding metadata
    title = Column(String, nullable=False)
    severity = Column(SQLEnum(FindingSeverity), nullable=False, index=True)
    category = Column(SQLEnum(FindingCategory), nullable=False, index=True)
    affected_target = Column(String, nullable=False)

    # Finding content
    description_md = Column(Text, nullable=False)
    reproducibility_md = Column(Text, nullable=True)

    # Evidence backing
    evidence_ids = Column(JSON, nullable=True, default=list)  # array of UUID strings

    # Review workflow
    status = Column(SQLEnum(FindingStatus), nullable=False, default=FindingStatus.DRAFT, index=True)
    created_by = Column(String, nullable=True)  # agent_id or user_id
    reviewer_id = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    run = relationship("Run", back_populates="findings")
    project = relationship("Project")
    scope = relationship("Scope")
    manual_tasks = relationship("ManualValidationTask", back_populates="finding", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Finding {self.id} severity={self.severity.value} status={self.status.value} title='{self.title}'>"

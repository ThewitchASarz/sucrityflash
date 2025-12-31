"""
Audit bundle job model for compliance export.
"""
from sqlalchemy import Column, String, Text, TIMESTAMP, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ForeignKey
from sqlalchemy.sql import func
from database import Base
import uuid
import enum


class JobStatus(str, enum.Enum):
    """Async job status."""
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    READY = "READY"
    FAILED = "FAILED"


class AuditBundleJob(Base):
    """
    Audit bundle generation job.

    Bundle contains:
    - logs.json (all audit events)
    - evidence-hashes.csv (evidence integrity verification)
    - report.html (validated findings report)
    - metadata.json (run metadata, timestamps, actors)
    """
    __tablename__ = "audit_bundle_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)

    # Job status
    status = Column(SQLEnum(JobStatus), default=JobStatus.QUEUED, nullable=False, index=True)

    # Output
    artifact_uri = Column(String(500))  # S3 URI to zip file
    artifact_hash = Column(String(64))  # SHA-256

    # Error handling
    error_message = Column(Text)

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(TIMESTAMP(timezone=True))

    def __repr__(self):
        return f"<AuditBundleJob(id={self.id}, run_id={self.run_id}, status={self.status})>"

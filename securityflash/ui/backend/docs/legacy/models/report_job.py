"""
Report job model for asynchronous report generation.
"""
from sqlalchemy import Column, String, Text, Integer, TIMESTAMP, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ForeignKey
from sqlalchemy.sql import func
from database import Base
import uuid
import enum


class ReportFormat(str, enum.Enum):
    """Report output formats."""
    HTML = "HTML"
    PDF = "PDF"


class JobStatus(str, enum.Enum):
    """Async job status."""
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    READY = "READY"
    FAILED = "FAILED"


class ReportJob(Base):
    """
    Asynchronous report generation job.

    Report includes validated findings only, with OWASP mapping and compliance evidence.
    """
    __tablename__ = "report_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)

    # Job configuration
    format = Column(SQLEnum(ReportFormat), nullable=False)
    include_evidence = Column(String(10), default="true")  # Include evidence details

    # Job status
    status = Column(SQLEnum(JobStatus), default=JobStatus.QUEUED, nullable=False, index=True)
    progress_percent = Column(Integer, default=0)

    # Output
    artifact_uri = Column(String(500))  # S3 URI
    artifact_hash = Column(String(64))  # SHA-256

    # Error handling
    error_message = Column(Text)

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(TIMESTAMP(timezone=True))

    def __repr__(self):
        return f"<ReportJob(id={self.id}, run_id={self.run_id}, status={self.status})>"

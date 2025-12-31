"""
Evidence model for immutable, hash-chained evidence storage.
"""
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy import event
import uuid
import enum

from database import Base


class ActorType(str, enum.Enum):
    """Actor type for evidence attribution."""
    USER = "USER"
    AGENT = "AGENT"
    SYSTEM = "SYSTEM"


class EvidenceType(str, enum.Enum):
    """Evidence content type."""
    COMMAND_OUTPUT = "COMMAND_OUTPUT"
    SCREENSHOT = "SCREENSHOT"
    NETWORK_CAPTURE = "NETWORK_CAPTURE"
    LOG_FILE = "LOG_FILE"
    OTHER = "OTHER"


class Evidence(Base):
    """
    Immutable evidence object with hash chaining.

    Each evidence object is:
    - Hash-chained to prior evidence (prior_evidence_hash)
    - Digitally signed by backend (signature)
    - Stored in S3/MinIO (s3_path)
    - Immutable (UPDATE trigger prevents modifications)
    """

    __tablename__ = "evidence"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    action_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Actor attribution
    created_by_actor_type = Column(String(50), nullable=False)  # USER, AGENT, SYSTEM
    created_by_actor_id = Column(String(255), nullable=False)  # user_id or agent name

    # Evidence content
    evidence_type = Column(String(50), nullable=False)  # COMMAND_OUTPUT, SCREENSHOT, etc.
    content_hash = Column(String(64), nullable=False, index=True)  # SHA-256 of evidence content
    prior_evidence_hash = Column(String(64), nullable=True)  # Hash of previous evidence (chain)

    # Storage
    s3_path = Column(Text, nullable=False)  # s3://bucket/evidence/{run_id}/{action_id}/{hash}.json

    # Metadata
    evidence_metadata = Column(JSONB, nullable=False, server_default='{}')  # {action_description, tool, target, risk_level, scope_validated, autonomous}

    # Signature (backend key signs evidence hash)
    signature = Column(Text, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    def __repr__(self):
        return f"<Evidence {self.id} ({self.evidence_type}, hash: {self.content_hash[:16]}...)>"


# Trigger to prevent evidence updates (immutability enforcement)
# This will be created via Alembic migration
# CREATE OR REPLACE FUNCTION prevent_evidence_update()
# RETURNS TRIGGER AS $$
# BEGIN
#     RAISE EXCEPTION 'Evidence records are immutable and cannot be updated';
# END;
# $$ LANGUAGE plpgsql;
#
# CREATE TRIGGER evidence_update_prevention
# BEFORE UPDATE ON evidence
# FOR EACH ROW
# EXECUTE FUNCTION prevent_evidence_update();

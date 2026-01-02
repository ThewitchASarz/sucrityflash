"""
Evidence model - immutable record of tool execution results.
MUST-FIX C: No delete operations allowed.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from apps.api.db.base import Base


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="RESTRICT"), nullable=False, index=True)
    validation_pack_id = Column(UUID(as_uuid=True), ForeignKey("validation_packs.id", ondelete="SET NULL"), nullable=True, index=True)

    evidence_type = Column(String(100), nullable=False)  # command_output, llm_response, etc.

    # MinIO storage
    artifact_uri = Column(String(500), nullable=False)  # s3://bucket/path
    artifact_hash = Column(String(64), nullable=False)  # SHA256

    generated_by = Column(String(255), nullable=False)  # worker, agent_id
    generated_at = Column(DateTime(timezone=True), nullable=False)

    validation_status = Column(String(50), nullable=False, default="PENDING")

    # Metadata (JSONB) - renamed to evidence_metadata to avoid SQLAlchemy reserved name conflict
    evidence_metadata = Column(JSONB, nullable=False)
    # Contains: tool_used, tool_version, returncode, stdout, stderr, model_attribution

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    validation_pack = relationship("ValidationPack", back_populates="evidence_items")

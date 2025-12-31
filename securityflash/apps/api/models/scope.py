"""
Scope model - defines immutable boundaries for a project.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
from apps.api.db.base import Base


class Scope(Base):
    __tablename__ = "scopes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    # Scope definition (JSONB for flexibility)
    scope_json = Column(JSONB, nullable=False)
    # Contains: scope_type, targets[], excluded_targets[], attack_vectors_allowed[],
    # attack_vectors_prohibited[], approved_tools[], time_restrictions

    # Immutability enforcement
    locked_at = Column(DateTime(timezone=True), nullable=True)
    locked_by = Column(String(255), nullable=True)
    lock_signature = Column(Text, nullable=True)  # Cryptographic signature

    version = Column(Integer, nullable=False, default=1)
    status = Column(String(50), nullable=False, default="draft")  # draft, locked

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

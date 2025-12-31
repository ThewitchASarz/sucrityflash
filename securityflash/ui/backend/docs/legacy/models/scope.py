"""
Scope model for defining test boundaries and rules of engagement.
"""
from sqlalchemy import Column, Text, DateTime, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from database import Base


class Scope(Base):
    """
    Scope model with dual-signature lock for immutability.

    Scope defines:
    - target_systems: List of IPs, domains, CIDR ranges to test
    - excluded_systems: List of systems explicitly excluded
    - forbidden_methods: List of methods not allowed (e.g., social_engineering, dos)
    - roe: Rules of engagement (max_concurrent, testing_window, etc.)
    """

    __tablename__ = "scopes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Scope definition (JSONB for flexibility)
    target_systems = Column(JSONB, nullable=False)  # ["192.168.1.0/24", "example.com", ...]
    excluded_systems = Column(JSONB, nullable=False, server_default='[]')  # ["192.168.1.254", ...]
    forbidden_methods = Column(JSONB, nullable=False, server_default='[]')  # ["social_engineering", "dos", ...]

    # Rules of engagement
    roe = Column(JSONB, nullable=False, server_default='{}')  # {max_concurrent: 10, allows_data_exfiltration: false, ...}

    # Scope lock (dual signature required)
    locked_at = Column(DateTime(timezone=True), nullable=True)
    locked_by_coordinator = Column(UUID(as_uuid=True), nullable=True)
    locked_by_approver = Column(UUID(as_uuid=True), nullable=True)
    coordinator_signature = Column(Text, nullable=True)  # RSA-SHA256 signature
    approver_signature = Column(Text, nullable=True)  # RSA-SHA256 signature

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Constraint: Either all lock fields are NULL or all are NOT NULL
    __table_args__ = (
        CheckConstraint(
            """
            (locked_at IS NULL AND locked_by_coordinator IS NULL AND locked_by_approver IS NULL) OR
            (locked_at IS NOT NULL AND locked_by_coordinator IS NOT NULL AND locked_by_approver IS NOT NULL)
            """,
            name="scope_locked_check"
        ),
    )

    def __repr__(self):
        lock_status = "LOCKED" if self.locked_at else "UNLOCKED"
        return f"<Scope {self.id} ({lock_status})>"

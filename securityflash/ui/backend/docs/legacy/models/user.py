"""
User model for authentication and role-based access control.
"""
from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from datetime import datetime
import uuid
import enum

from database import Base


class UserRole(str, enum.Enum):
    """User roles for RBAC."""
    COORDINATOR = "COORDINATOR"
    APPROVER = "APPROVER"
    OPERATOR = "OPERATOR"
    TEAM_LEAD = "TEAM_LEAD"
    CISO = "CISO"
    AUDITOR = "AUDITOR"


class User(Base):
    """User model with role-based access control."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


class UserSigningKey(Base):
    """RSA public keys for digital signature verification."""

    __tablename__ = "user_signing_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # RSA key data
    public_key = Column(String, nullable=False)  # PEM-encoded RSA public key
    fingerprint = Column(String(64), unique=True, nullable=False)  # SHA-256 fingerprint

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<UserSigningKey {self.fingerprint[:16]}... for user {self.user_id}>"

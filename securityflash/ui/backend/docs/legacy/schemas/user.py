"""
Pydantic schemas for user-related requests and responses.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from uuid import UUID
from models.user import UserRole


# Request schemas
class UserRegister(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    full_name: str = Field(..., min_length=1, max_length=255)
    role: UserRole


class UserLogin(BaseModel):
    """User login request."""
    email: EmailStr
    password: str


class SigningKeyCreate(BaseModel):
    """Request to generate RSA signing key pair."""
    pass  # No input required, key pair generated automatically


# Response schemas
class UserResponse(BaseModel):
    """User response (without password)."""
    id: UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class SigningKeyResponse(BaseModel):
    """RSA public key response."""
    id: UUID
    user_id: UUID
    public_key: str
    fingerprint: str
    created_at: datetime

    class Config:
        from_attributes = True


class SigningKeyWithPrivate(BaseModel):
    """RSA key pair response (includes private key - only returned once)."""
    id: UUID
    user_id: UUID
    public_key: str
    private_key: str  # ONLY returned once during generation
    fingerprint: str
    created_at: datetime
    warning: str = "CRITICAL: Save private_key securely. It will not be shown again."

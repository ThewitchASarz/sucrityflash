"""
Pydantic schemas for scope-related requests and responses.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# Request schemas
class ScopeCreate(BaseModel):
    """Scope creation request."""
    project_id: str
    target_systems: list[str] = Field(..., description="List of IPs, domains, CIDR ranges to test")
    excluded_systems: list[str] = Field(default_factory=list, description="List of systems explicitly excluded")
    forbidden_methods: list[str] = Field(default_factory=list, description="List of methods not allowed (e.g., social_engineering, dos)")
    roe: dict = Field(default_factory=dict, description="Rules of engagement (max_concurrent, testing_window, etc.)")


class ScopeLock(BaseModel):
    """Scope lock request (dual signature)."""
    coordinator_signature: str = Field(..., description="RSA-SHA256 signature from coordinator")
    approver_signature: str = Field(..., description="RSA-SHA256 signature from approver")


# Response schemas
class ScopeResponse(BaseModel):
    """Scope response."""
    id: str
    project_id: str
    target_systems: list[str]
    excluded_systems: list[str]
    forbidden_methods: list[str]
    roe: dict

    # Lock information
    locked_at: Optional[datetime]
    locked_by_coordinator: Optional[str]
    locked_by_approver: Optional[str]
    is_locked: bool

    # Timestamps
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_lock_status(cls, obj):
        """Create response with computed is_locked field."""
        data = {
            "id": str(obj.id),
            "project_id": str(obj.project_id),
            "target_systems": obj.target_systems,
            "excluded_systems": obj.excluded_systems,
            "forbidden_methods": obj.forbidden_methods,
            "roe": obj.roe,
            "locked_at": obj.locked_at,
            "locked_by_coordinator": str(obj.locked_by_coordinator) if obj.locked_by_coordinator else None,
            "locked_by_approver": str(obj.locked_by_approver) if obj.locked_by_approver else None,
            "is_locked": obj.locked_at is not None,
            "created_at": obj.created_at,
            "updated_at": obj.updated_at,
        }
        return cls(**data)

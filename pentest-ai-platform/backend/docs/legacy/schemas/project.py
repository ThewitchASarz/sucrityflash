"""
Pydantic schemas for project-related requests and responses.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from models.project import ProjectStatus


# Request schemas
class ProjectCreate(BaseModel):
    """Project creation request."""
    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    customer_name: str = Field(..., min_length=1, max_length=255, description="Customer/client name")
    description: Optional[str] = Field(None, description="Project description")


class ProjectUpdate(BaseModel):
    """Project update request."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    customer_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None


# Response schemas
class ProjectResponse(BaseModel):
    """Project response."""
    id: str
    name: str
    customer_name: str
    description: Optional[str]
    status: ProjectStatus
    created_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """List of projects response."""
    projects: list[ProjectResponse]
    total: int

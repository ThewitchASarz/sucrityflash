"""
Project schemas (Pydantic).
"""
from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import Optional


class ProjectCreate(BaseModel):
    name: str
    customer_id: str
    target_url: str
    primary_target_url: Optional[str] = None  # Used to prefill first scope targets
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    rules_of_engagement: Optional[str] = None
    created_by: str = "system"


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    customer_id: Optional[str] = None
    target_url: Optional[str] = None
    primary_target_url: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    rules_of_engagement: Optional[str] = None


class ProjectResponse(BaseModel):
    id: UUID4
    name: str
    customer_id: str
    target_url: Optional[str]
    primary_target_url: Optional[str]
    status: str
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    rules_of_engagement: Optional[str]
    created_at: datetime
    updated_at: datetime
    created_by: str
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True

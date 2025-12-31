"""
Project schemas (Pydantic).
"""
from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import Optional


class ProjectCreate(BaseModel):
    name: str
    customer_id: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    rules_of_engagement: Optional[str] = None
    created_by: str = "system"


class ProjectResponse(BaseModel):
    id: UUID4
    name: str
    customer_id: str
    status: str
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    rules_of_engagement: Optional[str]
    created_at: datetime
    updated_at: datetime
    created_by: str

    class Config:
        from_attributes = True

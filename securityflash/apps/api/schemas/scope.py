"""
Scope schemas (Pydantic).
"""
from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import Optional, List, Dict, Any


class Target(BaseModel):
    type: str  # domain, ip, cidr
    value: str
    criticality: str = "MEDIUM"  # HIGH, MEDIUM, LOW


class TimeRestrictions(BaseModel):
    start_time: Optional[str] = None  # "09:00 UTC"
    end_time: Optional[str] = None  # "17:00 UTC"
    blackout_dates: List[str] = []


class ScopeCreate(BaseModel):
    scope_type: str  # network, web_app, api, mobile
    targets: List[Target]
    excluded_targets: List[Target] = []
    attack_vectors_allowed: List[str]
    attack_vectors_prohibited: List[str]
    approved_tools: List[str]
    time_restrictions: Optional[TimeRestrictions] = None


class ScopeLock(BaseModel):
    locked_by: str
    signature: str


class ScopeResponse(BaseModel):
    id: UUID4
    project_id: UUID4
    scope_json: Dict[str, Any]
    locked_at: Optional[datetime]
    locked_by: Optional[str]
    lock_signature: Optional[str]
    version: int
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

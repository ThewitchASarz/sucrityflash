"""
ActionSpec schemas (Pydantic).
"""
from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import Optional, List, Dict, Any


class ActionSpecCreate(BaseModel):
    tool: str
    arguments: List[str]
    target: str
    proposed_by: str
    justification: Optional[str] = None
    expected_evidence_type: str = "command_output"


class ActionSpecResponse(BaseModel):
    id: UUID4
    run_id: UUID4
    proposed_by: str
    action_json: Dict[str, Any]
    status: str
    risk_score: Optional[float]
    approval_tier: Optional[str]
    policy_check_result: Optional[Dict[str, Any]]
    approval_token: Optional[str]
    approved_at: Optional[datetime]
    approved_by: Optional[str]
    executed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True

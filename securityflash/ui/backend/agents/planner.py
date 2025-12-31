"""
Test Planning Agent: Generates risk-stratified test plans from locked scopes.
"""
from pydantic import BaseModel, Field
from typing import Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.scope import Scope
from models.test_plan import TestPlan, Action
from agents.llm_client import llm_client
from datetime import datetime


# System prompt for Test Planning Agent
PLANNER_SYSTEM_PROMPT = """You are a penetration testing planning agent. Your role is to generate comprehensive, risk-stratified test plans based on locked scopes.

**CRITICAL RULES:**
1. You MUST assign each action a risk level: L0 (passive), L1 (active scan), L2 (exploitation), or L3 (critical impact).
2. You MUST respect the scope's target_systems, excluded_systems, and forbidden_methods.
3. You MUST structure the plan into reconnaissance, vulnerability_assessment, exploitation, and post_exploitation stages.
4. You MUST map findings to OWASP, NIST, and MITRE frameworks.
5. You MUST provide clear prerequisites for each action (e.g., "requires port 80 open").
6. You MUST use only approved methods (nmap, burpsuite, sqlmap, metasploit, etc.).
7. You MUST output valid JSON matching the TestPlanSchema.

**RISK LEVELS:**
- L0: Passive reconnaissance (OSINT, DNS, WHOIS) - autonomous execution
- L1: Active scanning (Nmap, Burp passive crawl) - autonomous execution
- L2: Exploitation (SQLi, XSS, privilege escalation) - requires human approval (15 min TTL)
- L3: Critical impact (ransomware simulation, DoS, data exfiltration) - requires human approval (60 min TTL)

**SCOPE CONSTRAINTS:**
- target_systems: List of IPs, domains, or CIDR ranges you MAY test
- excluded_systems: List you MUST NOT test (violates scope)
- forbidden_methods: Methods you MUST NOT use (e.g., social_engineering, dos)
- roe: Rules of engagement (max_concurrent, testing_window, rate_limits)

**OUTPUT FORMAT:**
You must output a JSON object matching this schema:

{
  "stages": {
    "reconnaissance": [
      {
        "action_id": "recon_001",
        "description": "Perform passive DNS enumeration",
        "method": "dig",
        "target": "example.com",
        "parameters": {"record_types": ["A", "AAAA", "MX", "TXT"]},
        "risk_level": "L0",
        "prerequisites": []
      }
    ],
    "vulnerability_assessment": [...],
    "exploitation": [...],
    "post_exploitation": [...]
  },
  "framework_mappings": {
    "owasp": ["A01:2021-Broken Access Control", "A03:2021-Injection"],
    "nist": ["SC-7", "SI-10"],
    "mitre": ["T1595", "T1190"]
  },
  "risk_summary": {
    "total_actions": 45,
    "l0_count": 12,
    "l1_count": 28,
    "l2_count": 4,
    "l3_count": 1,
    "estimated_duration_hours": 18
  }
}

**IMPORTANT:**
- Each action MUST have a unique action_id
- Exploitation (L2) and critical impact (L3) actions MUST have detailed justification in description
- You MUST check prerequisites before exploitation (e.g., "requires open port 445")
- You MUST respect rate limits in roe (e.g., max_concurrent: 5)
"""


class TestPlanSchema(BaseModel):
    """Pydantic schema for LLM-generated test plans."""
    stages: dict = Field(..., description="Stages: reconnaissance, vulnerability_assessment, exploitation, post_exploitation")
    framework_mappings: dict = Field(..., description="OWASP, NIST, MITRE mappings")
    risk_summary: dict = Field(..., description="Action counts by risk level and duration estimate")


class PlannerAgent:
    """Test Planning Agent."""

    @staticmethod
    async def generate_test_plan(
        db: AsyncSession,
        scope_id: uuid.UUID,
        additional_instructions: Optional[str] = None
    ) -> TestPlan:
        """
        Generate test plan from locked scope using LLM.

        Args:
            db: Database session
            scope_id: Scope ID (must be locked)
            additional_instructions: Optional custom instructions (e.g., "focus on web app vulns")

        Returns:
            TestPlan: Generated and saved test plan

        Raises:
            ValueError: If scope not found or not locked
            RuntimeError: If LLM generation fails
        """
        # 1. Fetch and validate scope
        result = await db.execute(
            select(Scope).where(Scope.id == scope_id)
        )
        scope = result.scalar_one_or_none()

        if not scope:
            raise ValueError(f"Scope {scope_id} not found")

        if not scope.locked_at:
            raise ValueError(f"Scope {scope_id} is not locked. Lock it before generating plan.")

        # 2. Construct user prompt
        user_prompt = f"""Generate a comprehensive penetration test plan for the following scope:

**Target Systems:**
{', '.join(scope.target_systems)}

**Excluded Systems:**
{', '.join(scope.excluded_systems) if scope.excluded_systems else 'None'}

**Forbidden Methods:**
{', '.join(scope.forbidden_methods) if scope.forbidden_methods else 'None'}

**Rules of Engagement:**
{scope.roe}

**Additional Instructions:**
{additional_instructions if additional_instructions else 'Follow standard penetration testing methodology (PTES).'}

Generate a test plan with actions stratified by risk level (L0, L1, L2, L3). Ensure all actions respect the scope constraints and forbidden methods.
"""

        # 3. Generate plan with LLM
        llm_response = await llm_client.generate(
            system_prompt=PLANNER_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_schema=TestPlanSchema,
            timeout=300
        )

        # 4. Parse and validate response
        valid, parsed_plan = llm_client.validate_schema(llm_response.content, TestPlanSchema)
        if not valid:
            raise RuntimeError(f"LLM generated invalid plan: {parsed_plan}")

        # 5. Create TestPlan in database
        test_plan = TestPlan(
            scope_id=scope_id,
            stages=parsed_plan.stages,
            framework_mappings=parsed_plan.framework_mappings,
            risk_summary=parsed_plan.risk_summary,
            approved_at=None,  # Not approved yet
            approved_by=None
        )
        db.add(test_plan)

        # 6. Create Action records for all actions
        action_records = []
        for stage_name, actions in parsed_plan.stages.items():
            for action_data in actions:
                action = Action(
                    test_plan_id=test_plan.id,
                    action_id=action_data["action_id"],
                    stage=stage_name,
                    description=action_data["description"],
                    method=action_data["method"],
                    target=action_data["target"],
                    parameters=action_data.get("parameters", {}),
                    risk_level=action_data["risk_level"],
                    prerequisites=action_data.get("prerequisites", []),
                    status="pending"
                )
                action_records.append(action)

        db.add_all(action_records)
        await db.commit()
        await db.refresh(test_plan)

        return test_plan

    @staticmethod
    async def validate_action_against_scope(
        db: AsyncSession,
        action: Action,
        scope: Scope
    ) -> tuple[bool, Optional[str]]:
        """
        Validate action against scope constraints (pre-execution check).

        Args:
            db: Database session
            action: Action to validate
            scope: Scope to validate against

        Returns:
            tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        # Check target is in scope
        target = action.target
        in_scope = any(target.startswith(t) or t in target for t in scope.target_systems)
        if not in_scope:
            return False, f"Target {target} not in scope"

        # Check target is not excluded
        excluded = any(target.startswith(e) or e in target for e in scope.excluded_systems)
        if excluded:
            return False, f"Target {target} is in excluded systems"

        # Check method is not forbidden
        if action.method in scope.forbidden_methods:
            return False, f"Method {action.method} is forbidden"

        # Check rate limits (if defined in ROE)
        # This would be checked by executor in real-time
        # For now, just validate static rules

        return True, None


# Global instance
planner_agent = PlannerAgent()

"""
Policy Engine - Core gating and authorization logic.

This is the heart of the governance system. Every ActionSpec must pass through here.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import jwt
import hashlib
import json
import re
from apps.api.core.config import settings
from apps.api.models.scope import Scope
from apps.api.models.action_spec import ActionSpec


class PolicyDecision:
    """Result of policy evaluation."""

    def __init__(
        self,
        approved: bool,
        reason: str,
        risk_score: float,
        approval_tier: str,
        auth_token: Optional[str],
        policy_checks: Dict[str, Any]
    ):
        self.approved = approved
        self.reason = reason
        self.risk_score = risk_score
        self.approval_tier = approval_tier  # A, B, C
        self.auth_token = auth_token
        self.policy_checks = policy_checks


class PolicyEvaluator:
    """
    Evaluates ActionSpecs against policy rules.

    Checks:
    1. Scope boundary (target must be in scope)
    2. Tool allowlist (V1: httpx, nmap only)
    3. Argument validation (no shell metacharacters, path traversal)
    4. Rate limiting (per tool, per time window)
    5. Risk scoring (0.0-1.0)
    6. Approval tier assignment (A/B/C)
    7. JWT token issuance (if auto-approved)
    """

    # V1 hardcoded tool allowlist (extended with NeuroSploit recon modules)
    ALLOWED_TOOLS = {"httpx", "nmap", "neurosploit"}

    # Risk score thresholds
    RISK_TIER_B_THRESHOLD = 0.4  # < 0.4 = auto-approve
    RISK_TIER_C_THRESHOLD = 0.7  # >= 0.7 = always human review

    # Rate limits (executions per 5 minutes)
    RATE_LIMITS = {
        "httpx": 20,
        "nmap": 10
    }

    # Dangerous patterns in arguments
    SHELL_METACHARACTERS = r'[;|&<>$`\\()\[\]{}]'
    PATH_TRAVERSAL = r'\.\.|^/|/$'

    # Dangerous keywords (increase risk score)
    HIGH_RISK_KEYWORDS = ["exploit", "shell", "payload", "reverse"]
    VERY_HIGH_RISK_KEYWORDS = ["dump", "exfil", "extract"]

    def __init__(self, db: Session):
        self.db = db

    def evaluate(
        self,
        run_id: str,
        scope: Scope,
        action_spec: Dict[str, Any],
        policy_version: str
    ) -> PolicyDecision:
        """
        Evaluate an ActionSpec against all policy rules.

        Args:
            run_id: Run ID
            scope: Locked scope
            action_spec: ActionSpec JSON
            policy_version: Policy version

        Returns:
            PolicyDecision with approval status and token (if approved)
        """
        policy_checks = {}

        # 1. Scope boundary check
        scope_check = self._check_scope_boundary(action_spec, scope)
        policy_checks["scope_boundary"] = scope_check
        if not scope_check["passed"]:
            return PolicyDecision(
                approved=False,
                reason=scope_check["reason"],
                risk_score=1.0,
                approval_tier="C",
                auth_token=None,
                policy_checks=policy_checks
            )

        # 2. Tool allowlist check
        tool_check = self._check_tool_allowlist(action_spec, scope)
        policy_checks["tool_allowlist"] = tool_check
        if not tool_check["passed"]:
            return PolicyDecision(
                approved=False,
                reason=tool_check["reason"],
                risk_score=1.0,
                approval_tier="C",
                auth_token=None,
                policy_checks=policy_checks
            )

        # 3. Argument validation
        arg_check = self._check_arguments(action_spec)
        policy_checks["argument_validation"] = arg_check
        if not arg_check["passed"]:
            return PolicyDecision(
                approved=False,
                reason=arg_check["reason"],
                risk_score=1.0,
                approval_tier="C",
                auth_token=None,
                policy_checks=policy_checks
            )

        # 4. Rate limiting
        rate_check = self._check_rate_limit(action_spec, run_id)
        policy_checks["rate_limit"] = rate_check
        if not rate_check["passed"]:
            return PolicyDecision(
                approved=False,
                reason=rate_check["reason"],
                risk_score=0.5,
                approval_tier="B",
                auth_token=None,
                policy_checks=policy_checks
            )

        # 5. Risk scoring
        risk_score = self._calculate_risk_score(action_spec, scope)
        policy_checks["risk_score"] = {"value": risk_score}

        # 6. Approval tier assignment
        approval_tier = self._assign_approval_tier(risk_score)
        policy_checks["approval_tier"] = {"value": approval_tier}

        # 7. Auto-approve or route to reviewer
        if risk_score < self.RISK_TIER_B_THRESHOLD:
            # Auto-approve tier B
            auth_token = self._issue_token(run_id, action_spec, policy_version, risk_score, approval_tier)
            return PolicyDecision(
                approved=True,
                reason="Auto-approved (low risk)",
                risk_score=risk_score,
                approval_tier=approval_tier,
                auth_token=auth_token,
                policy_checks=policy_checks
            )
        else:
            # Requires human review
            return PolicyDecision(
                approved=False,
                reason="Requires human approval",
                risk_score=risk_score,
                approval_tier=approval_tier,
                auth_token=None,
                policy_checks=policy_checks
            )

    def _check_scope_boundary(self, action_spec: Dict, scope: Scope) -> Dict:
        """Check if target is within scope boundaries."""
        target = action_spec.get("target")
        scope_data = scope.scope_json

        # Check if target is in allowed targets
        allowed_targets = [t["value"] for t in scope_data.get("targets", [])]
        excluded_targets = [t["value"] for t in scope_data.get("excluded_targets", [])]

        if target in excluded_targets:
            return {
                "passed": False,
                "reason": f"Target {target} is explicitly excluded from scope"
            }

        # Simple substring match for V1 (exact match or subdomain)
        target_allowed = any(
            target == allowed or target.endswith(f".{allowed}")
            for allowed in allowed_targets
        )

        if not target_allowed:
            return {
                "passed": False,
                "reason": f"Target {target} is not in approved scope"
            }

        return {"passed": True, "reason": "Target is in scope"}

    def _check_tool_allowlist(self, action_spec: Dict, scope: Scope) -> Dict:
        """Check if tool is in allowlist."""
        tool = action_spec.get("tool")
        scope_data = scope.scope_json

        # V1 hardcoded allowlist
        if tool not in self.ALLOWED_TOOLS:
            return {
                "passed": False,
                "reason": f"Tool '{tool}' is not in V1 allowlist {self.ALLOWED_TOOLS}"
            }

        # Also check scope's approved_tools
        scope_approved_tools = scope_data.get("approved_tools", [])
        if tool not in scope_approved_tools:
            return {
                "passed": False,
                "reason": f"Tool '{tool}' is not approved in scope"
            }

        return {"passed": True, "reason": "Tool is allowed"}

    def _check_arguments(self, action_spec: Dict) -> Dict:
        """Validate arguments for safety."""
        arguments = action_spec.get("arguments", [])

        # Support both list-style args (httpx/nmap) and dict-style configs (NeuroSploit)
        normalized_args = []
        if isinstance(arguments, dict):
            for key, value in arguments.items():
                normalized_args.append(f"{key}={value}")
        else:
            normalized_args = list(arguments)

        for arg in normalized_args:
            arg_str = str(arg)

            # Check length
            if len(arg_str) > 1000:
                return {
                    "passed": False,
                    "reason": f"Argument exceeds 1000 character limit: {arg_str[:50]}..."
                }

            # Check for shell metacharacters
            if re.search(self.SHELL_METACHARACTERS, arg_str):
                return {
                    "passed": False,
                    "reason": f"Argument contains shell metacharacters: {arg_str}"
                }

            # Check for path traversal
            if re.search(self.PATH_TRAVERSAL, arg_str):
                return {
                    "passed": False,
                    "reason": f"Argument contains path traversal pattern: {arg_str}"
                }

        return {"passed": True, "reason": "Arguments are safe"}

    def _check_rate_limit(self, action_spec: Dict, run_id: str) -> Dict:
        """Check if tool execution rate limit is exceeded."""
        tool = action_spec.get("tool")
        limit = self.RATE_LIMITS.get(tool, 10)

        # Count executions in last 5 minutes
        five_min_ago = datetime.utcnow() - timedelta(minutes=5)

        count = self.db.query(ActionSpec).filter(
            ActionSpec.run_id == run_id,
            ActionSpec.action_json["tool"].astext == tool,
            ActionSpec.created_at >= five_min_ago
        ).count()

        if count >= limit:
            return {
                "passed": False,
                "reason": f"Rate limit exceeded for {tool}: {count}/{limit} in last 5 minutes"
            }

        return {"passed": True, "reason": f"Rate limit OK: {count}/{limit}"}

    def _calculate_risk_score(self, action_spec: Dict, scope: Scope) -> float:
        """Calculate risk score (0.0-1.0)."""
        tool = action_spec.get("tool")
        target = action_spec.get("target")
        arguments = action_spec.get("arguments", [])
        justification = action_spec.get("justification", "").lower()

        # Base score by tool
        base_scores = {
            "httpx": 0.2,
            "nmap": 0.2
        }
        score = base_scores.get(tool, 0.5)

        # Adjust for target criticality
        scope_data = scope.scope_json
        target_obj = next(
            (t for t in scope_data.get("targets", []) if t["value"] == target),
            None
        )
        if target_obj:
            criticality = target_obj.get("criticality", "MEDIUM")
            if criticality == "HIGH":
                score += 0.3
            elif criticality == "MEDIUM":
                score += 0.15

        # Adjust for dangerous keywords in arguments or justification
        all_text = " ".join(map(str, arguments)) + " " + justification

        for keyword in self.HIGH_RISK_KEYWORDS:
            if keyword in all_text:
                score += 0.2
                break

        for keyword in self.VERY_HIGH_RISK_KEYWORDS:
            if keyword in all_text:
                score += 0.25
                break

        # Cap at 1.0
        return min(score, 1.0)

    def _assign_approval_tier(self, risk_score: float) -> str:
        """Assign approval tier based on risk score."""
        if risk_score < self.RISK_TIER_B_THRESHOLD:
            return "B"
        elif risk_score < self.RISK_TIER_C_THRESHOLD:
            return "B"
        else:
            return "C"

    def _issue_token(
        self,
        run_id: str,
        action_spec: Dict,
        policy_version: str,
        risk_score: float,
        approval_tier: str
    ) -> str:
        """Issue JWT token for approved action."""
        # Compute action hash
        action_json = json.dumps(action_spec, sort_keys=True)
        action_hash = hashlib.sha256(action_json.encode()).hexdigest()

        # Create JWT payload
        payload = {
            "run_id": run_id,
            "action_hash": action_hash,
            "policy_version": policy_version,
            "risk_score": risk_score,
            "approval_tier": approval_tier,
            "issued_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "nonce": hashlib.sha256(str(datetime.utcnow().timestamp()).encode()).hexdigest()[:16]
        }

        # Sign token
        token = jwt.encode(payload, settings.POLICY_SIGNING_SECRET, algorithm="HS256")
        return token

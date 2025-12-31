"""
Policy Engine: Issues JWT approval tokens for Worker Runtime execution (V2 requirement).

Per spec: "Policy Engine issues signed JWT token containing:
- action_id, run_id, method, flags (validated)
- Signature prevents tampering
- Worker validates JWT before execution"
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from jose import JWTError, jwt
import uuid

from config import settings


class PolicyEngine:
    """
    Policy Engine for action approval and JWT token issuance.

    Three-Layer Tool Enforcement:
    1. Policy Engine allowlist (Stage 1 tools only)
    2. Worker Runtime enum validation
    3. Subprocess validation (tool exists, flags valid)
    """

    # Stage 1 tools (V2 MVP allowlist - per spec)
    STAGE_1_TOOLS = {
        "httpx", "nmap", "dnsx", "subfinder", "katana", "ffuf"
    }

    # Stage 2 tools (MUST be rejected in V2 MVP)
    STAGE_2_TOOLS = {
        "nuclei", "sqlmap", "nikto"
    }

    @staticmethod
    def validate_tool_allowlist(method: str) -> tuple[bool, Optional[str]]:
        """
        Validate tool against allowlist (Layer 1 enforcement).

        Args:
            method: Tool method name

        Returns:
            tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        method_lower = method.lower()

        if method_lower in PolicyEngine.STAGE_2_TOOLS:
            return False, f"Tool '{method}' is Stage 2 (not allowed in V2 MVP). Only Stage 1 tools allowed: {', '.join(PolicyEngine.STAGE_1_TOOLS)}"

        if method_lower not in PolicyEngine.STAGE_1_TOOLS:
            return False, f"Tool '{method}' not in Stage 1 allowlist. Allowed: {', '.join(PolicyEngine.STAGE_1_TOOLS)}"

        return True, None

    @staticmethod
    def issue_approval_token(
        action_id: uuid.UUID,
        run_id: uuid.UUID,
        method: str,
        flags: Dict[str, Any],
        approved_by: uuid.UUID,
        ttl_minutes: int = 30
    ) -> str:
        """
        Issue JWT approval token for Worker Runtime execution.

        Args:
            action_id: Action ID
            run_id: Run ID
            method: Tool method (e.g., "nmap", "httpx")
            flags: Validated flags for tool execution
            approved_by: User ID who approved
            ttl_minutes: Token TTL (default: 30 minutes)

        Returns:
            str: JWT approval token

        Token Claims:
            - sub: action_id
            - run_id: run_id
            - method: tool method
            - flags: validated flags
            - approved_by: user_id
            - iat: issued at
            - exp: expiration
        """
        now = datetime.utcnow()
        expiration = now + timedelta(minutes=ttl_minutes)

        claims = {
            "sub": str(action_id),
            "run_id": str(run_id),
            "method": method,
            "flags": flags,
            "approved_by": str(approved_by),
            "iat": now.timestamp(),
            "exp": expiration.timestamp()
        }

        token = jwt.encode(
            claims,
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM
        )

        return token

    @staticmethod
    def verify_approval_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode JWT approval token.

        Args:
            token: JWT token

        Returns:
            Optional[Dict]: Decoded claims or None if invalid
        """
        try:
            claims = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM]
            )
            return claims
        except JWTError:
            return None

    @staticmethod
    def validate_action_spec(action_spec: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate ActionSpec structure and content.

        Args:
            action_spec: ActionSpec dictionary

        Returns:
            tuple[bool, Optional[str]]: (is_valid, error_message)

        Validates:
            - Required fields present (action_id, run_id, method, flags)
            - Tool in Stage 1 allowlist
            - Flags structure valid
        """
        # Check required fields
        required_fields = ["action_id", "run_id", "method", "flags"]
        for field in required_fields:
            if field not in action_spec:
                return False, f"Missing required field: {field}"

        # Validate tool allowlist
        method = action_spec["method"]
        is_valid, error = PolicyEngine.validate_tool_allowlist(method)
        if not is_valid:
            return False, error

        # Validate flags is dict
        if not isinstance(action_spec["flags"], dict):
            return False, "flags must be a dictionary"

        return True, None


# Global instance
policy_engine = PolicyEngine()

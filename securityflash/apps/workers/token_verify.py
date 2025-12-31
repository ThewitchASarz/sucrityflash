"""
JWT token verification for workers.

CRITICAL: Workers must verify token before executing any tool.
"""
import jwt
import hashlib
import json
from datetime import datetime
from typing import Dict, Any, Optional
from apps.api.core.config import settings


def verify_action_token(action_spec: Dict[str, Any], token: str) -> tuple[bool, Optional[str]]:
    """
    Verify JWT token for an ActionSpec.

    Checks:
    1. Token signature (signed with POLICY_SIGNING_SECRET)
    2. Token expiration (expires_at < now)
    3. Action hash match (sha256(action_json) == token.action_hash)

    Args:
        action_spec: ActionSpec action_json dict
        token: JWT token string

    Returns:
        (is_valid, error_message) tuple
    """
    if not token:
        return False, "No approval token provided"

    try:
        # Decode and verify signature
        payload = jwt.decode(
            token,
            settings.POLICY_SIGNING_SECRET,
            algorithms=["HS256"]
        )
    except jwt.ExpiredSignatureError:
        return False, "Token has expired"
    except jwt.InvalidTokenError as e:
        return False, f"Invalid token: {str(e)}"

    # Check expiration manually (extra safety)
    expires_at_str = payload.get("expires_at")
    if expires_at_str:
        expires_at = datetime.fromisoformat(expires_at_str)
        if expires_at < datetime.utcnow():
            return False, "Token has expired (manual check)"

    # Check action hash
    action_json = json.dumps(action_spec, sort_keys=True)
    action_hash = hashlib.sha256(action_json.encode()).hexdigest()

    token_hash = payload.get("action_hash")
    if action_hash != token_hash:
        return False, f"Action hash mismatch (expected {token_hash[:16]}..., got {action_hash[:16]}...)"

    return True, None

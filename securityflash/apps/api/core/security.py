"""
Security and RBAC enforcement.

MUST-FIX C: Evidence deletion is ALWAYS blocked (403).
"""
from fastapi import HTTPException, Request
from typing import Optional


def block_evidence_delete():
    """
    MUST-FIX C: Always raise 403 for evidence deletion.

    This is layer 1 of 3-layer evidence immutability:
    - Layer 1: API returns 403 (this function)
    - Layer 2: No delete() method in EvidenceService
    - Layer 3: MinIO bucket policy denies delete operations

    Raises:
        HTTPException(403): Always
    """
    raise HTTPException(
        status_code=403,
        detail="Evidence cannot be deleted. Evidence is immutable once created. "
               "This is enforced for compliance and audit integrity."
    )


def block_scope_modification_if_locked(scope):
    """
    Block modification of locked scopes.

    Args:
        scope: Scope model instance

    Raises:
        HTTPException(403): If scope is locked
    """
    if scope.status == "locked":
        raise HTTPException(
            status_code=403,
            detail="Cannot modify locked scope. Scopes are immutable once locked."
        )


def require_role(required_role: str):
    """
    Dependency for role-based access control.

    V1: Placeholder for future RBAC implementation.
    In production, this would check JWT claims or session data.

    Args:
        required_role: Required role (e.g., "reviewer", "admin")

    Returns:
        Dependency function for FastAPI
    """
    def _require_role(request: Request):
        # TODO V2: Implement actual RBAC with JWT/session
        # For V1, we trust the caller (development only)
        return True

    return _require_role


def get_current_user(request: Request) -> str:
    """
    Get current user ID from request.

    V1: Placeholder returning "system".
    In production, extract from JWT or session.

    Args:
        request: FastAPI request

    Returns:
        User ID string
    """
    # TODO V2: Implement actual user extraction from JWT
    # For V1, return system user
    return "system"


def get_client_ip(request: Request) -> Optional[str]:
    """
    Get client IP address from request.

    Args:
        request: FastAPI request

    Returns:
        IP address string or None
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def get_user_agent(request: Request) -> Optional[str]:
    """
    Get user agent from request.

    Args:
        request: FastAPI request

    Returns:
        User agent string or None
    """
    return request.headers.get("User-Agent")

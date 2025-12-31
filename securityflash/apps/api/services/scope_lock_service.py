"""
Scope lock service - enforces scope immutability.
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session
from apps.api.models.scope import Scope
from datetime import datetime
import uuid


class ScopeLockService:
    """
    Manages scope locking and immutability enforcement.
    """

    @staticmethod
    def lock_scope(
        db: Session,
        scope_id: uuid.UUID,
        locked_by: str,
        signature: str
    ) -> Scope:
        """
        Lock a scope, making it immutable.

        Args:
            db: Database session
            scope_id: Scope ID
            locked_by: User/reviewer ID
            signature: Cryptographic signature

        Returns:
            Locked Scope instance

        Raises:
            HTTPException(404): Scope not found
            HTTPException(400): Scope already locked
        """
        scope = db.query(Scope).filter(Scope.id == scope_id).first()

        if not scope:
            raise HTTPException(status_code=404, detail="Scope not found")

        if scope.status == "locked":
            raise HTTPException(status_code=400, detail="Scope is already locked")

        scope.locked_at = datetime.utcnow()
        scope.locked_by = locked_by
        scope.lock_signature = signature
        scope.status = "locked"

        db.commit()
        db.refresh(scope)

        return scope

    @staticmethod
    def is_locked(scope: Scope) -> bool:
        """Check if scope is locked."""
        return scope.status == "locked"

    @staticmethod
    def enforce_locked(scope: Scope) -> None:
        """
        Raise exception if scope is not locked.

        Used before starting runs to ensure scope is immutable.

        Raises:
            HTTPException(400): Scope not locked
        """
        if not ScopeLockService.is_locked(scope):
            raise HTTPException(
                status_code=400,
                detail="Scope must be locked before starting run"
            )

    @staticmethod
    def prevent_modification(scope: Scope) -> None:
        """
        Raise exception if attempting to modify locked scope.

        Raises:
            HTTPException(403): Scope is locked and cannot be modified
        """
        if ScopeLockService.is_locked(scope):
            raise HTTPException(
                status_code=403,
                detail="Cannot modify locked scope. Scopes are immutable once locked."
            )

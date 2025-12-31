"""
Scope management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from apps.api.db.session import get_db
from apps.api.models.scope import Scope
from apps.api.schemas.scope import ScopeCreate, ScopeLock, ScopeResponse
from apps.api.services.audit_service import audit_log
from apps.api.services.scope_lock_service import ScopeLockService
from apps.api.core.security import get_current_user

router = APIRouter(prefix="/api/v1/projects/{project_id}/scopes", tags=["scopes"])


@router.post("", response_model=ScopeResponse, status_code=201)
def create_scope(
    project_id: str,
    scope_data: ScopeCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Create a new scope for a project."""
    # Convert Pydantic model to dict for JSONB storage
    scope_json = {
        "scope_type": scope_data.scope_type,
        "targets": [t.dict() for t in scope_data.targets],
        "excluded_targets": [t.dict() for t in scope_data.excluded_targets],
        "attack_vectors_allowed": scope_data.attack_vectors_allowed,
        "attack_vectors_prohibited": scope_data.attack_vectors_prohibited,
        "approved_tools": scope_data.approved_tools,
        "time_restrictions": scope_data.time_restrictions.dict() if scope_data.time_restrictions else None
    }

    scope = Scope(
        project_id=project_id,
        scope_json=scope_json,
        status="draft"
    )

    db.add(scope)
    db.commit()
    db.refresh(scope)

    # Audit log
    current_user = get_current_user(request)
    audit_log(
        db=db,
        run_id=None,
        event_type="SCOPE_CREATED",
        actor=current_user,
        details={
            "scope_id": str(scope.id),
            "project_id": project_id,
            "target_count": len(scope_data.targets)
        }
    )

    return scope


@router.post("/{scope_id}/lock", response_model=ScopeResponse)
def lock_scope(
    project_id: str,
    scope_id: str,
    lock_data: ScopeLock,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Lock a scope, making it immutable.

    Once locked, scope cannot be modified. This ensures run integrity.
    """
    scope = ScopeLockService.lock_scope(
        db=db,
        scope_id=scope_id,
        locked_by=lock_data.locked_by,
        signature=lock_data.signature
    )

    # Audit log
    audit_log(
        db=db,
        run_id=None,
        event_type="SCOPE_LOCKED",
        actor=lock_data.locked_by,
        details={
            "scope_id": str(scope.id),
            "locked_at": scope.locked_at.isoformat(),
            "signature": lock_data.signature[:20] + "..."
        }
    )

    return scope


@router.get("", response_model=list[ScopeResponse])
def list_scopes(project_id: str, db: Session = Depends(get_db)):
    """List all scopes for a project."""
    scopes = db.query(Scope).filter(
        Scope.project_id == project_id
    ).order_by(Scope.created_at.desc()).all()

    return scopes


@router.get("/{scope_id}", response_model=ScopeResponse)
def get_scope(project_id: str, scope_id: str, db: Session = Depends(get_db)):
    """Get scope by ID."""
    scope = db.query(Scope).filter(
        Scope.id == scope_id,
        Scope.project_id == project_id
    ).first()

    if not scope:
        raise HTTPException(status_code=404, detail="Scope not found")

    return scope


@router.put("/{scope_id}", response_model=ScopeResponse)
def update_scope(
    project_id: str,
    scope_id: str,
    scope_data: ScopeCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Update a scope. Fails if scope is locked."""
    scope = db.query(Scope).filter(
        Scope.id == scope_id,
        Scope.project_id == project_id
    ).first()

    if not scope:
        raise HTTPException(status_code=404, detail="Scope not found")

    if scope.locked_at:
        raise HTTPException(
            status_code=409,
            detail="Cannot update locked scope. Locked scopes are immutable to ensure run integrity."
        )

    # Update scope_json
    scope.scope_json = {
        "scope_type": scope_data.scope_type,
        "targets": [t.dict() for t in scope_data.targets],
        "excluded_targets": [t.dict() for t in scope_data.excluded_targets],
        "attack_vectors_allowed": scope_data.attack_vectors_allowed,
        "attack_vectors_prohibited": scope_data.attack_vectors_prohibited,
        "approved_tools": scope_data.approved_tools,
        "time_restrictions": scope_data.time_restrictions.dict() if scope_data.time_restrictions else None
    }

    # Increment version (updated_at will be set automatically by onupdate)
    scope.version += 1

    db.commit()
    db.refresh(scope)

    # Audit log
    current_user = get_current_user(request)
    audit_log(
        db=db,
        run_id=None,
        event_type="SCOPE_UPDATED",
        actor=current_user,
        details={
            "scope_id": str(scope.id),
            "project_id": project_id,
            "version": scope.version
        }
    )

    return scope


@router.delete("/{scope_id}", status_code=204)
def delete_scope(
    project_id: str,
    scope_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Delete a scope. Fails if scope is locked."""
    scope = db.query(Scope).filter(
        Scope.id == scope_id,
        Scope.project_id == project_id
    ).first()

    if not scope:
        raise HTTPException(status_code=404, detail="Scope not found")

    if scope.locked_at:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete locked scope. Locked scopes are immutable to ensure run integrity."
        )

    # Audit log before deletion
    current_user = get_current_user(request)
    audit_log(
        db=db,
        run_id=None,
        event_type="SCOPE_DELETED",
        actor=current_user,
        details={
            "scope_id": str(scope.id),
            "project_id": project_id
        }
    )

    db.delete(scope)
    db.commit()

    return None

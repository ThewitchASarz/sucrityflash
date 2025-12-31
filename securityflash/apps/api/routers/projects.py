"""
Project management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List
from apps.api.db.session import get_db
from apps.api.models.project import Project
from apps.api.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from apps.api.services.audit_service import audit_log
from apps.api.core.security import get_current_user

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(project_data: ProjectCreate, db: Session = Depends(get_db)):
    """Create a new penetration testing project."""
    project = Project(
        name=project_data.name,
        customer_id=project_data.customer_id,
        primary_target_url=project_data.primary_target_url,
        start_date=project_data.start_date,
        end_date=project_data.end_date,
        rules_of_engagement=project_data.rules_of_engagement,
        created_by=project_data.created_by
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    # Audit log
    audit_log(
        db=db,
        run_id=None,
        event_type="PROJECT_CREATED",
        actor=project_data.created_by,
        details={"project_id": str(project.id), "name": project.name}
    )

    return project


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, db: Session = Depends(get_db)):
    """Get project by ID."""
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return project


@router.get("", response_model=List[ProjectResponse])
def list_projects(customer_id: str = None, db: Session = Depends(get_db)):
    """List all projects, optionally filtered by customer."""
    query = db.query(Project)

    if customer_id:
        query = query.filter(Project.customer_id == customer_id)

    return query.all()


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Update a project."""
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Update only provided fields
    if project_data.name is not None:
        project.name = project_data.name
    if project_data.customer_id is not None:
        project.customer_id = project_data.customer_id
    if project_data.primary_target_url is not None:
        project.primary_target_url = project_data.primary_target_url
    if project_data.start_date is not None:
        project.start_date = project_data.start_date
    if project_data.end_date is not None:
        project.end_date = project_data.end_date
    if project_data.rules_of_engagement is not None:
        project.rules_of_engagement = project_data.rules_of_engagement

    db.commit()
    db.refresh(project)

    # Audit log
    current_user = get_current_user(request)
    audit_log(
        db=db,
        run_id=None,
        event_type="PROJECT_UPDATED",
        actor=current_user,
        details={"project_id": str(project.id), "name": project.name}
    )

    return project


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: str, request: Request, db: Session = Depends(get_db)):
    """Delete a project. This will cascade delete all associated scopes and runs."""
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Audit log before deletion
    current_user = get_current_user(request)
    audit_log(
        db=db,
        run_id=None,
        event_type="PROJECT_DELETED",
        actor=current_user,
        details={"project_id": str(project.id), "name": project.name}
    )

    db.delete(project)
    db.commit()

    return None

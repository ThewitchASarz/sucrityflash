"""
Project management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from apps.api.db.session import get_db
from apps.api.models.project import Project
from apps.api.schemas.project import ProjectCreate, ProjectResponse
from apps.api.services.audit_service import audit_log

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(project_data: ProjectCreate, db: Session = Depends(get_db)):
    """Create a new penetration testing project."""
    project = Project(
        name=project_data.name,
        customer_id=project_data.customer_id,
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

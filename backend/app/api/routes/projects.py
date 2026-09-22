from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.repositories.project_repository import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectRead
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])
DbSession = Annotated[Session, Depends(get_db)]


def _service(session: Session) -> ProjectService:
    return ProjectService(ProjectRepository(session))


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, session: DbSession) -> ProjectRead:
    return _service(session).create(payload)


@router.get("", response_model=list[ProjectRead])
def list_projects(session: DbSession) -> list[ProjectRead]:
    return _service(session).list()


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: str, session: DbSession) -> ProjectRead:
    project = _service(session).get(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project

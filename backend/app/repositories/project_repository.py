from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.project import Project


class ProjectRepository:
    """Keeps persistence details out of the API and service layers."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, project: Project) -> Project:
        self.session.add(project)
        self.session.commit()
        self.session.refresh(project)
        return project

    def get(self, project_id: str) -> Project | None:
        statement = (
            select(Project)
            .options(selectinload(Project.scenes))
            .where(Project.id == project_id)
        )
        return self.session.scalar(statement)

    def list(self) -> list[Project]:
        statement = (
            select(Project)
            .options(selectinload(Project.scenes))
            .order_by(Project.created_at.desc())
        )
        return list(self.session.scalars(statement).all())

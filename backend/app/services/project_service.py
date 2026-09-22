from uuid import uuid4

from app.models.enums import ProjectStatus
from app.models.project import Project
from app.repositories.project_repository import ProjectRepository
from app.schemas.project import ProjectCreate
from app.services.scene_planner import ScenePlanner


class ProjectService:
    def __init__(
        self,
        repository: ProjectRepository,
        scene_planner: ScenePlanner | None = None,
    ) -> None:
        self.repository = repository
        self.scene_planner = scene_planner or ScenePlanner()

    def create(self, payload: ProjectCreate) -> Project:
        project = Project(
            id=str(uuid4()),
            prompt=payload.prompt.strip(),
            duration_seconds=payload.duration_seconds,
            quality=payload.quality,
            status=ProjectStatus.CREATED,
        )
        project.scenes = self.scene_planner.plan(
            project_id=project.id,
            video_prompt=project.prompt,
            duration_seconds=project.duration_seconds,
        )
        return self.repository.add(project)

    def get(self, project_id: str) -> Project | None:
        return self.repository.get(project_id)

    def list(self) -> list[Project]:
        return self.repository.list()

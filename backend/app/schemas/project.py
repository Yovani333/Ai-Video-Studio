from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ProjectQuality, ProjectStatus
from app.schemas.scene import SceneRead


class ProjectCreate(BaseModel):
    prompt: str = Field(min_length=3, max_length=4000)
    duration_seconds: int = Field(default=60, ge=5, le=600)
    quality: ProjectQuality = ProjectQuality.DRAFT


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    prompt: str
    duration_seconds: int
    quality: ProjectQuality
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
    scenes: list[SceneRead] = Field(default_factory=list)

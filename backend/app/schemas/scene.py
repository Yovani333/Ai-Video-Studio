from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import SceneStatus
from app.schemas.context import SceneContext


class SceneRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    order: int = Field(ge=1)
    duration_seconds: float = Field(gt=0)
    prompt: str
    status: SceneStatus
    context: SceneContext

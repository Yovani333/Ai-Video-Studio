import math
from uuid import uuid4

from app.models.enums import SceneStatus
from app.models.scene import Scene
from app.schemas.context import SceneContext


class ScenePlanner:
    """Creates an initial deterministic scene plan; AI planning can replace it later."""

    def __init__(self, target_scene_duration: int = 5) -> None:
        self.target_scene_duration = target_scene_duration

    def plan(
        self,
        *,
        project_id: str,
        video_prompt: str,
        duration_seconds: int,
    ) -> list[Scene]:
        scene_count = max(1, math.ceil(duration_seconds / self.target_scene_duration))
        remaining = float(duration_seconds)
        scenes: list[Scene] = []

        for index in range(1, scene_count + 1):
            scene_duration = min(float(self.target_scene_duration), remaining)
            remaining -= scene_duration
            scenes.append(
                Scene(
                    id=str(uuid4()),
                    project_id=project_id,
                    order=index,
                    duration_seconds=scene_duration,
                    prompt=f"{video_prompt} — scene {index:02d}",
                    status=SceneStatus.WAITING,
                    context=SceneContext().model_dump(),
                )
            )

        return scenes

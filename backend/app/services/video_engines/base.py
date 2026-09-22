from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from app.schemas.context import SceneContext


@dataclass(frozen=True)
class ClipGenerationRequest:
    scene_id: str
    prompt: str
    duration_seconds: float
    context: SceneContext


@dataclass(frozen=True)
class GeneratedClip:
    scene_id: str
    file_path: Path
    metadata: dict[str, object]


class VideoEngine(ABC):
    """Provider-neutral contract for a future local or remote video engine."""

    @abstractmethod
    async def generate_clip(self, request: ClipGenerationRequest) -> GeneratedClip:
        raise NotImplementedError

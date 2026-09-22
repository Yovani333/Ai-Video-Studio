from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class RenderRequest:
    project_id: str
    clips: list[Path]
    output_path: Path
    resolution: tuple[int, int] = (1920, 1080)
    fps: int = 24
    audio_path: Path | None = None
    options: dict[str, object] = field(default_factory=dict)


class VideoRenderer(ABC):
    """Contract for the future FFmpeg-backed final rendering service."""

    @abstractmethod
    async def render(self, request: RenderRequest) -> Path:
        raise NotImplementedError

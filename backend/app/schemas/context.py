from pydantic import BaseModel, Field


class SceneContext(BaseModel):
    """Continuity metadata shared or refined between generated scenes."""

    character: str | None = None
    environment: str | None = None
    visual_style: str | None = None
    lighting: str | None = None
    camera: str | None = None
    colors: list[str] = Field(default_factory=list)
    reference_images: list[str] = Field(default_factory=list)
    seed: int | None = None

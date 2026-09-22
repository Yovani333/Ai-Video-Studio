from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import GenerationJobStatus


class GenerationCreate(BaseModel):
    mode: Literal["text_to_video"] = "text_to_video"
    engine: str = Field(default="diagnostic", min_length=1, max_length=64)
    model_revision: str = Field(default="diagnostic-v1", min_length=1, max_length=255)
    width: int = Field(default=1280, ge=256, le=2048)
    height: int = Field(default=704, ge=256, le=2048)
    fps: int = Field(default=24, ge=1, le=60)
    seed: int | None = Field(default=None, ge=0)


class WorkerJobRequest(BaseModel):
    protocol_version: Literal["1"] = "1"
    job_id: str
    scene_id: str
    mode: Literal["text_to_video"]
    engine: str
    model_revision: str
    prompt: str
    duration_seconds: float = Field(gt=0)
    width: int
    height: int
    fps: int
    seed: int | None = None
    reference_artifact_ids: list[str] = Field(default_factory=list)


class ArtifactMetadata(BaseModel):
    artifact_id: str
    media_type: str
    size_bytes: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    kind: Literal["diagnostic", "video"]
    filename: str


class WorkerJobRead(BaseModel):
    protocol_version: Literal["1"] = "1"
    job_id: str
    payload_hash: str
    status: GenerationJobStatus
    artifact: ArtifactMetadata | None = None
    effective_parameters: dict[str, object] | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


class GenerationJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    scene_id: str
    attempt: int
    prompt_snapshot: str
    provider: str
    engine: str
    model_revision: str
    status: GenerationJobStatus
    request_payload: dict
    effective_parameters: dict | None
    remote_job_id: str | None
    artifact: dict | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

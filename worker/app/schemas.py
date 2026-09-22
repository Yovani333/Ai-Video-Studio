from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


JobStatus = Literal[
    "queued",
    "submitting",
    "running",
    "transferring",
    "succeeded",
    "failed",
    "timed_out",
    "cancelled",
]


class WorkerJobRequest(BaseModel):
    protocol_version: Literal["1"] = "1"
    job_id: str
    scene_id: str
    mode: Literal["text_to_video"]
    engine: str
    model_revision: str
    prompt: str = Field(min_length=1, max_length=4000)
    duration_seconds: float = Field(gt=0, le=30)
    width: int = Field(ge=256, le=2048)
    height: int = Field(ge=256, le=2048)
    fps: int = Field(ge=1, le=60)
    seed: int | None = Field(default=None, ge=0)
    reference_artifact_ids: list[str] = Field(default_factory=list, max_length=8)


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
    status: JobStatus
    artifact: ArtifactMetadata | None = None
    effective_parameters: dict[str, object] | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


class WorkerReadiness(BaseModel):
    status: Literal["ready"] = "ready"
    protocol_version: Literal["1"] = "1"
    engine: Literal["diagnostic"] = "diagnostic"
    accepts_jobs: bool

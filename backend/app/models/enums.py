from enum import Enum


class ProjectStatus(str, Enum):
    CREATED = "created"
    PLANNING = "planning"
    QUEUED = "queued"
    GENERATING = "generating"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"


class ProjectQuality(str, Enum):
    DRAFT = "draft"
    FINAL = "final"


class SceneStatus(str, Enum):
    WAITING = "waiting"
    QUEUED = "queued"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class GenerationJobStatus(str, Enum):
    QUEUED = "queued"
    SUBMITTING = "submitting"
    RUNNING = "running"
    TRANSFERRING = "transferring"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.models.enums import GenerationJobStatus
from app.models.generation_job import GenerationJob
from app.repositories.generation_job_repository import GenerationJobRepository
from app.repositories.scene_repository import SceneRepository
from app.schemas.generation import (
    ArtifactMetadata,
    GenerationCreate,
    WorkerJobRead,
    WorkerJobRequest,
)
from app.services.gpu.base import GPUProvider, GPUProviderError


ACTIVE_STATUSES = {
    GenerationJobStatus.QUEUED,
    GenerationJobStatus.SUBMITTING,
    GenerationJobStatus.RUNNING,
    GenerationJobStatus.TRANSFERRING,
}


class SceneNotFoundError(LookupError):
    pass


class JobNotFoundError(LookupError):
    pass


class ArtifactUnavailableError(LookupError):
    pass


ARTIFACT_SUFFIXES = {
    "application/json": ".json",
    "video/mp4": ".mp4",
}


class GenerationService:
    def __init__(
        self,
        jobs: GenerationJobRepository,
        scenes: SceneRepository,
        provider: GPUProvider,
        storage_root: Path,
    ) -> None:
        self.jobs = jobs
        self.scenes = scenes
        self.provider = provider
        self.storage_root = storage_root.resolve()

    @staticmethod
    def _hash_payload(payload: dict) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    async def create(
        self,
        *,
        project_id: str,
        scene_id: str,
        command: GenerationCreate,
    ) -> GenerationJob:
        scene = self.scenes.get(scene_id)
        if scene is None or scene.project_id != project_id:
            raise SceneNotFoundError

        job_id = str(uuid4())
        request = WorkerJobRequest(
            job_id=job_id,
            scene_id=scene.id,
            mode=command.mode,
            engine=command.engine,
            model_revision=command.model_revision,
            prompt=scene.prompt,
            duration_seconds=scene.duration_seconds,
            width=command.width,
            height=command.height,
            fps=command.fps,
            seed=command.seed,
        )
        payload = request.model_dump(mode="json")
        job = GenerationJob(
            id=job_id,
            project_id=project_id,
            scene_id=scene.id,
            attempt=self.jobs.next_attempt(scene.id),
            prompt_snapshot=scene.prompt,
            payload_hash=self._hash_payload(payload),
            provider=self.provider.name,
            engine=command.engine,
            model_revision=command.model_revision,
            status=GenerationJobStatus.QUEUED,
            request_payload=payload,
        )
        self.jobs.add(job)
        job.status = GenerationJobStatus.SUBMITTING
        self.jobs.save(job)

        try:
            remote = await self.provider.submit(request)
        except GPUProviderError as exc:
            job.error_code = exc.code
            job.error_message = exc.message
            if not exc.retryable:
                job.status = GenerationJobStatus.FAILED
                job.completed_at = datetime.now(timezone.utc)
            return self.jobs.save(job)

        return await self._apply_remote(job, remote)

    async def get(self, job_id: str, *, refresh: bool = True) -> GenerationJob:
        job = self.jobs.get(job_id)
        if job is None:
            raise JobNotFoundError
        if refresh and job.status in ACTIVE_STATUSES:
            try:
                remote = await self.provider.get_status(job.id)
            except GPUProviderError as exc:
                job.error_code = exc.code
                job.error_message = exc.message
                return self.jobs.save(job)
            return await self._apply_remote(job, remote)
        return job

    async def cancel(self, job_id: str) -> GenerationJob:
        job = self.jobs.get(job_id)
        if job is None:
            raise JobNotFoundError
        if job.status not in ACTIVE_STATUSES:
            return job
        try:
            remote = await self.provider.cancel(job.id)
        except GPUProviderError as exc:
            job.error_code = exc.code
            job.error_message = exc.message
            return self.jobs.save(job)
        return await self._apply_remote(job, remote)

    def artifact_path(self, job_id: str) -> tuple[Path, str]:
        job = self.jobs.get(job_id)
        if job is None:
            raise JobNotFoundError
        if job.status != GenerationJobStatus.SUCCEEDED or not job.artifact:
            raise ArtifactUnavailableError
        relative_path = job.artifact.get("local_path")
        media_type = job.artifact.get("media_type")
        if not isinstance(relative_path, str) or not isinstance(media_type, str):
            raise ArtifactUnavailableError
        path = (self.storage_root / relative_path).resolve()
        if not path.is_relative_to(self.storage_root) or not path.is_file():
            raise ArtifactUnavailableError
        return path, media_type

    def _artifact_destination(self, job: GenerationJob, artifact: ArtifactMetadata) -> Path:
        suffix = ARTIFACT_SUFFIXES.get(artifact.media_type)
        if suffix is None:
            raise GPUProviderError(
                "artifact_media_type_unsupported",
                "The worker returned an unsupported artifact media type.",
            )
        destination = (
            self.storage_root / "clips" / job.project_id / job.scene_id / f"{job.id}{suffix}"
        ).resolve()
        if not destination.is_relative_to(self.storage_root):
            raise GPUProviderError(
                "artifact_path_invalid",
                "The local artifact path is invalid.",
            )
        return destination

    async def _transfer_artifact(
        self,
        job: GenerationJob,
        artifact: ArtifactMetadata,
    ) -> GenerationJob:
        try:
            destination = self._artifact_destination(job, artifact)
            metadata = artifact.model_dump(mode="json")
            job.status = GenerationJobStatus.TRANSFERRING
            job.artifact = metadata
            job.error_code = None
            job.error_message = None
            job.completed_at = None
            self.jobs.save(job)
            saved_path = await self.provider.download_artifact(job.id, destination, artifact)
        except GPUProviderError as exc:
            job.error_code = exc.code
            job.error_message = exc.message
            if not exc.retryable:
                job.status = GenerationJobStatus.FAILED
                job.completed_at = datetime.now(timezone.utc)
            return self.jobs.save(job)

        metadata["local_path"] = saved_path.relative_to(self.storage_root).as_posix()
        job.artifact = metadata
        job.status = GenerationJobStatus.SUCCEEDED
        job.error_code = None
        job.error_message = None
        job.completed_at = datetime.now(timezone.utc)
        return self.jobs.save(job)

    async def _apply_remote(
        self, job: GenerationJob, remote: WorkerJobRead
    ) -> GenerationJob:
        if remote.job_id != job.id or remote.payload_hash != job.payload_hash:
            job.status = GenerationJobStatus.FAILED
            job.error_code = "worker_protocol_mismatch"
            job.error_message = "The worker response did not match the submitted job."
            job.completed_at = datetime.now(timezone.utc)
            return self.jobs.save(job)
        job.remote_job_id = remote.job_id
        job.effective_parameters = remote.effective_parameters
        job.error_code = remote.error_code
        job.error_message = remote.error_message
        job.started_at = remote.started_at
        job.completed_at = remote.completed_at
        if remote.status == GenerationJobStatus.SUCCEEDED:
            if remote.artifact is None:
                job.status = GenerationJobStatus.FAILED
                job.error_code = "worker_protocol_mismatch"
                job.error_message = "The worker reported success without an artifact."
                job.completed_at = datetime.now(timezone.utc)
                return self.jobs.save(job)
            return await self._transfer_artifact(job, remote.artifact)
        job.status = remote.status
        job.artifact = remote.artifact.model_dump(mode="json") if remote.artifact else None
        return self.jobs.save(job)

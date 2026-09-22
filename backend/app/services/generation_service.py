import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

from app.models.enums import GenerationJobStatus
from app.models.generation_job import GenerationJob
from app.repositories.generation_job_repository import GenerationJobRepository
from app.repositories.scene_repository import SceneRepository
from app.schemas.generation import GenerationCreate, WorkerJobRead, WorkerJobRequest
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


class GenerationService:
    def __init__(
        self,
        jobs: GenerationJobRepository,
        scenes: SceneRepository,
        provider: GPUProvider,
    ) -> None:
        self.jobs = jobs
        self.scenes = scenes
        self.provider = provider

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

        return self._apply_remote(job, remote)

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
            return self._apply_remote(job, remote)
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
        return self._apply_remote(job, remote)

    def _apply_remote(self, job: GenerationJob, remote: WorkerJobRead) -> GenerationJob:
        if remote.job_id != job.id or remote.payload_hash != job.payload_hash:
            job.status = GenerationJobStatus.FAILED
            job.error_code = "worker_protocol_mismatch"
            job.error_message = "The worker response did not match the submitted job."
            job.completed_at = datetime.now(timezone.utc)
            return self.jobs.save(job)
        job.remote_job_id = remote.job_id
        job.status = remote.status
        job.artifact = remote.artifact.model_dump(mode="json") if remote.artifact else None
        job.effective_parameters = remote.effective_parameters
        job.error_code = remote.error_code
        job.error_message = remote.error_message
        job.started_at = remote.started_at
        job.completed_at = remote.completed_at
        return self.jobs.save(job)

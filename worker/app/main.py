import hashlib
import hmac
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.responses import FileResponse

from worker.app.config import get_worker_settings
from worker.app.engine import DiagnosticEngine
from worker.app.runtime import WorkerRuntime
from worker.app.schemas import WorkerJobRead, WorkerJobRequest, WorkerReadiness
from worker.app.store import PayloadConflictError, WorkerJobStore


def create_app(
    *,
    database_path: Path | None = None,
    artifact_root: Path | None = None,
    api_token: str | None = None,
    engine: DiagnosticEngine | None = None,
) -> FastAPI:
    settings = get_worker_settings()
    token = settings.worker_api_token if api_token is None else api_token
    store = WorkerJobStore(database_path or settings.worker_database_path)
    diagnostic_engine = engine or DiagnosticEngine(
        artifact_root or settings.worker_artifact_root
    )
    runtime = WorkerRuntime(store, diagnostic_engine)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await runtime.start()
        yield
        await runtime.stop()

    application = FastAPI(title="AI Video Studio Worker", version="0.1.0", lifespan=lifespan)
    application.state.store = store
    application.state.runtime = runtime
    application.state.engine = diagnostic_engine

    def authorize(authorization: str | None = Header(default=None)) -> None:
        if not token:
            raise HTTPException(status_code=503, detail="Worker authentication is not configured")
        expected = f"Bearer {token}"
        if authorization is None or not hmac.compare_digest(authorization, expected):
            raise HTTPException(status_code=401, detail="Invalid worker token")

    @application.get("/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/v1/readiness", response_model=WorkerReadiness, dependencies=[Depends(authorize)])
    def readiness() -> WorkerReadiness:
        return WorkerReadiness(accepts_jobs=True)

    @application.put(
        "/v1/jobs/{job_id}",
        response_model=WorkerJobRead,
        status_code=status.HTTP_202_ACCEPTED,
        dependencies=[Depends(authorize)],
    )
    async def submit(job_id: str, payload: WorkerJobRequest) -> WorkerJobRead:
        if payload.job_id != job_id:
            raise HTTPException(status_code=422, detail="Path and payload job IDs differ")
        if payload.engine != diagnostic_engine.name:
            raise HTTPException(status_code=422, detail="Engine is not available on this worker")
        serialized = payload.model_dump(mode="json")
        canonical = json.dumps(serialized, sort_keys=True, separators=(",", ":"))
        payload_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        try:
            job, created = store.put(job_id, payload_hash, serialized)
        except PayloadConflictError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Job ID already exists with a different payload",
            ) from exc
        if created:
            await runtime.enqueue(job_id)
        return job

    @application.get(
        "/v1/jobs/{job_id}",
        response_model=WorkerJobRead,
        dependencies=[Depends(authorize)],
    )
    def get_job(job_id: str) -> WorkerJobRead:
        job = store.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return job

    @application.post(
        "/v1/jobs/{job_id}/cancel",
        response_model=WorkerJobRead,
        dependencies=[Depends(authorize)],
    )
    def cancel_job(job_id: str) -> WorkerJobRead:
        job = store.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        if job.status in {"queued", "submitting", "running", "transferring"}:
            return store.update(job_id, status="cancelled")
        return job

    @application.get(
        "/v1/jobs/{job_id}/artifacts/clip",
        dependencies=[Depends(authorize)],
    )
    def download_artifact(job_id: str) -> FileResponse:
        job = store.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        if job.status != "succeeded" or job.artifact is None:
            raise HTTPException(status_code=409, detail="Artifact is not available")
        path = diagnostic_engine.artifact_root / job.artifact.filename
        if not path.is_file():
            raise HTTPException(status_code=410, detail="Artifact is no longer available")
        return FileResponse(path, media_type=job.artifact.media_type, filename=path.name)

    return application


app = create_app()

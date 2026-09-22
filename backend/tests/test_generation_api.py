from datetime import datetime, timezone
import hashlib
import json

import pytest

from app.api.dependencies import get_gpu_provider
from app.main import app
from app.models.enums import GenerationJobStatus
from app.schemas.generation import ArtifactMetadata, WorkerJobRead, WorkerJobRequest
from app.services.gpu.base import GPUProvider, GPUProviderError


def now() -> datetime:
    return datetime.now(timezone.utc)


class FakeGPUProvider(GPUProvider):
    name = "fake-provider"

    def __init__(self) -> None:
        self.requests: dict[str, WorkerJobRequest] = {}
        self.cancelled: set[str] = set()

    @staticmethod
    def payload_hash(request: WorkerJobRequest) -> str:
        canonical = json.dumps(
            request.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    async def probe(self) -> dict[str, object]:
        return {"status": "ready"}

    async def submit(self, request: WorkerJobRequest) -> WorkerJobRead:
        self.requests[request.job_id] = request
        timestamp = now()
        return WorkerJobRead(
            job_id=request.job_id,
            payload_hash=self.payload_hash(request),
            status=GenerationJobStatus.QUEUED,
            created_at=timestamp,
            updated_at=timestamp,
        )

    async def get_status(self, job_id: str) -> WorkerJobRead:
        timestamp = now()
        request = self.requests[job_id]
        return WorkerJobRead(
            job_id=job_id,
            payload_hash=self.payload_hash(request),
            status=GenerationJobStatus.SUCCEEDED,
            artifact=ArtifactMetadata(
                artifact_id=f"diagnostic:{job_id}",
                media_type="application/json",
                size_bytes=10,
                sha256="b" * 64,
                kind="diagnostic",
                filename=f"{job_id}.json",
            ),
            effective_parameters={
                "engine": "diagnostic",
                "video_generated": False,
                "requested_duration_seconds": request.duration_seconds,
            },
            created_at=timestamp,
            updated_at=timestamp,
            started_at=timestamp,
            completed_at=timestamp,
        )

    async def cancel(self, job_id: str) -> WorkerJobRead:
        self.cancelled.add(job_id)
        timestamp = now()
        return WorkerJobRead(
            job_id=job_id,
            payload_hash=self.payload_hash(self.requests[job_id]),
            status=GenerationJobStatus.CANCELLED,
            created_at=timestamp,
            updated_at=timestamp,
            completed_at=timestamp,
        )

    async def download_artifact(self, job_id: str) -> bytes:
        return b"{}"


@pytest.fixture
def fake_provider():
    provider = FakeGPUProvider()
    app.dependency_overrides[get_gpu_provider] = lambda: provider
    yield provider
    app.dependency_overrides.pop(get_gpu_provider, None)


def create_project(client) -> dict:
    response = client.post(
        "/api/projects",
        json={"prompt": "A blue crystal planet", "duration_seconds": 10, "quality": "draft"},
    )
    assert response.status_code == 201
    return response.json()


def test_create_and_refresh_generation_job(client, fake_provider):
    project = create_project(client)
    scene = project["scenes"][0]
    created_response = client.post(
        f"/api/projects/{project['id']}/scenes/{scene['id']}/generations",
        json={"engine": "diagnostic", "model_revision": "diagnostic-v1", "seed": 7},
    )
    assert created_response.status_code == 202
    created = created_response.json()
    assert created["status"] == "queued"
    assert created["attempt"] == 1
    assert created["provider"] == "fake-provider"
    assert fake_provider.requests[created["id"]].prompt == scene["prompt"]

    refreshed_response = client.get(f"/api/jobs/{created['id']}")
    assert refreshed_response.status_code == 200
    refreshed = refreshed_response.json()
    assert refreshed["status"] == "succeeded"
    assert refreshed["artifact"]["kind"] == "diagnostic"
    assert refreshed["effective_parameters"]["video_generated"] is False


def test_cancel_generation_job(client, fake_provider):
    project = create_project(client)
    scene = project["scenes"][0]
    created = client.post(
        f"/api/projects/{project['id']}/scenes/{scene['id']}/generations", json={}
    ).json()
    response = client.post(f"/api/jobs/{created['id']}/cancel")
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert created["id"] in fake_provider.cancelled


def test_generation_rejects_scene_from_another_project(client, fake_provider):
    first = create_project(client)
    second = create_project(client)
    response = client.post(
        f"/api/projects/{second['id']}/scenes/{first['scenes'][0]['id']}/generations",
        json={},
    )
    assert response.status_code == 404


def test_missing_generation_job(client, fake_provider):
    assert client.get("/api/jobs/missing").status_code == 404
    assert client.post("/api/jobs/missing/cancel").status_code == 404


def test_uncertain_submission_is_persisted_for_reconciliation(client):
    class TimeoutProvider(FakeGPUProvider):
        async def submit(self, request: WorkerJobRequest) -> WorkerJobRead:
            raise GPUProviderError(
                "provider_timeout",
                "The worker response was not received.",
                retryable=True,
            )

    provider = TimeoutProvider()
    app.dependency_overrides[get_gpu_provider] = lambda: provider
    try:
        project = create_project(client)
        scene = project["scenes"][0]
        response = client.post(
            f"/api/projects/{project['id']}/scenes/{scene['id']}/generations",
            json={},
        )
        assert response.status_code == 202
        job = response.json()
        assert job["status"] == "submitting"
        assert job["error_code"] == "provider_timeout"
    finally:
        app.dependency_overrides.pop(get_gpu_provider, None)


def test_mismatched_worker_response_fails_safely(client):
    class MismatchedProvider(FakeGPUProvider):
        async def submit(self, request: WorkerJobRequest) -> WorkerJobRead:
            response = await super().submit(request)
            return response.model_copy(update={"payload_hash": "f" * 64})

    provider = MismatchedProvider()
    app.dependency_overrides[get_gpu_provider] = lambda: provider
    try:
        project = create_project(client)
        scene = project["scenes"][0]
        response = client.post(
            f"/api/projects/{project['id']}/scenes/{scene['id']}/generations",
            json={},
        )
        assert response.status_code == 202
        job = response.json()
        assert job["status"] == "failed"
        assert job["error_code"] == "worker_protocol_mismatch"
    finally:
        app.dependency_overrides.pop(get_gpu_provider, None)

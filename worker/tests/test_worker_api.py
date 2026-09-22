import hashlib
import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from worker.app.engine import DiagnosticEngine
from worker.app.main import create_app


def wait_for_terminal_state(client, headers: dict, job_id: str) -> dict:
    for _ in range(100):
        response = client.get(f"/v1/jobs/{job_id}", headers=headers)
        assert response.status_code == 200
        job = response.json()
        if job["status"] in {"succeeded", "failed", "cancelled"}:
            return job
        time.sleep(0.01)
    raise AssertionError("Worker job did not reach a terminal state")


def test_health_and_authentication(worker_client, auth_headers):
    assert worker_client.get("/v1/health").json() == {"status": "ok"}
    assert worker_client.get("/v1/readiness").status_code == 401
    readiness = worker_client.get("/v1/readiness", headers=auth_headers)
    assert readiness.status_code == 200
    assert readiness.json() == {
        "status": "ready",
        "protocol_version": "1",
        "engine": "diagnostic",
        "accepts_jobs": True,
    }


def test_idempotency_and_diagnostic_artifact(worker_client, auth_headers, job_payload):
    first = worker_client.put("/v1/jobs/job-001", headers=auth_headers, json=job_payload)
    assert first.status_code == 202
    duplicate = worker_client.put("/v1/jobs/job-001", headers=auth_headers, json=job_payload)
    assert duplicate.status_code == 202
    assert duplicate.json()["payload_hash"] == first.json()["payload_hash"]

    completed = wait_for_terminal_state(worker_client, auth_headers, "job-001")
    assert completed["status"] == "succeeded"
    assert completed["artifact"]["kind"] == "diagnostic"
    assert completed["effective_parameters"]["video_generated"] is False
    artifact_response = worker_client.get(
        "/v1/jobs/job-001/artifacts/clip", headers=auth_headers
    )
    assert artifact_response.status_code == 200
    assert hashlib.sha256(artifact_response.content).hexdigest() == completed["artifact"]["sha256"]
    artifact = artifact_response.json()
    assert artifact["message"] == "Diagnostic worker completed without video generation."


def test_same_id_with_different_payload_returns_conflict(
    worker_client, auth_headers, job_payload
):
    assert (
        worker_client.put("/v1/jobs/job-001", headers=auth_headers, json=job_payload).status_code
        == 202
    )
    changed = dict(job_payload)
    changed["prompt"] = "A different prompt"
    response = worker_client.put("/v1/jobs/job-001", headers=auth_headers, json=changed)
    assert response.status_code == 409


def test_contract_manifest_matches_worker_schema():
    repository_root = Path(__file__).resolve().parents[2]
    contract = json.loads((repository_root / "contracts" / "worker-api-v1.json").read_text())
    assert contract["protocol_version"] == "1"
    assert contract["idempotency"]["same_job_id_different_payload"] == "409_conflict"
    assert "cancelled" in contract["job_states"]


def test_running_diagnostic_job_can_be_cancelled(tmp_path, auth_headers, job_payload):
    artifact_root = tmp_path / "artifacts"
    app = create_app(
        database_path=tmp_path / "worker.db",
        artifact_root=artifact_root,
        api_token="test-worker-token",
        engine=DiagnosticEngine(artifact_root, delay_seconds=0.2),
    )
    with TestClient(app) as client:
        assert client.put(
            "/v1/jobs/job-001", headers=auth_headers, json=job_payload
        ).status_code == 202
        cancelled = client.post("/v1/jobs/job-001/cancel", headers=auth_headers)
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "cancelled"
        time.sleep(0.25)
        persisted = client.get("/v1/jobs/job-001", headers=auth_headers)
        assert persisted.json()["status"] == "cancelled"
        assert client.get(
            "/v1/jobs/job-001/artifacts/clip", headers=auth_headers
        ).status_code == 409

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from worker.app.main import create_app  # noqa: E402


@pytest.fixture
def worker_client(tmp_path):
    app = create_app(
        database_path=tmp_path / "worker.db",
        artifact_root=tmp_path / "artifacts",
        api_token="test-worker-token",
    )
    with TestClient(app) as client:
        yield client


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-worker-token"}


@pytest.fixture
def job_payload():
    return {
        "protocol_version": "1",
        "job_id": "job-001",
        "scene_id": "scene-001",
        "mode": "text_to_video",
        "engine": "diagnostic",
        "model_revision": "diagnostic-v1",
        "prompt": "A blue crystal planet",
        "duration_seconds": 5,
        "width": 1280,
        "height": 704,
        "fps": 24,
        "seed": 7,
        "reference_artifact_ids": [],
    }

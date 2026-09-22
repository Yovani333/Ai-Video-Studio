import asyncio
import hashlib

import httpx
import pytest

from app.schemas.generation import ArtifactMetadata
from app.services.gpu.base import GPUProviderError
from app.services.gpu.http import HttpGPUProvider


def metadata_for(content: bytes) -> ArtifactMetadata:
    return ArtifactMetadata(
        artifact_id="artifact-1",
        media_type="video/mp4",
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        kind="video",
        filename="clip.mp4",
    )


def provider_for(handler, *, max_artifact_bytes: int = 1024) -> HttpGPUProvider:
    return HttpGPUProvider(
        base_url="https://worker.example",
        token="secret",
        max_artifact_bytes=max_artifact_bytes,
        transport=httpx.MockTransport(handler),
    )


def test_download_artifact_is_verified_and_atomically_published(tmp_path):
    content = b"safe-video-bytes"
    provider = provider_for(lambda request: httpx.Response(200, content=content))
    destination = tmp_path / "clip.mp4"

    result = asyncio.run(
        provider.download_artifact("job-1", destination, metadata_for(content))
    )

    assert result == destination
    assert destination.read_bytes() == content
    assert not (tmp_path / "clip.mp4.part").exists()


@pytest.mark.parametrize(
    ("metadata", "expected_code"),
    [
        (
            ArtifactMetadata(
                artifact_id="artifact-1",
                media_type="video/mp4",
                size_bytes=999,
                sha256=hashlib.sha256(b"content").hexdigest(),
                kind="video",
                filename="clip.mp4",
            ),
            "artifact_size_mismatch",
        ),
        (
            ArtifactMetadata(
                artifact_id="artifact-1",
                media_type="video/mp4",
                size_bytes=len(b"content"),
                sha256="0" * 64,
                kind="video",
                filename="clip.mp4",
            ),
            "artifact_checksum_mismatch",
        ),
    ],
)
def test_invalid_artifact_is_removed(tmp_path, metadata, expected_code):
    provider = provider_for(lambda request: httpx.Response(200, content=b"content"))
    destination = tmp_path / "clip.mp4"

    with pytest.raises(GPUProviderError) as error:
        asyncio.run(provider.download_artifact("job-1", destination, metadata))

    assert error.value.code == expected_code
    assert not destination.exists()
    assert not (tmp_path / "clip.mp4.part").exists()


def test_download_enforces_configured_size_limit(tmp_path):
    content = b"too-large"
    provider = provider_for(
        lambda request: httpx.Response(200, content=content),
        max_artifact_bytes=4,
    )

    with pytest.raises(GPUProviderError) as error:
        asyncio.run(
            provider.download_artifact("job-1", tmp_path / "clip.mp4", metadata_for(content))
        )

    assert error.value.code == "artifact_too_large"


def test_download_maps_not_ready_conflict_as_retryable(tmp_path):
    provider = provider_for(
        lambda request: httpx.Response(409, json={"detail": "not ready"})
    )
    content = b"content"

    with pytest.raises(GPUProviderError) as error:
        asyncio.run(
            provider.download_artifact("job-1", tmp_path / "clip.mp4", metadata_for(content))
        )

    assert error.value.code == "worker_artifact_not_ready"
    assert error.value.retryable is True


@pytest.mark.parametrize(
    ("status_code", "expected_code", "retryable"),
    [
        (401, "worker_auth_failed", False),
        (409, "worker_job_conflict", False),
        (429, "worker_rate_limited", True),
        (503, "worker_unavailable", True),
    ],
)
def test_worker_http_errors_have_stable_categories(
    status_code, expected_code, retryable
):
    provider = provider_for(
        lambda request: httpx.Response(status_code, json={"detail": "failure"})
    )

    with pytest.raises(GPUProviderError) as error:
        asyncio.run(provider.probe())

    assert error.value.code == expected_code
    assert error.value.retryable is retryable

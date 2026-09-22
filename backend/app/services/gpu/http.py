import hashlib
import os
from pathlib import Path

import httpx
from pydantic import ValidationError

from app.schemas.generation import ArtifactMetadata, WorkerJobRead, WorkerJobRequest
from app.services.gpu.base import GPUProvider, GPUProviderError


ERRORS_BY_STATUS: dict[int, tuple[str, bool]] = {
    400: ("worker_request_invalid", False),
    401: ("worker_auth_failed", False),
    403: ("worker_auth_failed", False),
    404: ("worker_job_not_found", False),
    409: ("worker_job_conflict", False),
    410: ("worker_artifact_expired", False),
    422: ("worker_request_invalid", False),
    429: ("worker_rate_limited", True),
}


class HttpGPUProvider(GPUProvider):
    name = "http-worker"

    def __init__(
        self,
        base_url: str,
        token: str,
        timeout_seconds: float = 10.0,
        max_artifact_bytes: int = 2_147_483_648,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout_seconds = timeout_seconds
        self.max_artifact_bytes = max_artifact_bytes
        self.transport = transport

    def _ensure_configured(self) -> None:
        if not self.base_url or not self.token:
            raise GPUProviderError(
                "provider_not_configured",
                "Remote GPU worker is not configured.",
            )

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    @staticmethod
    def _error_detail(response: httpx.Response) -> str:
        try:
            body = response.json()
        except ValueError:
            return "Remote worker rejected the request."
        if isinstance(body, dict) and isinstance(body.get("detail"), str):
            return body["detail"]
        return "Remote worker rejected the request."

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        code, retryable = ERRORS_BY_STATUS.get(
            response.status_code,
            ("worker_unavailable", response.status_code >= 500),
        )
        raise GPUProviderError(
            code,
            self._error_detail(response),
            retryable=retryable,
        )

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url,
            headers=self._headers(),
            timeout=self.timeout_seconds,
            transport=self.transport,
        )

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        self._ensure_configured()
        try:
            async with self._client() as client:
                response = await client.request(method, path, **kwargs)
        except httpx.TimeoutException as exc:
            raise GPUProviderError(
                "provider_timeout",
                "The remote worker did not respond before the timeout.",
                retryable=True,
            ) from exc
        except httpx.HTTPError as exc:
            raise GPUProviderError(
                "provider_unreachable",
                "The remote worker could not be reached.",
                retryable=True,
            ) from exc
        self._raise_for_status(response)
        return response

    @staticmethod
    def _validate_job_response(response: httpx.Response) -> WorkerJobRead:
        try:
            return WorkerJobRead.model_validate(response.json())
        except (ValueError, ValidationError) as exc:
            raise GPUProviderError(
                "worker_protocol_invalid",
                "The remote worker returned an invalid job response.",
            ) from exc

    async def probe(self) -> dict[str, object]:
        response = await self._request("GET", "/v1/readiness")
        try:
            body = response.json()
        except ValueError as exc:
            raise GPUProviderError(
                "worker_protocol_invalid",
                "The remote worker returned invalid readiness data.",
            ) from exc
        if not isinstance(body, dict):
            raise GPUProviderError(
                "worker_protocol_invalid",
                "The remote worker returned invalid readiness data.",
            )
        return body

    async def submit(self, request: WorkerJobRequest) -> WorkerJobRead:
        response = await self._request(
            "PUT", f"/v1/jobs/{request.job_id}", json=request.model_dump(mode="json")
        )
        return self._validate_job_response(response)

    async def get_status(self, job_id: str) -> WorkerJobRead:
        response = await self._request("GET", f"/v1/jobs/{job_id}")
        return self._validate_job_response(response)

    async def cancel(self, job_id: str) -> WorkerJobRead:
        response = await self._request("POST", f"/v1/jobs/{job_id}/cancel")
        return self._validate_job_response(response)

    async def download_artifact(
        self,
        job_id: str,
        destination: Path,
        expected: ArtifactMetadata,
    ) -> Path:
        self._ensure_configured()
        if expected.size_bytes > self.max_artifact_bytes:
            raise GPUProviderError(
                "artifact_too_large",
                "The remote artifact exceeds the configured size limit.",
            )

        destination.parent.mkdir(parents=True, exist_ok=True)
        partial = destination.with_name(f"{destination.name}.part")
        partial.unlink(missing_ok=True)
        digest = hashlib.sha256()
        received = 0

        try:
            async with self._client() as client:
                async with client.stream(
                    "GET", f"/v1/jobs/{job_id}/artifacts/clip"
                ) as response:
                    if response.status_code == 409:
                        raise GPUProviderError(
                            "worker_artifact_not_ready",
                            self._error_detail(response),
                            retryable=True,
                        )
                    self._raise_for_status(response)
                    with partial.open("xb") as artifact_file:
                        async for chunk in response.aiter_bytes():
                            received += len(chunk)
                            if received > self.max_artifact_bytes:
                                raise GPUProviderError(
                                    "artifact_too_large",
                                    "The remote artifact exceeds the configured size limit.",
                                )
                            digest.update(chunk)
                            artifact_file.write(chunk)
                        artifact_file.flush()
                        os.fsync(artifact_file.fileno())
        except httpx.TimeoutException as exc:
            partial.unlink(missing_ok=True)
            raise GPUProviderError(
                "provider_timeout",
                "The artifact transfer did not finish before the timeout.",
                retryable=True,
            ) from exc
        except httpx.HTTPError as exc:
            partial.unlink(missing_ok=True)
            raise GPUProviderError(
                "provider_unreachable",
                "The remote artifact could not be downloaded.",
                retryable=True,
            ) from exc
        except Exception:
            partial.unlink(missing_ok=True)
            raise

        if received != expected.size_bytes:
            partial.unlink(missing_ok=True)
            raise GPUProviderError(
                "artifact_size_mismatch",
                "The downloaded artifact size did not match its metadata.",
            )
        if digest.hexdigest() != expected.sha256.lower():
            partial.unlink(missing_ok=True)
            raise GPUProviderError(
                "artifact_checksum_mismatch",
                "The downloaded artifact checksum did not match its metadata.",
            )

        os.replace(partial, destination)
        return destination

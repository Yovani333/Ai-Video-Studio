import httpx

from app.schemas.generation import WorkerJobRead, WorkerJobRequest
from app.services.gpu.base import GPUProvider, GPUProviderError


class HttpGPUProvider(GPUProvider):
    name = "http-worker"

    def __init__(self, base_url: str, token: str, timeout_seconds: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout_seconds = timeout_seconds

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        if not self.base_url or not self.token:
            raise GPUProviderError(
                "provider_not_configured",
                "Remote GPU worker is not configured.",
            )
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                headers=self._headers(),
                timeout=self.timeout_seconds,
            ) as client:
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

        if response.status_code >= 400:
            try:
                body = response.json()
                detail = (
                    body.get("detail", "Remote worker rejected the request")
                    if isinstance(body, dict)
                    else "Remote worker rejected the request"
                )
            except ValueError:
                detail = "Remote worker rejected the request"
            raise GPUProviderError(
                f"worker_http_{response.status_code}",
                str(detail),
                retryable=response.status_code >= 500,
            )
        return response

    async def probe(self) -> dict[str, object]:
        return (await self._request("GET", "/v1/readiness")).json()

    async def submit(self, request: WorkerJobRequest) -> WorkerJobRead:
        response = await self._request(
            "PUT", f"/v1/jobs/{request.job_id}", json=request.model_dump(mode="json")
        )
        return WorkerJobRead.model_validate(response.json())

    async def get_status(self, job_id: str) -> WorkerJobRead:
        response = await self._request("GET", f"/v1/jobs/{job_id}")
        return WorkerJobRead.model_validate(response.json())

    async def cancel(self, job_id: str) -> WorkerJobRead:
        response = await self._request("POST", f"/v1/jobs/{job_id}/cancel")
        return WorkerJobRead.model_validate(response.json())

    async def download_artifact(self, job_id: str) -> bytes:
        return (await self._request("GET", f"/v1/jobs/{job_id}/artifacts/clip")).content

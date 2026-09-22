from abc import ABC, abstractmethod
from pathlib import Path

from app.schemas.generation import ArtifactMetadata, WorkerJobRead, WorkerJobRequest


class GPUProviderError(RuntimeError):
    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


class GPUProvider(ABC):
    name: str

    @abstractmethod
    async def probe(self) -> dict[str, object]:
        raise NotImplementedError

    @abstractmethod
    async def submit(self, request: WorkerJobRequest) -> WorkerJobRead:
        raise NotImplementedError

    @abstractmethod
    async def get_status(self, job_id: str) -> WorkerJobRead:
        raise NotImplementedError

    @abstractmethod
    async def cancel(self, job_id: str) -> WorkerJobRead:
        raise NotImplementedError

    @abstractmethod
    async def download_artifact(
        self,
        job_id: str,
        destination: Path,
        expected: ArtifactMetadata,
    ) -> Path:
        raise NotImplementedError

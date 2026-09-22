from collections.abc import Generator

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.config import get_settings
from app.services.gpu.base import GPUProvider
from app.services.gpu.http import HttpGPUProvider


def get_db() -> Generator[Session, None, None]:
    """Provide one database session per request."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_gpu_provider() -> GPUProvider:
    settings = get_settings()
    return HttpGPUProvider(
        base_url=settings.gpu_api_url,
        token=settings.gpu_worker_token,
        timeout_seconds=settings.gpu_request_timeout_seconds,
    )

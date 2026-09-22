from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPOSITORY_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    app_name: str = "AI Video Studio API"
    app_environment: str = "development"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'ai_video_studio.db').as_posix()}"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    storage_root: Path = REPOSITORY_DIR / "storage"
    gpu_provider: str = ""
    gpu_api_url: str = ""
    gpu_api_key: str = ""
    gpu_worker_token: str = ""
    gpu_request_timeout_seconds: float = 10.0
    video_engine: str = "stub"

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

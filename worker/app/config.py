from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

WORKER_DIR = Path(__file__).resolve().parents[1]


class WorkerSettings(BaseSettings):
    worker_api_token: str = ""
    worker_database_path: Path = WORKER_DIR / "worker.db"
    worker_artifact_root: Path = WORKER_DIR / "artifacts"

    model_config = SettingsConfigDict(
        env_file=WORKER_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_worker_settings() -> WorkerSettings:
    return WorkerSettings()

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from worker.app.schemas import ArtifactMetadata, WorkerJobRead


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PayloadConflictError(RuntimeError):
    pass


class WorkerJobStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self._lock = threading.Lock()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS worker_jobs (
                    job_id TEXT PRIMARY KEY,
                    payload_hash TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    artifact_json TEXT,
                    effective_parameters_json TEXT,
                    error_code TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT
                )
                """
            )

    def mark_interrupted_jobs(self) -> None:
        now = utc_now()
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                UPDATE worker_jobs
                SET status = 'failed', error_code = 'worker_restarted',
                    error_message = 'The worker restarted during execution.',
                    updated_at = ?, completed_at = ?
                WHERE status IN ('running', 'transferring')
                """,
                (now, now),
            )

    def put(self, job_id: str, payload_hash: str, payload: dict) -> tuple[WorkerJobRead, bool]:
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        now = utc_now()
        with self._lock, self._connect() as connection:
            existing = connection.execute(
                "SELECT * FROM worker_jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
            if existing is not None:
                if existing["payload_hash"] != payload_hash:
                    raise PayloadConflictError
                return self._to_schema(existing), False
            connection.execute(
                """
                INSERT INTO worker_jobs (
                    job_id, payload_hash, payload_json, status, created_at, updated_at
                ) VALUES (?, ?, ?, 'queued', ?, ?)
                """,
                (job_id, payload_hash, serialized, now, now),
            )
            row = connection.execute(
                "SELECT * FROM worker_jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
        return self._to_schema(row), True

    def get(self, job_id: str) -> WorkerJobRead | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM worker_jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
        return self._to_schema(row) if row else None

    def get_payload(self, job_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM worker_jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def list_queued_ids(self) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT job_id FROM worker_jobs WHERE status = 'queued' ORDER BY created_at"
            ).fetchall()
        return [str(row["job_id"]) for row in rows]

    def update(
        self,
        job_id: str,
        *,
        status: str,
        artifact: ArtifactMetadata | None = None,
        effective_parameters: dict | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> WorkerJobRead:
        now = utc_now()
        started_at = now if status == "running" else None
        completed_at = now if status in {"succeeded", "failed", "timed_out", "cancelled"} else None
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                UPDATE worker_jobs
                SET status = ?, artifact_json = COALESCE(?, artifact_json),
                    effective_parameters_json = COALESCE(?, effective_parameters_json),
                    error_code = ?, error_message = ?, updated_at = ?,
                    started_at = COALESCE(started_at, ?),
                    completed_at = COALESCE(?, completed_at)
                WHERE job_id = ?
                """,
                (
                    status,
                    artifact.model_dump_json() if artifact else None,
                    json.dumps(effective_parameters) if effective_parameters else None,
                    error_code,
                    error_message,
                    now,
                    started_at,
                    completed_at,
                    job_id,
                ),
            )
            row = connection.execute(
                "SELECT * FROM worker_jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
        if row is None:
            raise KeyError(job_id)
        return self._to_schema(row)

    @staticmethod
    def _to_schema(row: sqlite3.Row) -> WorkerJobRead:
        return WorkerJobRead(
            job_id=row["job_id"],
            payload_hash=row["payload_hash"],
            status=row["status"],
            artifact=json.loads(row["artifact_json"]) if row["artifact_json"] else None,
            effective_parameters=(
                json.loads(row["effective_parameters_json"])
                if row["effective_parameters_json"]
                else None
            ),
            error_code=row["error_code"],
            error_message=row["error_message"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
        )

import asyncio
from pathlib import Path

from worker.app.engine import DiagnosticEngine
from worker.app.store import WorkerJobStore


class WorkerRuntime:
    def __init__(self, store: WorkerJobStore, engine: DiagnosticEngine) -> None:
        self.store = store
        self.engine = engine
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.consumer_task: asyncio.Task | None = None

    async def start(self) -> None:
        self.store.initialize()
        self.store.mark_interrupted_jobs()
        self.consumer_task = asyncio.create_task(self._consume())
        for job_id in self.store.list_queued_ids():
            await self.queue.put(job_id)

    async def stop(self) -> None:
        if self.consumer_task:
            self.consumer_task.cancel()
            try:
                await self.consumer_task
            except asyncio.CancelledError:
                pass

    async def enqueue(self, job_id: str) -> None:
        await self.queue.put(job_id)

    async def _consume(self) -> None:
        while True:
            job_id = await self.queue.get()
            try:
                current = self.store.get(job_id)
                if current is None or current.status != "queued":
                    continue
                self.store.update(job_id, status="running")
                payload = self.store.get_payload(job_id)
                if payload is None:
                    self.store.update(
                        job_id,
                        status="failed",
                        error_code="payload_missing",
                        error_message="Persisted job payload is missing.",
                    )
                    continue
                artifact, effective = await self.engine.generate(payload)
                latest = self.store.get(job_id)
                if latest and latest.status == "cancelled":
                    artifact_path = self.engine.artifact_root / artifact.filename
                    artifact_path.unlink(missing_ok=True)
                    continue
                self.store.update(
                    job_id,
                    status="succeeded",
                    artifact=artifact,
                    effective_parameters=effective,
                )
            except Exception:  # Worker boundary: persist a sanitized failure.
                self.store.update(
                    job_id,
                    status="failed",
                    error_code="diagnostic_failed",
                    error_message="Diagnostic execution failed.",
                )
            finally:
                self.queue.task_done()

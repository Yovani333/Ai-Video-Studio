from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.generation_job import GenerationJob


class GenerationJobRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, job: GenerationJob) -> GenerationJob:
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        return job

    def save(self, job: GenerationJob) -> GenerationJob:
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        return job

    def get(self, job_id: str) -> GenerationJob | None:
        return self.session.get(GenerationJob, job_id)

    def next_attempt(self, scene_id: str) -> int:
        statement = select(func.coalesce(func.max(GenerationJob.attempt), 0)).where(
            GenerationJob.scene_id == scene_id
        )
        return int(self.session.scalar(statement) or 0) + 1

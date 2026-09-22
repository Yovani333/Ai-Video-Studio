from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import GenerationJobStatus


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class GenerationJob(Base):
    __tablename__ = "generation_jobs"
    __table_args__ = (
        UniqueConstraint("scene_id", "attempt", name="uq_generation_job_scene_attempt"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    scene_id: Mapped[str] = mapped_column(
        ForeignKey("scenes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    engine: Mapped[str] = mapped_column(String(64), nullable=False)
    model_revision: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[GenerationJobStatus] = mapped_column(
        Enum(GenerationJobStatus, native_enum=False),
        nullable=False,
        default=GenerationJobStatus.QUEUED,
    )
    request_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    effective_parameters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    remote_job_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    artifact: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

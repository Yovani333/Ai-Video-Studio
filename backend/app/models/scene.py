from sqlalchemy import Enum, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import SceneStatus


class Scene(Base):
    __tablename__ = "scenes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[SceneStatus] = mapped_column(
        Enum(SceneStatus, native_enum=False), nullable=False, default=SceneStatus.WAITING
    )
    context: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    project = relationship("Project", back_populates="scenes")

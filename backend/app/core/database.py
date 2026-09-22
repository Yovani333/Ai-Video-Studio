from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def create_database_tables() -> None:
    # Import models so SQLAlchemy registers their tables before create_all.
    from app.models import generation_job, project, scene  # noqa: F401

    Base.metadata.create_all(bind=engine)

from collections.abc import Generator

from sqlalchemy.orm import Session

from app.core.database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Provide one database session per request."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

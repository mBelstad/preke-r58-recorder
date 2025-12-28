"""Database setup and connection management"""

from sqlmodel import Session, SQLModel, create_engine

from ..config import get_settings

_engine = None


def get_engine():
    """Get or create database engine"""
    global _engine
    if _engine is None:
        settings = get_settings()

        # Ensure directory exists
        db_path = settings.db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)

        _engine = create_engine(
            f"sqlite:///{db_path}",
            echo=settings.debug,
            connect_args={"check_same_thread": False}
        )
    return _engine


def init_db():
    """Initialize database tables"""
    engine = get_engine()
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    """Get a new database session"""
    engine = get_engine()
    return Session(engine)


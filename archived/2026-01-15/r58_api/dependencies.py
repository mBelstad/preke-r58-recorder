"""Dependency injection container for FastAPI"""
from functools import lru_cache
from typing import Generator

from sqlmodel import Session

from .config import Settings, get_settings
from .db.database import get_engine


def get_db() -> Generator[Session, None, None]:
    """Get database session dependency"""
    engine = get_engine()
    with Session(engine) as session:
        yield session


@lru_cache()
def get_cached_settings() -> Settings:
    """Cached settings for performance"""
    return get_settings()


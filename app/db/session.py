"""Engine and session factory, plus the FastAPI dependency that yields a session."""

import logging
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.base import Base

logger = logging.getLogger(__name__)

_settings = get_settings()

# SQLite connections are bound to the creating thread by default. FastAPI runs
# sync endpoints in a thread pool, so this check must be disabled; each request
# still gets its own session, so a connection is never used by two threads at once.
_connect_args = (
    {"check_same_thread": False} if _settings.database_url.startswith("sqlite") else {}
)

engine = create_engine(
    _settings.database_url,
    echo=_settings.sql_echo,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """Create all tables that do not exist yet.

    Fine for a small service; a production system would use migrations (Alembic).
    """
    # Import the models so they are registered on ``Base.metadata``.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    logger.info("Database initialised at %s", engine.url.render_as_string(hide_password=True))


def get_db() -> Iterator[Session]:
    """Yield a database session for a single request and always close it afterwards."""
    with SessionLocal() as session:
        yield session


# Reusable annotated dependency, e.g. ``def endpoint(db: DbSession): ...``
DbSession = Annotated[Session, Depends(get_db)]

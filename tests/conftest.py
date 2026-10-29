"""Shared pytest fixtures.

The tests run against a throw-away SQLite file so the real ``address_book.db``
is never touched. The environment variable must be set *before* the app is
imported, because the engine is created at import time.
"""

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

_TEST_DIR = Path(tempfile.mkdtemp(prefix="address_book_tests_"))
os.environ["ADDRESS_BOOK_DATABASE_URL"] = f"sqlite:///{_TEST_DIR / 'test.db'}"

from fastapi.testclient import TestClient  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def client() -> Iterator[TestClient]:
    """A test client with an empty database (the lifespan creates the tables)."""
    with TestClient(app) as test_client:
        yield test_client
    # Wipe all rows so every test starts from a clean state.
    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())


@pytest.fixture
def address_payload() -> dict[str, object]:
    """A valid address (Brandenburg Gate, Berlin)."""
    return {
        "label": "Brandenburg Gate",
        "street": "Pariser Platz",
        "postal_code": "10117",
        "city": "Berlin",
        "country": "de",
        "latitude": 52.516275,
        "longitude": 13.377704,
    }

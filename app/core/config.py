"""Application settings, loaded from environment variables and an optional ``.env`` file."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    """Runtime configuration.

    Every field can be overridden with an environment variable prefixed with
    ``ADDRESS_BOOK_`` (e.g. ``ADDRESS_BOOK_LOG_LEVEL=DEBUG``).
    """

    model_config = SettingsConfigDict(
        env_prefix="ADDRESS_BOOK_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Address Book API"
    database_url: str = "sqlite:///./address_book.db"
    log_level: LogLevel = "INFO"
    # Echo every SQL statement to the log; useful while debugging only.
    sql_echo: bool = False


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance so the environment is read only once."""
    return Settings()

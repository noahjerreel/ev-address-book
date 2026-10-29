"""ORM model for the ``addresses`` table."""

from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Address(Base):
    """A postal address together with its geographic coordinates (WGS 84)."""

    __tablename__ = "addresses"
    __table_args__ = (
        # Database-level safety net in addition to the Pydantic validation.
        CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_addresses_latitude_range"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_addresses_longitude_range"),
        # Speeds up the bounding-box pre-filter used by the distance search.
        Index("ix_addresses_latitude_longitude", "latitude", "longitude"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str | None] = mapped_column(String(100))
    street: Mapped[str] = mapped_column(String(200))
    postal_code: Mapped[str] = mapped_column(String(20))
    city: Mapped[str] = mapped_column(String(100))
    country: Mapped[str] = mapped_column(String(2))
    latitude: Mapped[float]
    longitude: Mapped[float]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    def __repr__(self) -> str:
        return (
            f"Address(id={self.id!r}, city={self.city!r}, "
            f"latitude={self.latitude!r}, longitude={self.longitude!r})"
        )

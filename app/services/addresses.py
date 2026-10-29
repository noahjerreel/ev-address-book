"""CRUD operations and the distance search for addresses."""

import logging
from collections.abc import Sequence

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import AddressNotFoundError
from app.models import Address
from app.schemas import AddressCreate, AddressUpdate
from app.utils.geo import bounding_box, haversine_km

logger = logging.getLogger(__name__)


def create_address(db: Session, data: AddressCreate) -> Address:
    """Persist a new address and return it."""
    address = Address(**data.model_dump())
    db.add(address)
    db.commit()
    db.refresh(address)
    logger.info("Created address id=%d (%s, %s)", address.id, address.city, address.country)
    return address


def list_addresses(db: Session, *, offset: int = 0, limit: int = 100) -> Sequence[Address]:
    """Return a page of addresses ordered by id."""
    stmt = select(Address).order_by(Address.id).offset(offset).limit(limit)
    return db.scalars(stmt).all()


def get_address(db: Session, address_id: int) -> Address:
    """Return the address with ``address_id`` or raise :class:`AddressNotFoundError`."""
    address = db.get(Address, address_id)
    if address is None:
        logger.warning("Address id=%d not found", address_id)
        raise AddressNotFoundError(address_id)
    return address


def replace_address(db: Session, address_id: int, data: AddressCreate) -> Address:
    """Overwrite every field of an existing address (``PUT`` semantics)."""
    return _apply_changes(db, address_id, data.model_dump())


def update_address(db: Session, address_id: int, data: AddressUpdate) -> Address:
    """Change only the fields that were sent (``PATCH`` semantics)."""
    return _apply_changes(db, address_id, data.model_dump(exclude_unset=True))


def delete_address(db: Session, address_id: int) -> None:
    """Delete an address or raise :class:`AddressNotFoundError`."""
    address = get_address(db, address_id)
    db.delete(address)
    db.commit()
    logger.info("Deleted address id=%d", address_id)


def find_addresses_within(
    db: Session,
    *,
    latitude: float,
    longitude: float,
    distance_km: float,
    limit: int = 100,
) -> list[tuple[Address, float]]:
    """Return ``(address, distance_km)`` pairs within ``distance_km``, nearest first.

    SQLite has no geospatial functions, so the search runs in two steps:

    1. an indexed bounding-box query narrows the candidates in the database;
    2. the exact great-circle (haversine) distance filters and sorts them in Python.
    """
    box = bounding_box(latitude, longitude, distance_km)
    longitude_filter = or_(
        *(Address.longitude.between(lo, hi) for lo, hi in box.lon_ranges)
    )
    stmt = select(Address).where(
        and_(Address.latitude.between(box.min_lat, box.max_lat), longitude_filter)
    )
    candidates = db.scalars(stmt).all()

    matches = [
        (address, distance)
        for address in candidates
        if (distance := haversine_km(latitude, longitude, address.latitude, address.longitude))
        <= distance_km
    ]
    matches.sort(key=lambda match: match[1])

    logger.info(
        "Nearby search (%.6f, %.6f, %.3f km): %d candidates, %d matches",
        latitude,
        longitude,
        distance_km,
        len(candidates),
        len(matches),
    )
    return matches[:limit]


def _apply_changes(db: Session, address_id: int, changes: dict[str, object]) -> Address:
    """Set ``changes`` on an existing address and commit."""
    address = get_address(db, address_id)
    for field, value in changes.items():
        setattr(address, field, value)
    db.commit()
    db.refresh(address)
    logger.info("Updated address id=%d (fields: %s)", address_id, ", ".join(sorted(changes)))
    return address

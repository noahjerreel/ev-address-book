"""Endpoints for the ``/addresses`` resource.

Endpoints are thin: they validate input (via Pydantic), call the service layer
and shape the response. ``AddressNotFoundError`` is turned into a 404 by the
exception handler registered in ``app.main``.
"""

from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.db.session import DbSession
from app.schemas import (
    AddressCreate,
    AddressRead,
    AddressUpdate,
    AddressWithDistance,
    NearbyQuery,
)
from app.services import addresses as service

router = APIRouter(prefix="/addresses", tags=["addresses"])

AddressId = Annotated[int, Path(ge=1, description="Id of the address.")]

_NOT_FOUND = {status.HTTP_404_NOT_FOUND: {"description": "Address not found"}}


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create an address",
)
def create_address(payload: AddressCreate, db: DbSession) -> AddressRead:
    """Create a new address with its coordinates."""
    return AddressRead.model_validate(service.create_address(db, payload))


@router.get("", summary="List addresses")
def list_addresses(
    db: DbSession,
    offset: Annotated[int, Query(ge=0, description="Number of addresses to skip.")] = 0,
    limit: Annotated[int, Query(ge=1, le=1000, description="Page size.")] = 100,
) -> list[AddressRead]:
    """Return addresses ordered by id, with offset/limit pagination."""
    addresses = service.list_addresses(db, offset=offset, limit=limit)
    return [AddressRead.model_validate(address) for address in addresses]


# Declared before ``/{address_id}`` so "nearby" is never matched as an id.
@router.get("/nearby", summary="Find addresses within a distance")
def find_nearby_addresses(
    query: Annotated[NearbyQuery, Query()],
    db: DbSession,
) -> list[AddressWithDistance]:
    """Return addresses within `distance_km` of the given point, nearest first.

    Distances are great-circle distances on a spherical earth.
    """
    matches = service.find_addresses_within(
        db,
        latitude=query.latitude,
        longitude=query.longitude,
        distance_km=query.distance_km,
        limit=query.limit,
    )
    return [
        AddressWithDistance(
            **AddressRead.model_validate(address).model_dump(),
            distance_km=round(distance, 3),
        )
        for address, distance in matches
    ]


@router.get("/{address_id}", summary="Get an address", responses=_NOT_FOUND)
def get_address(address_id: AddressId, db: DbSession) -> AddressRead:
    """Return a single address."""
    return AddressRead.model_validate(service.get_address(db, address_id))


@router.put("/{address_id}", summary="Replace an address", responses=_NOT_FOUND)
def replace_address(address_id: AddressId, payload: AddressCreate, db: DbSession) -> AddressRead:
    """Replace all fields of an address."""
    return AddressRead.model_validate(service.replace_address(db, address_id, payload))


@router.patch("/{address_id}", summary="Update an address", responses=_NOT_FOUND)
def update_address(address_id: AddressId, payload: AddressUpdate, db: DbSession) -> AddressRead:
    """Update only the fields present in the request body."""
    return AddressRead.model_validate(service.update_address(db, address_id, payload))


@router.delete(
    "/{address_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an address",
    responses=_NOT_FOUND,
)
def delete_address(address_id: AddressId, db: DbSession) -> None:
    """Delete an address."""
    service.delete_address(db, address_id)

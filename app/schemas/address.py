"""Request/response schemas and validation rules for addresses."""

from datetime import UTC, datetime
from typing import Annotated, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.utils.geo import MAX_SURFACE_DISTANCE_KM

# --------------------------------------------------------------------------- #
# Reusable, validated field types
# --------------------------------------------------------------------------- #
Latitude = Annotated[
    float,
    Field(ge=-90, le=90, allow_inf_nan=False, description="Latitude in decimal degrees (WGS 84).",
          examples=[52.520008]),
]
Longitude = Annotated[
    float,
    Field(ge=-180, le=180, allow_inf_nan=False,
          description="Longitude in decimal degrees (WGS 84).", examples=[13.404954]),
]
Label = Annotated[
    str, Field(min_length=1, max_length=100, description="Optional name, e.g. 'Home'.",
               examples=["Office"]),
]
Street = Annotated[
    str, Field(min_length=1, max_length=200, description="Street name and house number.",
               examples=["Unter den Linden 1"]),
]
PostalCode = Annotated[
    str,
    Field(min_length=2, max_length=20, pattern=r"^[A-Za-z0-9][A-Za-z0-9 \-]*[A-Za-z0-9]$",
          description="Postal / ZIP code (letters, digits, spaces and hyphens).",
          examples=["10117"]),
]
City = Annotated[
    str, Field(min_length=1, max_length=100, description="City or town.", examples=["Berlin"]),
]
CountryCode = Annotated[
    str,
    Field(pattern=r"^[A-Za-z]{2}$", description="ISO 3166-1 alpha-2 country code.",
          examples=["DE"]),
    AfterValidator(str.upper),
]


class _StrictModel(BaseModel):
    """Base for input models: trims strings and rejects unknown fields."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


# --------------------------------------------------------------------------- #
# Input models
# --------------------------------------------------------------------------- #
class AddressCreate(_StrictModel):
    """Payload to create an address, or to fully replace one (``PUT``)."""

    label: Label | None = None
    street: Street
    postal_code: PostalCode
    city: City
    country: CountryCode
    latitude: Latitude
    longitude: Longitude


class AddressUpdate(_StrictModel):
    """Payload for a partial update (``PATCH``): only the fields sent are changed."""

    label: Label | None = None
    street: Street | None = None
    postal_code: PostalCode | None = None
    city: City | None = None
    country: CountryCode | None = None
    latitude: Latitude | None = None
    longitude: Longitude | None = None

    @model_validator(mode="after")
    def _check_fields(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")
        # ``None`` means "not provided" for required columns; an explicit ``null``
        # would otherwise wipe a mandatory value. Only ``label`` may be cleared.
        explicit_nulls = [
            name
            for name in self.model_fields_set
            if name != "label" and getattr(self, name) is None
        ]
        if explicit_nulls:
            raise ValueError(f"Fields cannot be null: {', '.join(sorted(explicit_nulls))}.")
        return self


class NearbyQuery(_StrictModel):
    """Query parameters for the distance search."""

    latitude: Latitude
    longitude: Longitude
    distance_km: float = Field(
        gt=0,
        le=MAX_SURFACE_DISTANCE_KM,
        allow_inf_nan=False,
        description="Search radius in kilometres (great-circle distance).",
        examples=[5],
    )
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum number of results.")


# --------------------------------------------------------------------------- #
# Output models
# --------------------------------------------------------------------------- #
class AddressRead(BaseModel):
    """An address as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str | None
    street: str
    postal_code: str
    city: str
    country: str
    latitude: float
    longitude: float
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def _assume_utc(cls, value: datetime) -> datetime:
        # SQLite does not store time zones; timestamps are always written in UTC.
        return value if value.tzinfo else value.replace(tzinfo=UTC)


class AddressWithDistance(AddressRead):
    """An address plus its distance from the search point."""

    distance_km: float = Field(description="Great-circle distance from the search point.")
